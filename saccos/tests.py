from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import FundRelease, Sacco


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class SaccoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()
        cls.seeta = Sacco.objects.get(name="Seeta PDM SACCO")
        cls.nantabulirwa = Sacco.objects.get(name="Nantabulirwa PDM SACCO")

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def test_eligibility_follows_the_checklist(self):
        self.assertTrue(self.seeta.is_eligible)
        self.assertFalse(self.nantabulirwa.is_eligible)
        self.assertEqual(self.nantabulirwa.checklist_met, self.nantabulirwa.checklist_total - 1)

    def test_parish_chief_sees_only_own_sacco(self):
        self.login("parishchief")
        response = self.client.get(reverse("saccos:sacco_list"))
        self.assertContains(response, "Seeta PDM SACCO")
        self.assertNotContains(response, "Nantabulirwa PDM SACCO")

    def test_sacco_official_ticks_a_checklist_item(self):
        self.login("sacco")
        item = self.seeta.checklist.first()
        self.client.post(reverse("saccos:toggle_checklist", args=[item.pk]))
        item.refresh_from_db()
        self.assertFalse(item.met)
        self.assertEqual(item.checked_by.username, "sacco")

    def test_sacco_official_cannot_tick_another_parish(self):
        self.login("sacco")
        item = self.nantabulirwa.checklist.first()
        response = self.client.post(reverse("saccos:toggle_checklist", args=[item.pk]))
        self.assertEqual(response.status_code, 403)

    def release_data(self):
        return {"amount": 50_000_000, "financial_year": "2026/27", "release_date": "2026-11-10", "reference": "T-1"}

    def test_national_records_release_for_eligible_sacco(self):
        self.login("national")
        self.client.post(reverse("saccos:release_create", args=[self.seeta.pk]), self.release_data())
        release = FundRelease.objects.get(financial_year="2026/27")
        self.assertEqual(release.recorded_by.username, "national")
        self.assertFalse(release.is_confirmed)

    def test_release_refused_for_ineligible_sacco(self):
        self.login("national")
        response = self.client.post(
            reverse("saccos:release_create", args=[self.nantabulirwa.pk]), self.release_data()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has not met every checklist requirement")
        self.assertFalse(FundRelease.objects.filter(sacco=self.nantabulirwa).exists())

    def test_district_confirms_a_release(self):
        release = FundRelease.objects.create(
            sacco=self.seeta, amount=1_000_000, financial_year="2026/27", release_date="2026-11-10"
        )
        self.login("district")
        self.client.post(reverse("saccos:release_confirm", args=[release.pk]))
        release.refresh_from_db()
        self.assertTrue(release.is_confirmed)
        self.assertEqual(release.confirmed_by.username, "district")

    def test_parish_chief_cannot_confirm_a_release(self):
        release = FundRelease.objects.create(
            sacco=self.seeta, amount=1_000_000, financial_year="2026/27", release_date="2026-11-10"
        )
        self.login("parishchief")
        response = self.client.post(reverse("saccos:release_confirm", args=[release.pk]))
        self.assertEqual(response.status_code, 403)

    def test_total_released_counts_confirmed_releases_only(self):
        FundRelease.objects.create(
            sacco=self.seeta, amount=5_000_000, financial_year="2026/27", release_date="2026-11-10"
        )
        self.assertEqual(self.seeta.total_released, 100_000_000)
