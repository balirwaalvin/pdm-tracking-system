"""The whole PDM customer journey, end to end through the web pages, one role at a time.

1 Register  2 Verify  3 Group  4 Apply  5 Appraise  6 Decide (maker-checker) and pay out
7 Repay  8 Check by USSD and SMS  9 Speak up (complaint and story)  10 Oversee
"""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from feedback.models import Complaint, SuccessStory
from loans.models import LoanApplication
from registry.models import AdminUnit, EnterpriseGroup, Household
from ussd.models import SmsMessage

Status = LoanApplication.Status


class CustomerJourneyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))

    def as_(self, username):
        self.client.force_login(User.objects.get(username=username))

    def post(self, name, data=None, *args):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse(name, args=args), data or {})
        self.assertLess(response.status_code, 400, f"{name}: {response.status_code}")
        return response

    def test_the_whole_journey(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        today = timezone.localdate().isoformat()
        seeta = AdminUnit.objects.get(name="Seeta")

        # 3. Group: the CDO registers a group; it is linked to the parish SACCO.
        self.as_("subcounty")
        self.post("registry:group_create", {"name": "Seeta Mushroom Growers", "enterprise": "other",
                                            "parish": seeta.pk, "registration_number": "GOMA/EG/099"})
        group = EnterpriseGroup.objects.get(name="Seeta Mushroom Growers")
        self.assertEqual(group.sacco.name, "Seeta PDM SACCO")

        # 1. Register: the Parish Chief profiles a household.
        self.as_("parishchief")
        self.post("registry:household_create", {
            "head_name": "Agatha Namusoke", "nin": "cf90001111wxyz", "phone": "0772 555111", "sex": "F",
            "age_group": "youth", "household_size": 4, "wealth_rank": "very_poor",
            "village": AdminUnit.objects.get(name="Seeta Central").pk, "enterprise_group": group.pk,
        })
        household = Household.objects.get(nin="CF90001111WXYZ")
        self.assertEqual(household.phone, "256772555111")
        self.assertEqual(household.verification, Household.Verification.PENDING)

        # 2. Verify: the LC I chairperson confirms her.
        self.as_("lc1")
        self.post("registry:household_verify", {"decision": "verify"}, household.pk)
        household.refresh_from_db()
        self.assertEqual(household.verification, Household.Verification.VERIFIED)

        # 4. Apply: the group executive applies and submits.
        self.as_("groupexec")
        self.post("loans:loan_create", {"household": household.pk, "amount": 400_000, "enterprise": "Oyster mushrooms",
                                        "business_plan": "Grow oyster mushrooms and sell to hotels.", "term_months": 6})
        loan = LoanApplication.objects.get(household=household)
        self.post("loans:loan_submit", {}, loan.pk)

        # 5. Appraise: one SACCO official scores it.
        self.as_("sacco")
        self.post("loans:loan_appraise", {"viability_score": 4, "repayment_score": 4, "group_score": 5,
                                          "recommendation": "approve", "reasons": "Hotels have agreed to buy."}, loan.pk)

        # 6. Decide: the appraiser cannot approve; the Board chair does. Then the payout.
        self.post("loans:loan_decide", {"decision": "approve"}, loan.pk)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Status.APPRAISED)  # maker-checker held
        self.as_("saccochair")
        self.post("loans:loan_decide", {"decision": "approve"}, loan.pk)
        self.as_("sacco")
        self.post("loans:loan_disburse", {"amount": 400_000, "disbursed_on": today, "method": "mobile", "reference": "J-1"}, loan.pk)

        # 7. Repay: a repayment moves it to Repaying, with a receipt.
        self.post("loans:loan_repay", {"amount": 70_000, "paid_on": today, "method": "cash", "reference": "J-R1"}, loan.pk)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Status.REPAYING)
        self.assertEqual(loan.total_due, 412_000)

        # 8. Check: USSD shows the balance; SMS alerts were sent at each step.
        reply = self.client.post(reverse("ussd:callback"), {"phoneNumber": "+256772555111", "text": "2"}).content.decode()
        self.assertIn("Balance UGX 342,000", reply)
        texts = list(SmsMessage.objects.filter(loan=loan).values_list("message", flat=True))
        self.assertEqual(len(texts), 3)  # approved, paid out, repayment with receipt
        self.assertTrue(any("RCPT-" in t for t in texts))

        # 9. Speak up: a complaint by USSD, answered by the Parish Chief; a story checked by the PDC.
        self.client.post(reverse("ussd:callback"), {"phoneNumber": "+256772555111", "text": "3*3*My cash payment is missing"})
        complaint = Complaint.objects.get(household=household)
        self.as_("parishchief")
        self.post("feedback:complaint_respond", {"status": "resolved", "message": "Found and recorded."}, complaint.pk)
        self.post("feedback:story_create", {"household": household.pk, "title": "Mushrooms for Seeta hotels",
                                            "story": "Agatha now supplies three hotels.", "consent_given": "on",
                                            "consent_method": "signed", "show_name": "on"})
        story = SuccessStory.objects.get(household=household)
        self.post("feedback:story_submit", {}, story.pk)
        self.as_("pdc")
        self.post("feedback:story_check", {"decision": "approve", "records_match": "on"}, story.pk)
        self.client.logout()
        public = self.client.get(reverse("public_parish", args=[seeta.pk])).content.decode()
        self.assertIn("Mushrooms for Seeta hotels", public)
        self.assertNotIn("CF90001111WXYZ", public)

        # 10. Oversee: the national dashboard counts her loan; the auditor sees who did each step.
        self.as_("national")
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.as_("auditor")
        log = self.client.get(reverse("audit_log"), {"q": "Agatha"}).content.decode()
        for actor in ("Sarah Namubiru", "Joseph Mukasa"):  # Parish Chief registered, LC I verified
            self.assertIn(actor, log)
