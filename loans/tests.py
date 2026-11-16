import datetime

from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from registry.models import Household

from . import workflow
from .models import Disbursement, LoanApplication

Status = LoanApplication.Status


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class WorkflowRuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.isaac_loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")  # submitted
        self.sacco = User.objects.get(username="sacco")
        self.groupexec = User.objects.get(username="groupexec")

    def test_a_loan_cannot_skip_appraisal(self):
        with self.assertRaises(workflow.TransitionError):
            workflow.move(self.isaac_loan, Status.APPROVED, self.sacco)

    def test_only_the_named_role_can_move_a_loan(self):
        with self.assertRaises(PermissionDenied):
            workflow.move(self.isaac_loan, Status.APPRAISED, self.groupexec)

    def test_system_only_changes_cannot_be_made_by_a_person(self):
        self.isaac_loan.status = Status.DISBURSED
        self.assertFalse(workflow.can_move(self.isaac_loan, Status.DEFAULTED, self.sacco))
        self.assertTrue(workflow.can_move(self.isaac_loan, Status.DEFAULTED, None))

    def test_submitting_records_the_time(self):
        loan = LoanApplication.objects.create(
            household=self.isaac_loan.household,
            enterprise_group=self.isaac_loan.enterprise_group,
            sacco=self.isaac_loan.sacco,
            amount=100_000,
            enterprise="Test",
            business_plan="Test",
        )
        workflow.move(loan, Status.SUBMITTED, self.groupexec)
        self.assertIsNotNone(loan.submitted_at)


class LoanApplicationPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def apply(self, household, **overrides):
        data = {"household": household.pk, "amount": 600_000, "enterprise": "Piglets", "business_plan": "Raise pigs", "term_months": 12}
        data.update(overrides)
        return self.client.post(reverse("loans:loan_create"), data)

    def verified_household_without_loan(self):
        household = Household.objects.get(head_name="John Ssemwogerere")
        household.verification = Household.Verification.VERIFIED
        household.save()
        return household

    def test_group_executive_creates_a_draft(self):
        self.login("groupexec")
        household = self.verified_household_without_loan()
        self.apply(household)
        loan = LoanApplication.objects.get(household=household)
        self.assertEqual(loan.status, Status.DRAFT)
        self.assertEqual(loan.sacco.name, "Seeta PDM SACCO")

    def test_unverified_household_cannot_apply(self):
        self.login("groupexec")
        florence = Household.objects.get(head_name="Florence Atim")  # pending verification
        response = self.apply(florence)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LoanApplication.objects.filter(household=florence).exists())

    def test_loan_above_the_ceiling_is_refused(self):
        self.login("groupexec")
        household = self.verified_household_without_loan()
        response = self.apply(household, amount=1_500_000)
        self.assertContains(response, "cannot be more than UGX 1,000,000")

    def test_household_with_an_open_loan_cannot_apply_again(self):
        self.login("groupexec")
        grace = Household.objects.get(nin="CF85001234ABCD")
        response = self.apply(grace)
        self.assertContains(response, "already has an open loan")

    def test_group_executive_submits_a_draft(self):
        self.login("groupexec")
        household = self.verified_household_without_loan()
        self.apply(household)
        loan = LoanApplication.objects.get(household=household)
        self.client.post(reverse("loans:loan_submit", args=[loan.pk]))
        loan.refresh_from_db()
        self.assertEqual(loan.status, Status.SUBMITTED)

    def test_parish_chief_cannot_submit(self):
        loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")
        self.login("parishchief")
        response = self.client.post(reverse("loans:loan_submit", args=[loan.pk]))
        self.assertEqual(response.status_code, 403)


class AppraisalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.force_login(User.objects.get(username="sacco"))
        self.loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")  # submitted

    def appraisal_data(self):
        return {"viability_score": 4, "repayment_score": 3, "group_score": 4, "recommendation": "approve", "reasons": "Good plan."}

    def test_sacco_official_appraises_a_submitted_loan(self):
        self.client.post(reverse("loans:loan_appraise", args=[self.loan.pk]), self.appraisal_data())
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, Status.APPRAISED)
        self.assertEqual(self.loan.appraisal.total_score, 11)
        self.assertEqual(self.loan.appraisal.appraised_by.username, "sacco")

    def test_appraisal_page_redirects_for_a_loan_already_appraised(self):
        grace_loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        response = self.client.get(reverse("loans:loan_appraise", args=[grace_loan.pk]))
        self.assertRedirects(response, reverse("loans:loan_detail", args=[grace_loan.pk]))

    def test_loan_detail_shows_appraisal_and_history(self):
        self.client.post(reverse("loans:loan_appraise", args=[self.loan.pk]), self.appraisal_data())
        response = self.client.get(reverse("loans:loan_detail", args=[self.loan.pk]))
        self.assertContains(response, "11 / 15")
        self.assertContains(response, "submitted → appraised")


class DecisionTests(TestCase):
    """The SACCO official approves or rejects an appraised loan, with reasons for refusals."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.grace_loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")  # appraised
        self.isaac_loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")  # submitted

    def decide(self, loan, decision, reason="", username="sacco"):
        self.client.force_login(User.objects.get(username=username))
        return self.client.post(
            reverse("loans:loan_decide", args=[loan.pk]), {"decision": decision, "reason": reason}
        )

    def test_sacco_official_approves_an_appraised_loan(self):
        self.decide(self.grace_loan, "approve")
        self.grace_loan.refresh_from_db()
        self.assertEqual(self.grace_loan.status, Status.APPROVED)
        self.assertEqual(self.grace_loan.decided_by.username, "sacco")
        self.assertIsNotNone(self.grace_loan.decided_at)

    def test_rejection_keeps_the_reason(self):
        self.decide(self.grace_loan, "reject", "Business plan does not show a market.")
        self.grace_loan.refresh_from_db()
        self.assertEqual(self.grace_loan.status, Status.REJECTED)
        self.assertEqual(self.grace_loan.decision_reason, "Business plan does not show a market.")

    def test_rejection_without_a_reason_is_refused(self):
        response = self.decide(self.grace_loan, "reject", "   ")
        self.grace_loan.refresh_from_db()
        self.assertEqual(self.grace_loan.status, Status.APPRAISED)
        self.assertContains(self.client.get(response.url), "Give the reason for rejecting")

    def test_a_loan_not_yet_appraised_cannot_be_decided(self):
        self.decide(self.isaac_loan, "approve")
        self.isaac_loan.refresh_from_db()
        self.assertEqual(self.isaac_loan.status, Status.SUBMITTED)

    def test_other_roles_cannot_decide(self):
        for username in ("groupexec", "parishchief", "pdc", "subcounty", "national", "auditor"):
            response = self.decide(self.grace_loan, "approve", username=username)
            self.assertEqual(response.status_code, 403, username)
        self.grace_loan.refresh_from_db()
        self.assertEqual(self.grace_loan.status, Status.APPRAISED)

    def test_decision_form_shows_only_for_the_sacco_official(self):
        url = reverse("loans:loan_detail", args=[self.grace_loan.pk])
        self.client.force_login(User.objects.get(username="sacco"))
        self.assertContains(self.client.get(url), "Record decision")
        self.client.force_login(User.objects.get(username="pdc"))
        self.assertNotContains(self.client.get(url), "Record decision")


class DisbursementTests(TestCase):
    """The SACCO pays out an approved loan, within the approved amount and its confirmed funds."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.sacco_user = User.objects.get(username="sacco")
        self.loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        workflow.move(self.loan, Status.APPROVED, self.sacco_user, reason="Approved by the Board.")

    def disburse(self, username="sacco", loan=None, **overrides):
        loan = loan or self.loan
        self.client.force_login(User.objects.get(username=username))
        data = {
            "amount": 800_000,
            "disbursed_on": timezone.localdate().isoformat(),
            "method": "mobile",
            "reference": "SAMPLE-TXN-001",
        }
        data.update(overrides)
        return self.client.post(reverse("loans:loan_disburse", args=[loan.pk]), data)

    def test_sacco_official_records_a_disbursement(self):
        self.disburse()
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, Status.DISBURSED)
        self.assertEqual(self.loan.disbursement.amount, 800_000)
        self.assertEqual(self.loan.disbursement.recorded_by, self.sacco_user)
        self.assertEqual(self.loan.sacco.total_disbursed, 800_000)

    def test_cannot_pay_out_more_than_approved(self):
        response = self.disburse(amount=900_000)
        self.assertContains(response, "more than the approved UGX 800,000")
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, Status.APPROVED)

    def test_cannot_pay_out_more_than_the_sacco_holds(self):
        release = self.loan.sacco.releases.get()
        release.amount = 500_000
        release.save()
        response = self.disburse()
        self.assertContains(response, "only holds UGX 500,000")
        self.assertFalse(Disbursement.objects.exists())

    def test_unconfirmed_releases_do_not_count(self):
        self.loan.sacco.releases.update(confirmed_at=None)
        response = self.disburse()
        self.assertContains(response, "only holds UGX 0")

    def test_payment_date_cannot_be_in_the_future(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        response = self.disburse(disbursed_on=tomorrow.isoformat())
        self.assertContains(response, "cannot be in the future")

    def test_loan_not_approved_cannot_be_disbursed(self):
        isaac_loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")  # submitted
        response = self.disburse(loan=isaac_loan)
        self.assertRedirects(response, reverse("loans:loan_detail", args=[isaac_loan.pk]))
        isaac_loan.refresh_from_db()
        self.assertEqual(isaac_loan.status, Status.SUBMITTED)
        self.assertFalse(Disbursement.objects.exists())

    def test_a_loan_cannot_be_disbursed_twice(self):
        self.disburse()
        self.disburse(reference="SAMPLE-TXN-002")
        self.assertEqual(Disbursement.objects.count(), 1)

    def test_other_roles_cannot_disburse(self):
        for username in ("groupexec", "parishchief", "pdc", "district", "national", "auditor"):
            response = self.disburse(username=username)
            self.assertEqual(response.status_code, 403, username)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, Status.APPROVED)

    def test_loan_page_shows_the_disbursement(self):
        self.disburse()
        response = self.client.get(reverse("loans:loan_detail", args=[self.loan.pk]))
        self.assertContains(response, "SAMPLE-TXN-001")
        self.assertContains(response, "approved → disbursed")


