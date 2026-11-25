"""The extra household logins: each is linked to its own record, and a new loan can be run for any of them."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.management.commands.seed_demo import HOUSEHOLD_ACCOUNTS
from accounts.models import User
from loans.models import LoanApplication
from registry.models import Household
from ussd.models import SmsMessage


class HouseholdAccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def as_(self, username):
        self.client.force_login(User.objects.get(username=username))

    def test_every_household_login_sees_only_its_own_record(self):
        names = {nin: Household.objects.get(nin=nin).head_name for _, nin in HOUSEHOLD_ACCOUNTS}
        for username, nin in HOUSEHOLD_ACCOUNTS:
            self.as_(username)
            response = self.client.get(reverse("my_household"))
            self.assertContains(response, names[nin], msg_prefix=username)
            for other_nin, other_name in names.items():
                if other_nin != nin:
                    self.assertNotContains(response, other_name, msg_prefix=f"{username} sees {other_name}")
            sim = self.client.get(reverse("ussd:simulator"))
            self.assertContains(sim, Household.objects.get(nin=nin).phone, msg_prefix=username)

    def test_each_login_has_the_household_role_and_password(self):
        for username, nin in HOUSEHOLD_ACCOUNTS:
            user = User.objects.get(username=username)
            self.assertEqual(user.role, "Household", username)
            self.assertTrue(user.check_password("pdm12345"), username)
            self.assertEqual(user.household_record.nin, nin)

    def test_the_accounts_survive_a_reset(self):
        call_command("reset_demo", "--yes", stdout=StringIO())
        for username, nin in HOUSEHOLD_ACCOUNTS:
            self.assertEqual(User.objects.get(username=username).household_record.nin, nin)

    def post(self, name, data, *args):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse(name, args=args), data)
        self.assertLess(response.status_code, 400, name)
        return response

    def test_a_second_full_loan_for_christine(self):
        today = timezone.localdate().isoformat()
        christine = Household.objects.get(nin="CF89004713DEFG")
        self.as_("christine")
        self.assertContains(self.client.get(reverse("my_household")), "No loan application yet")

        self.as_("groupexec")
        self.post("loans:loan_create", {"household": christine.pk, "amount": 500000, "enterprise": "Piglets",
                                        "business_plan": "Raise and sell piglets.", "term_months": 10})
        loan = LoanApplication.objects.get(household=christine)
        self.post("loans:loan_submit", {}, loan.pk)
        self.as_("sacco")
        self.post("loans:loan_appraise", {"viability_score": 4, "repayment_score": 3, "group_score": 4,
                                          "recommendation": "approve", "reasons": "Sound plan."}, loan.pk)
        self.as_("saccochair")
        self.post("loans:loan_decide", {"decision": "approve"}, loan.pk)
        self.post("loans:loan_disburse", {"amount": 500000, "disbursed_on": today, "method": "mobile", "reference": "MM-1"}, loan.pk)
        self.post("loans:loan_repay", {"amount": 52500, "paid_on": today, "method": "cash", "reference": "R-1"}, loan.pk)

        self.as_("christine")
        page = self.client.get(reverse("my_household")).content.decode()
        self.assertIn("UGX 500,000", page)
        self.assertIn("RCPT-", page)  # her receipt
        self.assertIn("has been paid to you", page)  # her SMS alerts
        self.assertEqual(SmsMessage.objects.filter(loan=loan).count(), 3)
        reply = self.client.post(reverse("ussd:simulator"), {"phone": christine.phone, "session_text": "", "answer": "2", "action": "send"})
        self.assertContains(reply, "Balance UGX 472,500")

    def test_patrick_is_ready_to_apply(self):
        self.as_("groupexec")
        form = self.client.get(reverse("loans:loan_create")).context["form"]
        offered = [h.head_name for h in form.fields["household"].queryset]
        self.assertIn("Patrick Wasswa", offered)
        self.assertIn("Christine Namale", offered)
