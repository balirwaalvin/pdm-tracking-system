"""The Day 10 security check, as tests that cover every URL in the project.

- Signed out: every page except the public ones sends you to sign in.
- Cross-parish: officials cannot open or change records outside their area.
- CSRF: forms refuse posts without the token.
- The USSD callback can be locked with a token.
New pages are picked up automatically, because the sweep reads the URL list.
"""

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from accounts.models import User
from feedback.models import Complaint
from loans.models import LoanApplication
from registry.models import EnterpriseGroup, Household
from saccos.models import Sacco

# Pages anyone may open without signing in.
PUBLIC = {"home", "login", "public_parishes", "public_parish", "public_parish_data", "ussd:callback"}


def all_named_urls(resolver=None, namespace=""):
    """Every named URL pattern as (name, pattern), with namespaces."""
    resolver = resolver or get_resolver()
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            ns = f"{namespace}{entry.namespace}:" if entry.namespace else namespace
            if entry.app_name == "admin":
                continue
            yield from all_named_urls(entry, ns)
        elif isinstance(entry, URLPattern) and entry.name:
            yield f"{namespace}{entry.name}", entry.pattern


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class SignedOutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_every_private_page_sends_you_to_sign_in(self):
        client = Client(HTTP_HOST="localhost")
        checked = 0
        for name, pattern in all_named_urls():
            if name in PUBLIC:
                continue
            kwargs = {key: 1 for key in pattern.regex.groupindex}
            url = reverse(name, kwargs=kwargs)
            response = client.get(url)
            if response.status_code == 405:  # POST-only actions: try a post instead
                response = client.post(url)
            self.assertEqual(response.status_code, 302, f"{name} ({url}) answered {response.status_code}")
            self.assertIn(reverse("login"), response.url, name)
            checked += 1
        self.assertGreater(checked, 40)

    def test_public_pages_open_without_sign_in(self):
        client = Client(HTTP_HOST="localhost")
        for name in ("home", "login", "public_parishes"):
            self.assertEqual(client.get(reverse(name)).status_code, 200, name)


class CrossParishTests(TestCase):
    """Seeta officials against Nantabulirwa (same sub-county) and Wakiso (another district) records."""

    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.annet = Household.objects.get(head_name="Annet Nakiyimba")  # Nantabulirwa parish
        self.wakiso_loan = LoanApplication.objects.filter(household__village__parent__name="Kyengera").first()

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def assertRefused(self, response, label):
        self.assertIn(response.status_code, (403, 404), f"{label}: {response.status_code}")

    def test_reading_records_in_another_parish_is_refused(self):
        group = EnterpriseGroup.objects.get(name="Nantabulirwa Coffee Growers")
        sacco = Sacco.objects.get(name="Nantabulirwa PDM SACCO")
        complaint = Complaint.objects.get(household=self.annet)
        pages = [
            ("registry:household_detail", self.annet.pk),
            ("registry:household_edit", self.annet.pk),
            ("registry:group_detail", group.pk),
            ("saccos:sacco_detail", sacco.pk),
            ("loans:loan_detail", self.wakiso_loan.pk),
            ("feedback:complaint_detail", complaint.pk),
        ]
        for username in ("parishchief", "pdc", "sacco", "lc1"):
            self.login(username)
            for name, pk in pages:
                self.assertRefused(self.client.get(reverse(name, args=[pk])), f"{username} {name}")

    def test_changing_records_in_another_area_is_refused(self):
        self.login("lc1")
        self.assertRefused(self.client.post(reverse("registry:household_verify", args=[self.annet.pk]),
                                            {"decision": "verify"}), "verify")
        self.login("saccochair")
        self.assertRefused(self.client.post(reverse("loans:loan_decide", args=[self.wakiso_loan.pk]),
                                            {"decision": "approve"}), "decide")
        self.assertRefused(self.client.post(reverse("loans:loan_repay", args=[self.wakiso_loan.pk]),
                                            {"amount": 1000, "paid_on": "2026-11-01", "method": "cash", "reference": "X"}), "repay")
        self.login("subcounty")  # Goma: Wakiso complaints are outside the sub-county
        wakiso_household = self.wakiso_loan.household
        from feedback.services import raise_complaint
        complaint = raise_complaint(wakiso_household, Complaint.Category.BRIBERY, "Asked for money at the office.")
        self.assertRefused(self.client.post(reverse("feedback:complaint_respond", args=[complaint.pk]),
                                            {"status": "resolved", "message": "x"}), "respond")
        self.annet.refresh_from_db()
        self.assertNotEqual(self.annet.verification, Household.Verification.VERIFIED)
        self.assertFalse(complaint.responses.exists())

    def test_lists_and_exports_leave_out_other_areas(self):
        self.login("parishchief")
        for name in ("registry:household_list", "loans:loan_list", "feedback:complaint_list"):
            body = self.client.get(reverse(name), {"format": "csv"}).content.decode()
            self.assertNotIn("Annet Nakiyimba", body, name)
            self.assertNotIn("Sarah Nalubega", body, name)  # Wakiso


class CsrfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_posts_without_the_token_are_refused(self):
        client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
        client.force_login(User.objects.get(username="saccochair"))
        loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        self.assertEqual(client.post(reverse("loans:loan_decide", args=[loan.pk]), {"decision": "approve"}).status_code, 403)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanApplication.Status.APPRAISED)

    def test_sign_in_needs_the_token(self):
        client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)
        response = client.post(reverse("login"), {"username": "sacco", "password": "pdm12345"})
        self.assertEqual(response.status_code, 403)


class UssdTokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def post(self, token=None):
        url = reverse("ussd:callback") + (f"?token={token}" if token is not None else "")
        return self.client.post(url, {"phoneNumber": "+256700000001", "text": ""}, HTTP_HOST="localhost")

    @override_settings(USSD_CALLBACK_TOKEN="s3cret-token")
    def test_token_is_required_when_set(self):
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.post("wrong").status_code, 403)
        response = self.post("s3cret-token")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Grace Nakato", response.content.decode())

    @override_settings(USSD_CALLBACK_TOKEN="")
    def test_open_when_no_token_is_set(self):
        self.assertEqual(self.post().status_code, 200)


class ProductionSettingsTests(TestCase):
    def test_deploy_check_passes_with_production_settings(self):
        from io import StringIO

        with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=3600,
                               SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
                               SECRET_KEY="a-long-random-production-like-secret-key-for-the-check-0123456789"):
            out = StringIO()
            call_command("check", "--deploy", stdout=out, stderr=out)
        self.assertIn("no issues", out.getvalue())