class WorkflowEndToEndTests(TestCase):
    """A loan goes through every person-made step, and steps out of order are refused."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def test_full_path_from_draft_to_disbursed(self):
        groupexec = User.objects.get(username="groupexec")
        sacco = User.objects.get(username="sacco")
        isaac_loan = LoanApplication.objects.get(household__nin="CM92004567EFGH")
        loan = LoanApplication.objects.create(
            household=Household.objects.get(head_name="John Ssemwogerere"),
            enterprise_group=isaac_loan.enterprise_group,
            sacco=isaac_loan.sacco,
            amount=300_000,
            enterprise="Test",
            business_plan="Test",
        )
        workflow.move(loan, Status.SUBMITTED, groupexec)
        workflow.move(loan, Status.APPRAISED, sacco)
        workflow.move(loan, Status.APPROVED, sacco, reason="Good plan.")
        workflow.move(loan, Status.DISBURSED, sacco)
        self.assertEqual(loan.status, Status.DISBURSED)
        self.assertEqual(loan.decision_reason, "Good plan.")

    def test_wrong_status_changes_are_refused(self):
        sacco = User.objects.get(username="sacco")
        grace_loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")  # appraised
        with self.assertRaises(workflow.TransitionError):
            workflow.move(grace_loan, Status.DISBURSED, sacco)
        workflow.move(grace_loan, Status.REJECTED, sacco, reason="No market.")
        with self.assertRaises(workflow.TransitionError):
            workflow.move(grace_loan, Status.APPROVED, sacco)

    def test_disbursement_by_the_wrong_role_is_refused(self):
        grace_loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        workflow.move(grace_loan, Status.APPROVED, User.objects.get(username="sacco"))
        with self.assertRaises(PermissionDenied):
            workflow.move(grace_loan, Status.DISBURSED, User.objects.get(username="district"))
