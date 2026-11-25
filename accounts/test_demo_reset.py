"""Tests for resetting the demo data (command and admin page)."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from feedback.models import Complaint
from loans.models import LoanApplication
from registry.models import Household

from .models import User


def seed():
    call_command("seed_demo", verbosity=0, stdout=StringIO())


class ResetDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def make_a_mess(self):
        grace_loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        grace_loan.status = LoanApplication.Status.REJECTED
        grace_loan.save()
        Household.objects.filter(head_name="Florence Atim").update(verification=Household.Verification.VERIFIED)
        pdc = User.objects.get(username="pdc")
        pdc.set_password("changed-in-rehearsal")
        pdc.save()

    def test_command_needs_confirmation(self):
        with self.assertRaises(CommandError):
            call_command("reset_demo", stdout=StringIO())

    def test_reset_puts_the_sample_data_back(self):
        households, loans = Household.objects.count(), LoanApplication.objects.count()
        self.make_a_mess()
        call_command("reset_demo", "--yes", stdout=StringIO())
        self.assertEqual(Household.objects.count(), households)
        self.assertEqual(LoanApplication.objects.count(), loans)
        self.assertEqual(LoanApplication.objects.get(household__nin="CF85001234ABCD").status, LoanApplication.Status.APPRAISED)
        self.assertEqual(Household.objects.get(head_name="Florence Atim").verification, Household.Verification.PENDING)
        self.assertTrue(User.objects.get(username="pdc").check_password("pdm12345"))

    def test_numbering_restarts(self):
        call_command("reset_demo", "--yes", stdout=StringIO())
        self.assertEqual(LoanApplication.objects.order_by("pk").first().household.head_name, "Grace Nakato")
        self.assertEqual(LoanApplication.objects.order_by("pk").first().pk, 1)
        self.assertEqual(Complaint.objects.order_by("pk").first().reference, "PDM-000001")

    def test_reset_keeps_the_defaults_and_escalations(self):
        call_command("reset_demo", "--yes", stdout=StringIO())
        self.assertTrue(LoanApplication.objects.filter(status=LoanApplication.Status.DEFAULTED).exists())
        self.assertTrue(Complaint.objects.filter(escalation_count__gt=0).exists())

    def test_admin_resets_from_the_page(self):
        self.make_a_mess()
        self.client.force_login(User.objects.get(username="admin"))
        self.assertEqual(self.client.get(reverse("reset_demo")).status_code, 200)
        self.client.post(reverse("reset_demo"), {"confirm": "reset"})  # wrong: not capitals
        self.assertEqual(LoanApplication.objects.get(household__nin="CF85001234ABCD").status, LoanApplication.Status.REJECTED)
        response = self.client.post(reverse("reset_demo"), {"confirm": "RESET"})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(LoanApplication.objects.get(household__nin="CF85001234ABCD").status, LoanApplication.Status.APPRAISED)

    def test_only_the_administrator_can_reset(self):
        for username in ("national", "auditor", "sacco"):
            self.client.force_login(User.objects.get(username=username))
            self.assertEqual(self.client.post(reverse("reset_demo"), {"confirm": "RESET"}).status_code, 403, username)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("reset_demo"), {"confirm": "RESET"}).status_code, 302)


class InterruptedResetTests(TestCase):
    """A reset cut off by a server time limit must not leave numbering behind existing rows."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def test_seeding_repairs_numbering_left_behind(self):
        from django.db import connection

        from .models import SignInEvent

        SignInEvent.objects.create(username="x", succeeded=True)
        SignInEvent.objects.create(username="y", succeeded=True)
        # What an interrupted reset leaves behind: numbering restarted, rows rolled back.
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval(pg_get_serial_sequence('accounts_signinevent', 'id'), 1, false)")
        call_command("seed_demo", stdout=StringIO())
        SignInEvent.objects.create(username="z", succeeded=True)  # would collide with id 1 without the repair
        self.client.defaults["HTTP_HOST"] = "localhost"
        response = self.client.post(reverse("login"), {"username": "admin", "password": "pdm12345"})
        self.assertEqual(response.status_code, 302)
