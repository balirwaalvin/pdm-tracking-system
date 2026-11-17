"""Tests for the USSD menu (every path) and the SMS alerts."""

from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from loans import workflow
from loans.models import LoanApplication
from registry.models import Household

from .menu import MAX_LENGTH
from .models import SmsMessage
from .sms import normalise_phone, send_sms

Status = LoanApplication.Status


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class UssdMenuTests(TestCase):
    """Dial as each sample household, the way Africa's Talking would."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def dial(self, phone, text=""):
        response = self.client.post(
            reverse("ussd:callback"),
            {"sessionId": "ATUid_test", "serviceCode": "*384*1#", "phoneNumber": phone, "text": text},
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        return response.content.decode()

    def test_main_menu_greets_the_household(self):
        reply = self.dial("+256700000001")
        self.assertTrue(reply.startswith("CON "))
        self.assertIn("Grace Nakato", reply)
        self.assertIn("1. My PDM status", reply)
        self.assertIn("2. My loan", reply)

    def test_unknown_number_is_told_to_register(self):
        reply = self.dial("+256799999999")
        self.assertTrue(reply.startswith("END "))
        self.assertIn("not registered", reply)

    def test_number_formats_all_find_the_household(self):
        for phone in ("+256700000001", "256700000001", "0700000001"):
            self.assertIn("Grace Nakato", self.dial(phone), phone)

    def test_status_of_a_verified_household(self):
        reply = self.dial("+256700000001", "1")
        self.assertTrue(reply.startswith("END "))
        self.assertIn("Verified by LC I", reply)
        self.assertIn("Seeta Poultry Farmers", reply)
        self.assertIn("Seeta PDM SACCO", reply)

    def test_status_of_a_pending_household(self):
        self.assertIn("Waiting for LC I", self.dial("+256700000012", "1"))  # Florence

    def test_status_of_a_rejected_household_gives_the_reason(self):
        florence = Household.objects.get(phone="256700000012")
        florence.verification = Household.Verification.REJECTED
        florence.verification_note = "Does not live in this village."
        florence.save()
        self.assertIn("Not verified: Does not live in this village.", self.dial("+256700000012", "1"))

    def test_household_without_a_group(self):
        self.assertIn("Not yet in an enterprise group", self.dial("+256700000016", "1"))  # Betty

    def test_no_loan(self):
        self.assertIn("no PDM loan application", self.dial("+256700000012", "2"))

    def test_loan_waiting_for_a_decision(self):
        self.assertIn("with Seeta PDM SACCO for a decision", self.dial("+256700000001", "2"))

    def test_draft_loan(self):
        LoanApplication.objects.filter(household__phone="256700000001").update(status=Status.DRAFT)
        self.assertIn("draft with your group executive", self.dial("+256700000001", "2"))

    def test_approved_loan(self):
        self.assertIn("is approved", self.dial("+256700000021", "2"))  # Ronald

    def test_rejected_loan_gives_the_reason(self):
        reply = self.dial("+256700000020", "2")  # Sylvia
        self.assertIn("was not approved. Reason: Phone repair", reply)
        self.assertLessEqual(len(reply), MAX_LENGTH)
        self.assertTrue(reply.endswith("…"))

    def test_loan_being_repaid_shows_the_next_instalment(self):
        reply = self.dial("+256700000019", "2")  # Moses: up to date
        self.assertIn("Balance UGX", reply)
        self.assertIn("Next UGX", reply)

    def test_loan_in_arrears_shows_what_is_overdue(self):
        reply = self.dial("+256700000023", "2")  # Henry
        self.assertIn("Overdue UGX", reply)
        self.assertNotIn("In default", reply)

    def test_defaulted_loan(self):
        self.assertIn("In default", self.dial("+256700000022", "2"))  # Joyce

    def test_closed_loan(self):
        LoanApplication.objects.filter(household__phone="256700000019").update(status=Status.CLOSED)
        self.assertIn("fully repaid", self.dial("+256700000019", "2"))

    def test_invalid_choice(self):
        self.assertIn("Invalid choice", self.dial("+256700000001", "7"))

    def test_callback_refuses_get(self):
        self.assertEqual(self.client.get(reverse("ussd:callback"), HTTP_HOST="localhost").status_code, 405)

    def test_every_reply_fits_one_screen(self):
        for phone in Household.objects.exclude(phone="").values_list("phone", flat=True):
            for text in ("", "1", "2"):
                self.assertLessEqual(len(self.dial(phone, text)), MAX_LENGTH, (phone, text))


class SmsServiceTests(TestCase):
    def test_phone_numbers_are_normalised(self):
        self.assertEqual(normalise_phone("+256 700 000001"), "256700000001")
        self.assertEqual(normalise_phone("0700000001"), "256700000001")
        self.assertEqual(normalise_phone(""), "")

    @override_settings(AT_API_KEY="")
    def test_without_a_key_the_message_is_logged_not_sent(self):
        with mock.patch("africastalking.SMS") as sms:
            message = send_sms("0700000001", "Hello")
        sms.send.assert_not_called()
        self.assertEqual(message.status, SmsMessage.Status.LOGGED)
        self.assertEqual(message.phone, "256700000001")

    @override_settings(AT_API_KEY="test-key", AT_USERNAME="sandbox", AT_SENDER_ID="")
    def test_with_a_key_the_message_is_sent(self):
        with mock.patch("africastalking.initialize"), mock.patch("africastalking.SMS", create=True) as sms:
            message = send_sms("256700000001", "Hello")
        sms.send.assert_called_once_with("Hello", ["+256700000001"], None)
        self.assertEqual(message.status, SmsMessage.Status.SENT)

    @override_settings(AT_API_KEY="test-key")
    def test_a_failure_is_logged_not_raised(self):
        with mock.patch("africastalking.initialize", side_effect=RuntimeError("network down")):
            message = send_sms("256700000001", "Hello")
        self.assertEqual(message.status, SmsMessage.Status.FAILED)
        self.assertIn("network down", message.error)

    def test_no_phone_number_sends_nothing(self):
        self.assertIsNone(send_sms("", "Hello"))
        self.assertFalse(SmsMessage.objects.exists())


@override_settings(AT_API_KEY="")
class LoanAlertTests(TestCase):
    """The household gets a text when its loan is decided, paid out and repaid."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.force_login(User.objects.get(username="sacco"))
        self.loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")  # Grace, appraised

    def post(self, name, data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse(name, args=[self.loan.pk]), data, HTTP_HOST="localhost")

    def texts(self):
        return list(SmsMessage.objects.filter(loan=self.loan).order_by("pk").values_list("message", flat=True))

    def test_approval_sends_a_text(self):
        self.post("loans:loan_decide", {"decision": "approve"})
        self.assertEqual(len(self.texts()), 1)
        self.assertIn("approved", self.texts()[0])
        self.assertEqual(SmsMessage.objects.get(loan=self.loan).phone, "256700000001")

    def test_rejection_sends_a_text(self):
        self.post("loans:loan_decide", {"decision": "reject", "reason": "No market."})
        self.assertIn("not approved", self.texts()[0])

    def test_refused_decision_sends_nothing(self):
        self.post("loans:loan_decide", {"decision": "reject", "reason": ""})
        self.assertEqual(self.texts(), [])

    def test_payout_and_repayment_send_texts(self):
        today = timezone.localdate().isoformat()
        self.post("loans:loan_decide", {"decision": "approve"})
        self.post("loans:loan_disburse", {"amount": 800_000, "disbursed_on": today, "method": "mobile", "reference": "T9"})
        self.post("loans:loan_repay", {"amount": 70_666, "paid_on": today, "method": "cash", "reference": "R9"})
        approval, payout, repayment = self.texts()
        self.assertIn("UGX 800,000 has been paid to you", payout)
        self.assertIn("First instalment UGX 70,666", payout)
        self.assertIn("received UGX 70,666", repayment)
        self.assertIn("Balance UGX 777,334", repayment)

    def test_full_repayment_text_says_the_loan_is_repaid(self):
        today = timezone.localdate().isoformat()
        workflow.move(self.loan, Status.APPROVED, User.objects.get(username="sacco"))
        self.post("loans:loan_disburse", {"amount": 800_000, "disbursed_on": today, "method": "bank", "reference": "T9"})
        self.post("loans:loan_repay", {"amount": 848_000, "paid_on": today, "method": "bank", "reference": "R9"})
        self.assertIn("fully repaid", self.texts()[-1])

    def test_texts_fit_in_one_sms(self):
        self.test_payout_and_repayment_send_texts()
        for text in self.texts():
            self.assertLessEqual(len(text), 160, text)
