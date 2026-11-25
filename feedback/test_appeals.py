"""Tests for appeals against rejected loans, the eligibility checks and the mock identity check."""

import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from loans import workflow
from loans.models import LoanApplication
from registry.eligibility import household_checklist, screen
from registry.mock_register import MATCHED, NAME_DIFFERS, NOT_FOUND, check_identity
from registry.models import Household
from ussd.models import SmsMessage

from .models import Appeal

Status = LoanApplication.Status


class AppealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.loan = LoanApplication.objects.get(household__head_name="Sylvia Nambi")  # rejected 5 days ago

    def as_(self, username):
        self.client.force_login(User.objects.get(username=username))

    def file(self, username="sylvia", grounds="I now have a poultry plan that fits PDM."):
        self.as_(username)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("feedback:appeal_create", args=[self.loan.pk]), {"grounds": grounds})

    def decide(self, decision, note="Looked again at the plan."):
        appeal = Appeal.objects.get(loan=self.loan)
        self.as_("subcounty")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("feedback:appeal_decide", args=[appeal.pk]), {"decision": decision, "note": note})
        appeal.refresh_from_db()
        self.loan.refresh_from_db()
        return appeal

    def test_household_appeals_its_own_rejection(self):
        response = self.file()
        self.assertRedirects(response, reverse("my_household"))
        appeal = Appeal.objects.get(loan=self.loan)
        self.assertEqual(appeal.status, Appeal.Status.PENDING)
        self.assertIn(appeal.reference, SmsMessage.objects.latest("pk").message)

    def test_group_executive_can_appeal_for_a_member(self):
        self.file("groupexec")
        self.assertTrue(Appeal.objects.filter(loan=self.loan).exists())

    def test_appeal_needs_grounds(self):
        self.file(grounds="no")
        self.assertFalse(Appeal.objects.filter(loan=self.loan).exists())

    def test_only_one_appeal_per_rejection(self):
        self.file()
        self.file(grounds="A second appeal for the same decision.")
        self.assertEqual(Appeal.objects.filter(loan=self.loan).count(), 1)

    def test_no_appeal_after_30_days(self):
        LoanApplication.objects.filter(pk=self.loan.pk).update(decided_at=timezone.now() - datetime.timedelta(days=31))
        self.file()
        self.assertFalse(Appeal.objects.filter(loan=self.loan).exists())

    def test_other_households_and_roles_cannot_appeal(self):
        self.file("household")  # Grace, not Sylvia
        self.assertFalse(Appeal.objects.filter(loan=self.loan).exists())
        self.as_("sacco")
        self.assertEqual(self.client.get(reverse("feedback:appeal_create", args=[self.loan.pk])).status_code, 403)

    def test_only_rejected_loans_can_be_appealed(self):
        grace_loan = LoanApplication.objects.get(household__head_name="Grace Nakato")  # appraised
        self.as_("household")
        self.client.post(reverse("feedback:appeal_create", args=[grace_loan.pk]), {"grounds": "Please look again soon."})
        self.assertFalse(Appeal.objects.filter(loan=grace_loan).exists())

    def test_upheld_appeal_sends_the_loan_back_to_the_sacco(self):
        self.file()
        appeal = self.decide("refer")
        self.assertEqual(appeal.status, Appeal.Status.REFERRED)
        self.assertEqual(self.loan.status, Status.APPRAISED)
        self.assertIn("upheld", SmsMessage.objects.latest("pk").message)
        # Maker-checker still applies to the fresh decision.
        self.assertFalse(workflow.can_move(self.loan, Status.APPROVED, User.objects.get(username="sacco")))
        workflow.move(self.loan, Status.APPROVED, User.objects.get(username="saccochair"))

    def test_dismissed_appeal_keeps_the_rejection(self):
        self.file()
        appeal = self.decide("dismiss", "Phone repair is still outside the parish plan.")
        self.assertEqual(appeal.status, Appeal.Status.DISMISSED)
        self.assertEqual(self.loan.status, Status.REJECTED)
        self.assertIn("dismissed", SmsMessage.objects.latest("pk").message)

    def test_decision_needs_a_reason_and_the_right_role(self):
        self.file()
        appeal = self.decide("refer", note="")
        self.assertEqual(appeal.status, Appeal.Status.PENDING)
        for username in ("parishchief", "sacco", "national", "auditor"):
            self.as_(username)
            response = self.client.post(reverse("feedback:appeal_decide", args=[appeal.pk]), {"decision": "refer", "note": "x"})
            self.assertEqual(response.status_code, 403, username)

    def test_subcounty_sees_appeals_to_decide(self):
        self.file()
        self.as_("subcounty")
        tasks = {t["label"]: t["count"] for t in self.client.get(reverse("home")).context["tasks"]}
        self.assertEqual(tasks["Appeals to decide"], 1)

    def test_reset_clears_appeals(self):
        self.file()
        call_command("reset_demo", "--yes", stdout=StringIO())
        self.assertFalse(Appeal.objects.exists())


class EligibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_screening(self):
        self.assertEqual(screen({"adult_head": "yes", "resident": "yes", "subsistence": "yes", "group": "yes"}), (True, []))
        likely, gaps = screen({"adult_head": "yes", "resident": "yes", "subsistence": "no", "group": "no"})
        self.assertFalse(likely)
        self.assertEqual(len(gaps), 2)

    def test_public_page_needs_no_sign_in_and_stores_nothing(self):
        households = Household.objects.count()
        response = self.client.post(reverse("eligibility"), {"adult_head": "yes", "resident": "yes", "subsistence": "yes", "group": "yes"}, HTTP_HOST="localhost")
        self.assertContains(response, "likely to be eligible")
        self.assertEqual(Household.objects.count(), households)

    def test_household_checklist(self):
        florence = {i["label"]: i["ok"] for i in household_checklist(Household.objects.get(head_name="Florence Atim"))}
        self.assertFalse(florence["Confirmed by your LC I chairperson"])
        christine = {i["label"]: i["ok"] for i in household_checklist(Household.objects.get(head_name="Christine Namale"))}
        self.assertTrue(all(christine.values()))

    def test_checklist_on_my_household(self):
        self.client.force_login(User.objects.get(username="florence"))
        self.assertContains(self.client.get(reverse("my_household"), HTTP_HOST="localhost"), "My PDM eligibility")


class MockIdentityTests(TestCase):
    def test_results(self):
        self.assertEqual(check_identity("CF85001234ABCD", "Grace  Nakato")[0], MATCHED)
        self.assertEqual(check_identity("cf85001234abcd", "Grace Namata")[0], NAME_DIFFERS)
        self.assertEqual(check_identity("CX00000000ZZZZ", "Nobody")[0], NOT_FOUND)
