"""Tests for success stories (consent, PDC check, access) and the public parish page."""

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from registry.models import AdminUnit, Household

from .models import SuccessStory

Status = SuccessStory.Status


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class StoryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.isaac = Household.objects.get(nin="CM92004567EFGH")  # verified, Seeta Central

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def draft(self, **overrides):
        data = {
            "household": self.isaac.pk,
            "title": "Broilers every six weeks",
            "story": "Isaac raises broilers and sells them at Seeta market.",
            "consent_given": "on",
            "consent_method": "signed",
        }
        data.update(overrides)
        self.login("parishchief")
        self.client.post(reverse("feedback:story_create"), {k: v for k, v in data.items() if v is not None})
        return SuccessStory.objects.filter(household=self.isaac).last()

    def submit(self, story):
        self.login("parishchief")
        self.client.post(reverse("feedback:story_submit", args=[story.pk]))
        story.refresh_from_db()

    def check(self, story, decision, note="", records_match=True, username="pdc"):
        self.login(username)
        data = {"decision": decision, "note": note}
        if records_match:
            data["records_match"] = "on"
        response = self.client.post(reverse("feedback:story_check", args=[story.pk]), data)
        story.refresh_from_db()
        return response


class StoryWorkflowTests(StoryTestCase):
    def test_parish_chief_drafts_with_consent(self):
        story = self.draft()
        self.assertEqual(story.status, Status.DRAFT)
        self.assertEqual(story.drafted_by.username, "parishchief")
        self.assertEqual(story.consent_recorded_by.username, "parishchief")
        self.assertIsNotNone(story.consent_recorded_at)

    def test_consent_needs_a_method(self):
        self.draft(consent_method="")
        self.assertFalse(SuccessStory.objects.filter(household=self.isaac).exists())

    def test_naming_needs_consent(self):
        self.draft(consent_given=None, consent_method="", show_name="on")
        self.assertFalse(SuccessStory.objects.filter(household=self.isaac).exists())

    def test_story_without_consent_cannot_be_submitted(self):
        story = self.draft(consent_given=None, consent_method="")
        self.submit(story)
        self.assertEqual(story.status, Status.DRAFT)

    def test_full_path_to_publication(self):
        story = self.draft()
        self.submit(story)
        self.assertEqual(story.status, Status.SUBMITTED)
        self.check(story, "approve")
        self.assertEqual(story.status, Status.APPROVED)
        self.assertEqual(story.checked_by.username, "pdc")

    def test_pdc_must_confirm_the_records_check(self):
        story = self.draft()
        self.submit(story)
        self.check(story, "approve", records_match=False)
        self.assertEqual(story.status, Status.SUBMITTED)

    def test_sending_back_needs_a_reason_and_allows_a_fix(self):
        story = self.draft()
        self.submit(story)
        self.check(story, "reject", note="")
        self.assertEqual(story.status, Status.SUBMITTED)
        self.check(story, "reject", note="The loan amount in the story is wrong.")
        self.assertEqual(story.status, Status.REJECTED)
        self.login("parishchief")
        self.assertEqual(self.client.get(reverse("feedback:story_edit", args=[story.pk])).status_code, 200)
        self.submit(story)
        self.assertEqual(story.status, Status.SUBMITTED)

    def test_only_the_pdc_can_check(self):
        story = self.draft()
        self.submit(story)
        for username in ("parishchief", "subcounty", "sacco", "auditor"):
            self.assertEqual(self.check(story, "approve", username=username).status_code, 403, username)
        self.assertEqual(story.status, Status.SUBMITTED)

    def test_published_story_is_locked(self):
        story = SuccessStory.objects.get(status=Status.APPROVED)
        self.login("parishchief")
        self.assertEqual(self.client.get(reverse("feedback:story_edit", args=[story.pk])).status_code, 404)

    def test_unverified_households_are_not_offered(self):
        self.login("parishchief")
        form = self.client.get(reverse("feedback:story_create")).context["form"]
        self.assertNotIn(Household.objects.get(head_name="Florence Atim"), form.fields["household"].queryset)

    def test_pdc_sees_the_household_records_beside_the_story(self):
        story = SuccessStory.objects.get(status=Status.SUBMITTED)  # Ronald
        self.login("pdc")
        response = self.client.get(reverse("feedback:story_detail", args=[story.pk]))
        self.assertContains(response, "The household's records")
        self.assertContains(response, "Record my check")
        self.assertContains(response, "700,000")

    def test_pdc_workspace_lists_stories_to_check(self):
        self.login("pdc")
        tasks = {t["label"]: t["count"] for t in self.client.get(reverse("home")).context["tasks"]}
        self.assertEqual(tasks["Success stories to check"], 1)


class PublicParishTests(StoryTestCase):
    def setUp(self):
        super().setUp()
        self.client.logout()
        self.seeta = AdminUnit.objects.get(name="Seeta")

    def test_no_login_needed(self):
        self.assertEqual(self.client.get(reverse("public_parishes")).status_code, 200)
        self.assertEqual(self.client.get(reverse("public_parish", args=[self.seeta.pk])).status_code, 200)

    def test_only_approved_stories_appear(self):
        response = self.client.get(reverse("public_parish", args=[self.seeta.pk]))
        self.assertContains(response, "From four weaners to a growing piggery")
        self.assertNotContains(response, "A sty built by the group")

    def test_no_personal_data_on_the_page(self):
        response = self.client.get(reverse("public_parish", args=[self.seeta.pk]))
        for household in Household.objects.all():
            self.assertNotContains(response, household.nin)
            if household.phone:
                self.assertNotContains(response, household.phone)

    def test_name_shown_only_with_consent(self):
        story = SuccessStory.objects.get(status=Status.APPROVED)
        story.show_name = False
        story.save()
        response = self.client.get(reverse("public_parish", args=[self.seeta.pk]))
        self.assertNotContains(response, "Moses Waiswa")
        self.assertContains(response, "Moses of Kitega")

    def test_only_parishes_have_public_pages(self):
        goma = AdminUnit.objects.get(name="Goma")
        self.assertEqual(self.client.get(reverse("public_parish", args=[goma.pk])).status_code, 404)

    def test_open_data_csv(self):
        response = self.client.get(reverse("public_parish_data", args=[self.seeta.pk]))
        self.assertEqual(response["Content-Type"], "text/csv")
        rows = dict(line.split(",")[1:3] for line in response.content.decode().splitlines()[1:])
        self.assertEqual(rows["households"], str(Household.objects.filter(village__parent=self.seeta).count()))
        self.assertIn("repayment_rate", rows)
