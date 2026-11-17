"""Sign-in security: record every attempt, and lock an account after repeated failures.

After LOCKOUT_FAILURES failed attempts for a username within LOCKOUT_MINUTES,
further attempts are refused (even with the right password) until the window
passes. Every attempt is kept as a SignInEvent for the auditor.
"""

import datetime

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from .models import SignInEvent, User

LOCKOUT_FAILURES = 5
LOCKOUT_MINUTES = 15


def client_ip(request):
    """The caller's address; Render puts the real one first in X-Forwarded-For."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR")) or None


def _record(request, username, succeeded, user=None):
    SignInEvent.objects.create(
        user=user,
        username=(username or "")[:150],
        succeeded=succeeded,
        ip_address=client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:255],
    )


@receiver(user_logged_in)
def record_success(sender, request, user, **kwargs):
    _record(request, user.username, True, user)


@receiver(user_login_failed)
def record_failure(sender, credentials, request=None, **kwargs):
    username = credentials.get("username", "")
    _record(request, username, False, User.objects.filter(username=username).first())


def is_locked_out(username):
    since = timezone.now() - datetime.timedelta(minutes=LOCKOUT_MINUTES)
    recent = SignInEvent.objects.filter(username=username, created_at__gte=since)
    last_success = recent.filter(succeeded=True).order_by("-created_at").first()
    if last_success:
        recent = recent.filter(created_at__gt=last_success.created_at)
    return recent.filter(succeeded=False).count() >= LOCKOUT_FAILURES
