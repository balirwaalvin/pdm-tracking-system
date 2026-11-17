"""Tests for sign-in security: the sign-in log, lockout, password change and sessions."""

import datetime

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import SignInEvent, User
from .security import LOCKOUT_FAILURES


class SignInTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def sign_in(self, username="sacco", password="pdm12345", **extra):
        return self.client.post(reverse("login"), {"username": username, "password": password}, **extra)

    def test_success_is_recorded_with_the_address(self):
        self.sign_in(HTTP_X_FORWARDED_FOR="41.210.1.2, 10.0.0.1", HTTP_USER_AGENT="TestPhone")
        event = SignInEvent.objects.latest("created_at")
        self.assertTrue(event.succeeded)
        self.assertEqual(event.user.username, "sacco")
        self.assertEqual(event.ip_address, "41.210.1.2")
        self.assertEqual(event.user_agent, "TestPhone")

    def test_failure_is_recorded(self):
        self.sign_in(password="wrong")
        event = SignInEvent.objects.latest("created_at")
        self.assertFalse(event.succeeded)
        self.assertEqual(event.username, "sacco")

    def test_unknown_usernames_are_recorded_too(self):
        self.sign_in(username="nobody", password="x")
        event = SignInEvent.objects.latest("created_at")
        self.assertIsNone(event.user)
        self.assertEqual(event.username, "nobody")

    def test_account_locks_after_repeated_failures(self):
        for _ in range(LOCKOUT_FAILURES):
            self.sign_in(password="wrong")
        response = self.sign_in()  # right password, but locked
        self.assertContains(response, "Too many failed attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_ends_after_the_window(self):
        for _ in range(LOCKOUT_FAILURES):
            self.sign_in(password="wrong")
        SignInEvent.objects.update(created_at=timezone.now() - datetime.timedelta(minutes=16))
        self.sign_in()
        self.assertIn("_auth_user_id", self.client.session)

    def test_a_successful_sign_in_resets_the_count(self):
        for _ in range(LOCKOUT_FAILURES - 1):
            self.sign_in(password="wrong")
        self.sign_in()
        self.client.logout()
        self.sign_in(password="wrong")
        self.sign_in()
        self.assertIn("_auth_user_id", self.client.session)

    def test_lockout_is_per_account(self):
        for _ in range(LOCKOUT_FAILURES):
            self.sign_in(password="wrong")
        self.sign_in(username="pdc")
        self.assertIn("_auth_user_id", self.client.session)

    def test_sign_in_log_is_for_the_auditor_and_filters_failures(self):
        self.sign_in(password="wrong")
        self.sign_in()
        self.client.force_login(User.objects.get(username="auditor"))
        response = self.client.get(reverse("sign_in_log"), {"result": "failed"})
        self.assertTrue(response.context["events"])
        self.assertTrue(all(not e.succeeded for e in response.context["events"]))
        self.client.force_login(User.objects.get(username="national"))
        self.assertEqual(self.client.get(reverse("sign_in_log")).status_code, 403)

    def test_auditor_workspace_counts_failed_sign_ins(self):
        self.sign_in(password="wrong")
        self.sign_in(password="wrong")
        self.client.force_login(User.objects.get(username="auditor"))
        tasks = {t["label"]: t["count"] for t in self.client.get(reverse("home")).context["tasks"]}
        self.assertEqual(tasks["Failed sign-ins in the last 24 hours"], 2)

    def test_workspace_shows_the_previous_sign_in_and_failures(self):
        self.sign_in()
        self.client.logout()
        self.sign_in(password="wrong")
        self.sign_in()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Your previous sign-in")
        self.assertContains(response, "1 failed attempt before this sign-in")


class PasswordAndSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_user_changes_their_password(self):
        self.client.force_login(User.objects.get(username="pdc"))
        response = self.client.post(
            reverse("password_change"),
            {"old_password": "pdm12345", "new_password1": "Kitega-Sty-2026", "new_password2": "Kitega-Sty-2026"},
        )
        self.assertRedirects(response, reverse("password_change_done"))
        self.assertTrue(User.objects.get(username="pdc").check_password("Kitega-Sty-2026"))

    def test_wrong_old_password_is_refused(self):
        self.client.force_login(User.objects.get(username="pdc"))
        self.client.post(
            reverse("password_change"),
            {"old_password": "nope", "new_password1": "Kitega-Sty-2026", "new_password2": "Kitega-Sty-2026"},
        )
        self.assertTrue(User.objects.get(username="pdc").check_password("pdm12345"))

    def test_password_change_needs_sign_in(self):
        response = self.client.get(reverse("password_change"))
        self.assertEqual(response.status_code, 302)

    def test_sessions_end_after_30_idle_minutes(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
