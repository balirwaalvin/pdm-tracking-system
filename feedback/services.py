"""Raising, answering and escalating complaints. Every step texts the household.

Views, the USSD menu and the daily job all go through these functions, so
the rules live in one place.
"""

from django.db import transaction
from django.utils import timezone

from accounts import roles
from ussd.sms import send_sms

from .models import Complaint, ComplaintResponse

Level = Complaint.Level

# Which role handles a complaint at each level.
HANDLER_ROLE = {
    Level.PARISH: roles.PARISH_CHIEF,
    Level.SUBCOUNTY: roles.SUBCOUNTY_OFFICIAL,
    Level.DISTRICT: roles.DISTRICT_OFFICIAL,
}
NEXT_LEVEL = {Level.PARISH: Level.SUBCOUNTY, Level.SUBCOUNTY: Level.DISTRICT}


def _text(complaint, message):
    phone = complaint.household.phone
    transaction.on_commit(lambda: send_sms(phone, message))


def can_handle(user, complaint):
    """True if this user's role handles complaints at the complaint's current level."""
    if complaint.status == Complaint.Status.RESOLVED:
        return False
    return user.is_superuser or user.has_role(HANDLER_ROLE[complaint.level])


@transaction.atomic
def raise_complaint(household, category, description, channel=Complaint.Channel.WEB):
    complaint = Complaint.objects.create(
        household=household, category=category, description=description.strip(), channel=channel
    )
    _text(
        complaint,
        f"PDM: Complaint received. Ref {complaint.reference}. The {complaint.get_level_display().lower()} "
        "office will respond within 7 days. Dial the PDM code to track it.",
    )
    return complaint


@transaction.atomic
def respond(complaint, user, message, status):
    """Record an official's response.

    Resolving stops the escalation clock. "Being handled" restarts it, so the
    complaint still moves up if it is not resolved within another 7 days.
    """
    response = ComplaintResponse.objects.create(
        complaint=complaint, message=message.strip(), status_after=status, responded_by=user
    )
    complaint.status = status
    if status == Complaint.Status.RESOLVED:
        complaint.resolved_at = timezone.now()
        complaint.awaiting_since = None
    else:
        complaint.awaiting_since = timezone.now()
    complaint.save()
    outcome = "resolved" if status == Complaint.Status.RESOLVED else "being handled"
    _text(complaint, f"PDM: Your complaint {complaint.reference} is {outcome}. {message.strip()}"[:160])
    return response


def escalate_overdue(now=None):
    """Move up one level every complaint not resolved within 7 days at its level. Returns those moved."""
    now = now or timezone.now()
    moved = []
    waiting = Complaint.objects.exclude(status=Complaint.Status.RESOLVED).exclude(awaiting_since=None)
    for complaint in waiting.select_related("household"):
        if complaint.response_due > now or complaint.level not in NEXT_LEVEL:
            continue
        with transaction.atomic():
            complaint.level = NEXT_LEVEL[complaint.level]
            complaint.awaiting_since = now
            complaint.escalation_count += 1
            complaint.save()
            _text(
                complaint,
                f"PDM: Your complaint {complaint.reference} had no response, so it has gone to the "
                f"{complaint.get_level_display().lower()} office.",
            )
        moved.append(complaint)
    return moved

