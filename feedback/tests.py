"""Tests for complaints: raising (web and USSD), responding by level, escalation and access."""

import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from registry.models import Household
from ussd.models import SmsMessage

from . import services
from .models import Complaint

Level, Status = Complaint.Level, Complaint.Status


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class ComplaintTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.grace = Household.objects.get(nin="CF85001234ABCD")

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def raise_one(self, category=Complaint.Category.LOAN_DELAY, household=None, days_ago=0):
        with self.captureOnCommitCallbacks(execute=True):
            complaint = services.raise_complaint(household or self.grace, category, "My loan is late, please help.")
        if days_ago:
            past = timezone.now() - datetime.timedelta(days=days_ago)
            Complaint.objects.filter(pk=complaint.pk).update(created_at=past, awaiting_since=past)
            complaint.refresh_from_db()
        return complaint


class RaisingTests(ComplaintTestCase):
    def test_household_raises_a_complaint_on_the_web(self):
        self.login("household")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("feedback:complaint_create"), {"category": "loan_delay", "description": "No answer from the SACCO."}
            )
        self.assertRedirects(response, reverse("my_household"))
        complaint = Complaint.objects.filter(household=self.grace).latest("pk")
        self.assertEqual(complaint.level, Level.PARISH)
        self.assertEqual(complaint.channel, Complaint.Channel.WEB)
        sms = SmsMessage.objects.latest("pk")
        self.assertIn(complaint.reference, sms.message)
        self.assertEqual(sms.phone, self.grace.phone)

    def test_too_short_a_description_is_refused(self):
        self.login("household")
        response = self.client.post(reverse("feedback:complaint_create"), {"category": "other", "description": "bad"})
        self.assertContains(response, "describe the problem")

    def test_bribery_complaints_skip_the_parish(self):
        self.assertEqual(self.raise_one(Complaint.Category.BRIBERY).level, Level.SUBCOUNTY)

    def test_reference_is_digits_after_pdm(self):
        complaint = self.raise_one()
        self.assertRegex(complaint.reference, r"^PDM-\d{6}$")

    def test_only_households_can_raise_on_the_web(self):
        self.login("parishchief")
        self.assertEqual(self.client.get(reverse("feedback:complaint_create")).status_code, 403)

    def test_my_household_lists_own_complaints_and_replies(self):
        complaint = self.raise_one()
        services.respond(complaint, User.objects.get(username="parishchief"), "We are checking with the SACCO.", Status.IN_PROGRESS)
        self.login("household")
        response = self.client.get(reverse("my_household"))
        self.assertContains(response, complaint.reference)
        self.assertContains(response, "We are checking with the SACCO.")
        self.assertNotContains(response, "Isaac")  # other households' complaints stay hidden


class RespondingTests(ComplaintTestCase):
    def respond(self, complaint, username, status="in_progress", message="We are looking into it."):
        self.login(username)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("feedback:complaint_respond", args=[complaint.pk]), {"status": status, "message": message}
            )

    def test_parish_chief_responds_at_parish_level(self):
        complaint = self.raise_one()
        self.respond(complaint, "parishchief", "resolved", "Paid out today.")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Status.RESOLVED)
        self.assertIsNone(complaint.awaiting_since)
        self.assertEqual(complaint.responses.get().responded_by.username, "parishchief")
        self.assertIn("resolved", SmsMessage.objects.latest("pk").message)

    def test_being_handled_restarts_the_clock(self):
        complaint = self.raise_one(days_ago=5)
        before = complaint.awaiting_since
        self.respond(complaint, "parishchief")
        complaint.refresh_from_db()
        self.assertGreater(complaint.awaiting_since, before)
        self.assertEqual(complaint.status, Status.IN_PROGRESS)

    def test_other_levels_cannot_respond(self):
        complaint = self.raise_one()  # at the parish
        self.respond(complaint, "subcounty")
        self.assertFalse(complaint.responses.exists())

    def test_parish_chief_cannot_respond_to_bribery_complaints(self):
        complaint = self.raise_one(Complaint.Category.BRIBERY)
        self.respond(complaint, "parishchief")
        self.assertFalse(complaint.responses.exists())
        self.respond(complaint, "subcounty")
        self.assertTrue(complaint.responses.exists())

    def test_read_only_roles_cannot_respond(self):
        complaint = self.raise_one()
        for username in ("pdc", "national", "auditor", "sacco", "household"):
            self.assertEqual(self.respond(complaint, username).status_code, 403, username)

    def test_resolved_complaints_take_no_more_responses(self):
        complaint = self.raise_one()
        self.respond(complaint, "parishchief", "resolved", "Done.")
        self.respond(complaint, "parishchief", "in_progress", "Again.")
        self.assertEqual(complaint.responses.count(), 1)

    def test_response_needs_a_message(self):
        complaint = self.raise_one()
        self.respond(complaint, "parishchief", "resolved", "")
        self.assertFalse(complaint.responses.exists())


