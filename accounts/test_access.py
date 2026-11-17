"""The access policy is enforced: every role's menu links open, and every other page is refused.

This is the role-based access check for the whole system. If a view and the
policy in accounts/access.py ever disagree, these tests fail.
"""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts import access
from accounts.models import User
from registry.models import Household

# demo username -> role (one per role)
USERS = ["household", "groupexec", "lc1", "parishchief", "pdc", "sacco", "subcounty", "district", "national", "auditor"]


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class AccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_every_page_opens_for_allowed_roles_and_is_refused_to_others(self):
        for username in USERS:
            user = User.objects.get(username=username)
            self.client.force_login(user)
            for page in access.PAGES:
                status = self.client.get(reverse(page.url_name)).status_code
                expected = 200 if access.allows(user, page.key) else 403
                self.assertEqual(status, expected, f"{username} → {page.label}")

    def test_menu_shows_exactly_the_allowed_pages(self):
        for username in USERS:
            user = User.objects.get(username=username)
            self.client.force_login(user)
            response = self.client.get(reverse("home"))
            menu = [item.key for item in response.context["menu"]]
            self.assertEqual(menu, [page.key for page in access.PAGES if access.allows(user, page.key)], username)
            for page in access.PAGES:
                link = f'href="{reverse(page.url_name)}"'
                if page.key not in menu:
                    self.assertNotIn(f'class="nav-link" {link}', response.content.decode(), f"{username}: {page.label}")

    def test_logged_out_users_are_sent_to_login_everywhere(self):
        self.client.logout()
        for page in access.PAGES:
            response = self.client.get(reverse(page.url_name))
            self.assertEqual(response.status_code, 302, page.label)
            self.assertIn(reverse("login"), response.url)

    def test_every_role_has_a_summary_and_at_least_one_page(self):
        for username in USERS:
            user = User.objects.get(username=username)
            self.assertTrue(access.pages_for(user), username)
            self.assertNotIn("No role", access.summary_for(user), username)

    def test_least_privilege_for_sensitive_pages(self):
        # Household records (with NINs) stay with the parish and sub-county, not district or national.
        self.assertNotIn("district", [u for u in USERS if access.allows(User.objects.get(username=u), "households")])
        self.assertFalse(access.allows(User.objects.get(username="national"), "households"))
        # Only the auditor reads the audit log; the household sees only its own page.
        self.assertEqual([u for u in USERS if access.allows(User.objects.get(username=u), "audit_log")], ["auditor"])
        self.assertEqual([p.key for p in access.pages_for(User.objects.get(username="household"))], ["my_household"])


class WorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def home(self, username):
        self.client.force_login(User.objects.get(username=username))
        return self.client.get(reverse("home"))

    def test_each_role_sees_its_own_work(self):
        expected = {
            "lc1": "Households waiting for you to verify",
            "parishchief": "Rejected households to correct",
            "groupexec": "Draft applications to submit",
            "pdc": "Loans waiting for the SACCO",
            "sacco": "Approved loans to pay out",
            "subcounty": "Groups not linked to a SACCO",
            "district": "Fund releases to confirm",
            "national": "Eligible SACCOs with no fund release",
            "auditor": "Changes recorded today",
        }
        for username, task in expected.items():
            response = self.home(username)
            self.assertContains(response, task, msg_prefix=username)
            for other, other_task in expected.items():
                if other != username and other_task != task:
                    self.assertNotContains(response, other_task, msg_prefix=f"{username} sees {other}'s task")

    def test_task_counts_match_the_records(self):
        response = self.home("sacco")
        tasks = {t["label"]: t["count"] for t in response.context["tasks"]}
        self.assertEqual(tasks["Applications to appraise"], 1)  # Isaac
        self.assertEqual(tasks["Appraised loans to decide"], 0)  # sacco appraised Grace's loan itself
        chair_tasks = {t["label"]: t["count"] for t in self.home("saccochair").context["tasks"]}
        self.assertEqual(chair_tasks["Appraised loans to decide"], 1)  # so the Board chair decides it
        self.assertEqual(tasks["Approved loans to pay out"], 1)  # Ronald
        self.assertEqual(tasks["Loans in arrears"], 2)  # Henry and Joyce

    def test_home_lists_what_is_outside_the_role(self):
        response = self.home("lc1")
        self.assertContains(response, "Not part of your role")
        self.assertIn("audit_log", [p.key for p in response.context["denied"]])

    def test_household_home_shows_only_its_own_record(self):
        response = self.home("household")
        self.assertContains(response, "Grace Nakato")
        self.assertContains(response, "Your loan")
        self.assertNotContains(response, "Isaac Mugisha")
        self.assertEqual(response.context["tasks"], [])

    def test_my_household_page(self):
        self.client.force_login(User.objects.get(username="household"))
        response = self.client.get(reverse("my_household"))
        self.assertContains(response, "Grace Nakato")
        self.assertContains(response, "UGX 800,000")
        self.assertNotContains(response, "Isaac Mugisha")

    def test_household_user_without_a_record_is_told_so(self):
        Household.objects.filter(account__username="household").update(account=None)
        self.client.force_login(User.objects.get(username="household"))
        self.assertContains(self.client.get(reverse("my_household")), "not linked to a household")

    def test_household_cannot_open_other_households_or_loans(self):
        self.client.force_login(User.objects.get(username="household"))
        grace = User.objects.get(username="household").household_record
        self.assertEqual(self.client.get(reverse("registry:household_detail", args=[grace.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("loans:loan_detail", args=[grace.loans.first().pk])).status_code, 403)
