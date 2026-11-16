from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from registry.models import AdminUnit

from . import roles
from .models import User
from .scoping import scope_queryset, unit_in_scope


class ScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))
        cls.seeta = AdminUnit.objects.get(name="Seeta")
        cls.nantabulirwa = AdminUnit.objects.get(name="Nantabulirwa")

    def visible_names(self, username):
        user = User.objects.get(username=username)
        return set(scope_queryset(AdminUnit.objects.all(), user, "pk").values_list("name", flat=True))

    def test_ten_role_groups_exist(self):
        self.assertEqual(Group.objects.filter(name__in=roles.ALL_ROLES).count(), 10)

    def test_every_demo_user_has_exactly_one_role(self):
        for user in User.objects.exclude(username="admin"):
            self.assertEqual(user.groups.count(), 1, user.username)

    def test_parish_chief_sees_own_parish_and_its_villages_only(self):
        self.assertEqual(self.visible_names("parishchief"), {"Seeta", "Seeta Central", "Kitega", "Bajjo"})

    def test_parish_chief_cannot_see_another_parish(self):
        user = User.objects.get(username="parishchief")
        self.assertFalse(unit_in_scope(user, self.nantabulirwa))

    def test_lc1_sees_only_own_village(self):
        self.assertEqual(self.visible_names("lc1"), {"Seeta Central"})

    def test_subcounty_official_sees_both_parishes(self):
        names = self.visible_names("subcounty")
        self.assertIn("Seeta", names)
        self.assertIn("Nantabulirwa", names)
        self.assertNotIn("Mukono", names)

    def test_national_and_auditor_see_everything(self):
        total = AdminUnit.objects.count()
        for username in ("national", "auditor"):
            self.assertEqual(len(self.visible_names(username)), total)

    def test_seed_demo_can_run_twice_without_duplicates(self):
        units, users = AdminUnit.objects.count(), User.objects.count()
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))
        self.assertEqual(AdminUnit.objects.count(), units)
        self.assertEqual(User.objects.count(), users)


class PageAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))

    def test_home_page_is_public(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_each_role_can_sign_in_and_sees_their_role(self):
        for user in User.objects.exclude(username="admin"):
            self.client.force_login(user)
            response = self.client.get("/")
            self.assertContains(response, user.role)
            self.client.logout()