class EscalationTests(ComplaintTestCase):
    def test_unresolved_after_seven_days_moves_to_the_subcounty(self):
        complaint = self.raise_one(days_ago=8)
        with self.captureOnCommitCallbacks(execute=True):
            moved = services.escalate_overdue()
        complaint.refresh_from_db()
        self.assertIn(complaint, moved)
        self.assertEqual(complaint.level, Level.SUBCOUNTY)
        self.assertEqual(complaint.escalation_count, 1)
        self.assertIn("sub-county", SmsMessage.objects.latest("pk").message)

    def test_six_days_is_not_yet_overdue(self):
        complaint = self.raise_one(days_ago=6)
        services.escalate_overdue()
        complaint.refresh_from_db()
        self.assertEqual(complaint.level, Level.PARISH)

    def test_escalation_goes_on_to_the_district_and_stops_there(self):
        complaint = self.raise_one(days_ago=8)
        services.escalate_overdue()
        services.escalate_overdue(timezone.now() + datetime.timedelta(days=8))
        complaint.refresh_from_db()
        self.assertEqual(complaint.level, Level.DISTRICT)
        services.escalate_overdue(timezone.now() + datetime.timedelta(days=30))
        complaint.refresh_from_db()
        self.assertEqual(complaint.level, Level.DISTRICT)
        self.assertEqual(complaint.escalation_count, 2)

    def test_resolved_complaints_never_escalate(self):
        complaint = self.raise_one(days_ago=8)
        services.respond(complaint, User.objects.get(username="parishchief"), "Sorted.", Status.RESOLVED)
        services.escalate_overdue(timezone.now() + datetime.timedelta(days=30))
        complaint.refresh_from_db()
        self.assertEqual(complaint.level, Level.PARISH)

    def test_command_reports_what_moved(self):
        complaint = self.raise_one(days_ago=9)
        out = StringIO()
        call_command("escalate_complaints", stdout=out)
        self.assertIn(complaint.reference, out.getvalue())

    def test_seed_has_an_escalated_complaint(self):
        self.assertTrue(Complaint.objects.filter(escalation_count__gt=0, level=Level.SUBCOUNTY).exists())


class AccessTests(ComplaintTestCase):
    def test_complaint_list_is_scoped_to_the_area(self):
        self.login("parishchief")  # Seeta parish
        response = self.client.get(reverse("feedback:complaint_list"))
        self.assertContains(response, "Isaac Mugisha")
        self.assertNotContains(response, "Annet Nakiyimba")  # Nantabulirwa parish
        self.login("subcounty")
        self.assertContains(self.client.get(reverse("feedback:complaint_list")), "Annet Nakiyimba")

    def test_complaint_outside_the_area_is_refused(self):
        annet = Complaint.objects.get(household__head_name="Annet Nakiyimba")
        self.login("parishchief")
        self.assertEqual(self.client.get(reverse("feedback:complaint_detail", args=[annet.pk])).status_code, 404)

    def test_household_cannot_open_the_officials_list(self):
        self.login("household")
        self.assertEqual(self.client.get(reverse("feedback:complaint_list")).status_code, 403)

    def test_workspace_shows_complaints_for_the_office(self):
        self.login("subcounty")
        tasks = {t["label"]: t["count"] for t in self.client.get(reverse("home")).context["tasks"]}
        self.assertEqual(tasks["Complaints for your office"], 2)  # Henry (escalated) and Annet (bribery)


class UssdComplaintTests(ComplaintTestCase):
    def dial(self, text, phone="+256700000001"):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("ussd:callback"), {"phoneNumber": phone, "text": text})
        return response.content.decode()

    def test_main_menu_offers_complaints(self):
        reply = self.dial("")
        self.assertIn("3. Report a problem", reply)
        self.assertIn("4. Track a complaint", reply)

    def test_report_a_problem_end_to_end(self):
        self.assertIn("5. Asked for a bribe", self.dial("3"))
        self.assertIn("Describe the problem", self.dial("3*1"))
        reply = self.dial("3*1*Loan not paid out yet")
        complaint = Complaint.objects.filter(household=self.grace).latest("pk")
        self.assertIn(f"Ref {complaint.reference}", reply)
        self.assertEqual(complaint.channel, Complaint.Channel.USSD)
        self.assertEqual(complaint.category, Complaint.Category.LOAN_DELAY)

    def test_invalid_category(self):
        self.assertIn("Invalid choice", self.dial("3*9"))

    def test_track_own_complaint(self):
        complaint = self.raise_one()
        reply = self.dial(f"4*{complaint.pk}")
        self.assertIn(complaint.reference, reply)
        self.assertIn("parish office", reply)

    def test_cannot_track_another_households_complaint(self):
        isaacs = Complaint.objects.get(household__head_name="Isaac Mugisha")
        self.assertIn("No complaint with that number", self.dial(f"4*{isaacs.pk}"))

    def test_tracking_shows_the_latest_reply(self):
        complaint = self.raise_one()
        services.respond(complaint, User.objects.get(username="parishchief"), "SACCO will call you.", Status.IN_PROGRESS)
        self.assertIn("Reply: SACCO will call you.", self.dial(f"4*{complaint.pk}"))
