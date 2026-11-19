"""docs/DEMO.md, step by step, after a reset. If the demo script stops working, this fails."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from feedback.models import Complaint, SuccessStory
from loans.models import LoanApplication
from registry.models import AdminUnit, Household
from saccos.models import FundRelease

Status = LoanApplication.Status


class DemoScriptTest(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("reset_demo", "--yes", stdout=StringIO())
        self.client.defaults["HTTP_HOST"] = "localhost"

    def as_(self, username):
        self.client.force_login(User.objects.get(username=username))

    def post(self, name, data=None, *args):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse(name, args=args), data or {})

    def test_the_demo_script(self):
        today = timezone.localdate().isoformat()
        seeta = AdminUnit.objects.get(name="Seeta")
        florence = Household.objects.get(head_name="Florence Atim")

        # Starting state
        self.assertEqual(florence.verification, Household.Verification.PENDING)
        self.assertEqual(LoanApplication.objects.get(pk=1).household.head_name, "Grace Nakato")
        self.assertEqual(LoanApplication.objects.get(pk=3).status, Status.APPROVED)
        self.assertEqual(LoanApplication.objects.get(pk=7).status, Status.DEFAULTED)
        self.assertEqual(Complaint.objects.get(pk=4).escalation_count, 1)
        release = FundRelease.objects.get(financial_year="2026/27")
        self.assertIsNone(release.confirmed_at)

        # 0. Signed out: landing and the public parish page
        self.assertContains(self.client.get(reverse("home")), "See your parish")
        self.assertContains(self.client.get(reverse("public_parish", args=[seeta.pk])), "Seeta parish")

        # 1. Parish Chief: a duplicate NIN is refused and named
        self.as_("parishchief")
        response = self.post("registry:household_create", {"head_name": "X", "nin": "CF85001234ABCD", "sex": "F",
                                                          "age_group": "adult", "household_size": 2, "wealth_rank": "poor",
                                                          "village": florence.village_id})
        self.assertContains(response, "already registered to")

        # 2. LC I: one household to verify, Florence confirmed
        self.as_("lc1")
        tasks = {t["label"]: t["count"] for t in self.client.get(reverse("home")).context["tasks"]}
        self.assertEqual(tasks["Households waiting for you to verify"], 1)
        self.post("registry:household_verify", {"decision": "verify"}, florence.pk)

        # 3. Sub-county: the group is linked to the SACCO
        self.assertEqual(florence.enterprise_group.sacco.name, "Seeta PDM SACCO")

        # 4. Group executive applies and submits
        self.as_("groupexec")
        self.post("loans:loan_create", {"household": florence.pk, "amount": 600000, "enterprise": "Layer chickens",
                                        "business_plan": "Eggs for the market.", "term_months": 12})
        loan = LoanApplication.objects.get(household=florence)
        self.post("loans:loan_submit", {}, loan.pk)

        # 5. sacco appraises and is not offered the decision
        self.as_("sacco")
        self.post("loans:loan_appraise", {"viability_score": 4, "repayment_score": 4, "group_score": 4,
                                          "recommendation": "approve", "reasons": "Good plan."}, loan.pk)
        self.assertContains(self.client.get(reverse("loans:loan_detail", args=[loan.pk])), "another SACCO official must approve")

        # 6. saccochair approves and pays out
        self.as_("saccochair")
        self.post("loans:loan_decide", {"decision": "approve"}, loan.pk)
        self.post("loans:loan_disburse", {"amount": 600000, "disbursed_on": today, "method": "mobile", "reference": "DEMO-001"}, loan.pk)
        detail = self.client.get(reverse("loans:loan_detail", args=[loan.pk]))
        self.assertContains(detail, "has been approved")
        self.assertContains(detail, "has been paid to you")

        # 7. Repayment of 53,000 (one instalment) moves it to Repaying, with a receipt
        self.post("loans:loan_repay", {"amount": 53000, "paid_on": today, "method": "cash", "reference": "R-001"}, loan.pk)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Status.REPAYING)
        self.assertEqual(loan.schedule_with_status()[0]["state"], "paid")
        self.assertContains(self.client.get(reverse("loans:arrears_list")), "Henry Mubiru")

        # 8. USSD as Florence: loan, Luganda, and a bribery report
        self.as_("parishchief")
        sim = reverse("ussd:simulator")
        self.client.post(sim, {"phone": florence.phone, "action": "dial"})
        self.assertContains(self.client.post(sim, {"phone": florence.phone, "session_text": "", "answer": "2", "action": "send"}), "Next UGX")
        self.client.post(sim, {"phone": florence.phone, "action": "dial"})
        self.assertContains(self.client.post(sim, {"phone": florence.phone, "session_text": "", "answer": "0", "action": "send"}), "Looni yange")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(sim, {"phone": florence.phone, "session_text": "3*5", "answer": "Someone asked me for 20000", "action": "send"})
        complaint = Complaint.objects.get(pk=6)
        self.assertEqual(complaint.reference, "PDM-000006")
        self.assertEqual(complaint.level, Complaint.Level.SUBCOUNTY)

        # 9. Sub-county resolves it; the PDC approves Ronald's story; it is public without his full name
        self.as_("subcounty")
        self.post("feedback:complaint_respond", {"status": "resolved", "message": "Reported to the CDO and police."}, complaint.pk)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.RESOLVED)
        self.as_("pdc")
        story = SuccessStory.objects.get(title="A sty built by the group")
        self.post("feedback:story_check", {"decision": "approve", "records_match": "on"}, story.pk)
        self.client.logout()
        public = self.client.get(reverse("public_parish", args=[seeta.pk]))
        self.assertContains(public, "A sty built by the group")
        self.assertContains(public, "Ronald of Bajjo")
        self.assertNotContains(public, "Ronald Lubega")

        # 10. District confirms the release; national dashboard and report; auditor sees names
        self.as_("district")
        self.post("saccos:release_confirm", {}, release.pk)
        release.refresh_from_db()
        self.assertIsNotNone(release.confirmed_at)
        self.as_("national")
        self.assertContains(self.client.get(reverse("dashboard")), "Wakiso")
        self.assertEqual(self.client.get(reverse("quarterly_report")).status_code, 200)
        self.as_("auditor")
        log = self.client.get(reverse("audit_log"), {"q": "Florence"}).content.decode()
        self.assertIn("Joseph Mukasa", log)  # the LC I who verified her
