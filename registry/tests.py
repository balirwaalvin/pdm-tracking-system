from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import AdminUnit

Level = AdminUnit.Level


class AdminUnitTests(TestCase):
    def setUp(self):
        self.district = AdminUnit.objects.create(name="Mukono", level=Level.DISTRICT)
        self.subcounty = AdminUnit.objects.create(name="Goma", level=Level.SUBCOUNTY, parent=self.district)
        self.parish = AdminUnit.objects.create(name="Seeta", level=Level.PARISH, parent=self.subcounty)
        self.village = AdminUnit.objects.create(name="Kitega", level=Level.VILLAGE, parent=self.parish)

    def test_descendants_of_district_include_every_level(self):
        ids = self.district.descendant_ids()
        self.assertCountEqual(ids, [self.district.pk, self.subcounty.pk, self.parish.pk, self.village.pk])

    def test_descendants_can_exclude_self(self):
        self.assertEqual(self.parish.descendant_ids(include_self=False), [self.village.pk])

    def test_ancestors_run_nearest_first(self):
        self.assertEqual(self.village.ancestors(), [self.parish, self.subcounty, self.district])

    def test_parish_must_sit_inside_a_subcounty(self):
        bad = AdminUnit(name="Wrong", level=Level.PARISH, parent=self.district)
        with self.assertRaises(ValidationError):
            bad.clean()

    def test_district_cannot_have_a_parent(self):
        bad = AdminUnit(name="Wrong", level=Level.DISTRICT, parent=self.district)
        with self.assertRaises(ValidationError):
            bad.clean()


from django.core.management import call_command  # noqa: E402
from django.urls import reverse  # noqa: E402

from accounts.models import User  # noqa: E402

from .models import EnterpriseGroup, Household  # noqa: E402


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class HouseholdPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()
        cls.kitega = AdminUnit.objects.get(name="Kitega")

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def household_data(self, **overrides):
        data = {
            "head_name": "Test Head",
            "nin": "CM99000000TEST",
            "phone": "256700099999",
            "sex": "M",
            "age_group": "youth",
            "household_size": 4,
            "wealth_rank": "poor",
            "village": self.kitega.pk,
            "enterprise_group": "",
        }
        data.update(overrides)
        return data

    def test_parish_chief_sees_only_own_parish_households(self):
        self.login("parishchief")
        response = self.client.get(reverse("registry:household_list"))
        self.assertContains(response, "Grace Nakato")
        self.assertNotContains(response, "Paul Kizza")  # Nantabulirwa parish

    def test_household_role_cannot_open_the_register(self):
        self.login("household")
        self.assertEqual(self.client.get(reverse("registry:household_list")).status_code, 403)

    def test_parish_chief_registers_a_household_as_pending(self):
        self.login("parishchief")
        response = self.client.post(reverse("registry:household_create"), self.household_data())
        household = Household.objects.get(nin="CM99000000TEST")
        self.assertRedirects(response, reverse("registry:household_detail", args=[household.pk]))
        self.assertEqual(household.verification, Household.Verification.PENDING)
        self.assertEqual(household.registered_by.username, "parishchief")

    def test_duplicate_nin_is_refused_even_in_lowercase(self):
        self.login("parishchief")
        response = self.client.post(
            reverse("registry:household_create"), self.household_data(nin="cf85001234abcd")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertEqual(Household.objects.filter(nin="CF85001234ABCD").count(), 1)

    def test_parish_chief_cannot_register_in_another_parish(self):
        self.login("parishchief")
        other_village = AdminUnit.objects.get(name="Nantabulirwa A")
        response = self.client.post(
            reverse("registry:household_create"), self.household_data(village=other_village.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Household.objects.filter(nin="CM99000000TEST").exists())

    def test_group_must_be_in_the_household_parish(self):
        self.login("parishchief")
        coffee = EnterpriseGroup.objects.get(name="Nantabulirwa Coffee Growers")
        response = self.client.post(
            reverse("registry:household_create"), self.household_data(enterprise_group=coffee.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Household.objects.filter(nin="CM99000000TEST").exists())

    def test_editing_the_nin_sends_household_back_to_lc1(self):
        self.login("parishchief")
        grace = Household.objects.get(nin="CF85001234ABCD")
        data = self.household_data(
            head_name=grace.head_name,
            nin="CF85001234ABCE",
            village=grace.village.pk,
            enterprise_group=grace.enterprise_group.pk,
        )
        self.client.post(reverse("registry:household_edit", args=[grace.pk]), data)
        grace.refresh_from_db()
        self.assertEqual(grace.verification, Household.Verification.PENDING)
        self.assertIsNone(grace.verified_by)


class VerificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.force_login(User.objects.get(username="lc1"))

    def test_lc1_confirms_household_in_own_village(self):
        florence = Household.objects.get(head_name="Florence Atim")
        self.client.post(reverse("registry:household_verify", args=[florence.pk]), {"decision": "verify"})
        florence.refresh_from_db()
        self.assertEqual(florence.verification, Household.Verification.VERIFIED)
        self.assertEqual(florence.verified_by.username, "lc1")
        self.assertIsNotNone(florence.verified_at)

    def test_rejection_needs_a_reason(self):
        florence = Household.objects.get(head_name="Florence Atim")
        self.client.post(reverse("registry:household_verify", args=[florence.pk]), {"decision": "reject"})
        florence.refresh_from_db()
        self.assertEqual(florence.verification, Household.Verification.PENDING)

    def test_lc1_cannot_verify_another_village(self):
        john = Household.objects.get(head_name="John Ssemwogerere")  # Kitega village
        response = self.client.post(reverse("registry:household_verify", args=[john.pk]), {"decision": "verify"})
        self.assertEqual(response.status_code, 403)
        john.refresh_from_db()
        self.assertEqual(john.verification, Household.Verification.PENDING)

    def test_parish_chief_cannot_verify(self):
        self.client.force_login(User.objects.get(username="parishchief"))
        florence = Household.objects.get(head_name="Florence Atim")
        response = self.client.post(reverse("registry:household_verify", args=[florence.pk]), {"decision": "verify"})
        self.assertEqual(response.status_code, 403)


class EnterpriseGroupPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_subcounty_official_registers_a_group(self):
        self.client.force_login(User.objects.get(username="subcounty"))
        seeta = AdminUnit.objects.get(name="Seeta")
        self.client.post(
            reverse("registry:group_create"),
            {"name": "Bajjo Goat Keepers", "enterprise": "goats", "parish": seeta.pk, "registration_number": ""},
        )
        self.assertTrue(EnterpriseGroup.objects.filter(name="Bajjo Goat Keepers", parish=seeta).exists())

    def test_parish_chief_cannot_register_groups(self):
        self.client.force_login(User.objects.get(username="parishchief"))
        self.assertEqual(self.client.get(reverse("registry:group_create")).status_code, 403)

    def test_group_detail_lists_members(self):
        self.client.force_login(User.objects.get(username="parishchief"))
        group = EnterpriseGroup.objects.get(name="Seeta Poultry Farmers")
        response = self.client.get(reverse("registry:group_detail", args=[group.pk]))
        self.assertContains(response, "Grace Nakato")
        self.assertContains(response, "Members (4)")
