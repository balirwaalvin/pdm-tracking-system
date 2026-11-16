"""The loan workflow: which status changes are allowed, and which role may make each one.

Every status change goes through `move()`, which checks the rule, records
who did it and when, and saves. The audit log then keeps the history.
"""

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from accounts import roles

from .models import LoanApplication

Status = LoanApplication.Status
SYSTEM = "system"  # changes made by the system itself, such as the 90-day default flag

# (from, to) -> role allowed to make the change
TRANSITIONS = {
    (Status.DRAFT, Status.SUBMITTED): roles.GROUP_EXECUTIVE,
    (Status.SUBMITTED, Status.APPRAISED): roles.SACCO_OFFICIAL,
    (Status.APPRAISED, Status.APPROVED): roles.SACCO_OFFICIAL,
    (Status.APPRAISED, Status.REJECTED): roles.SACCO_OFFICIAL,
    (Status.APPROVED, Status.DISBURSED): roles.SACCO_OFFICIAL,
    (Status.DISBURSED, Status.REPAYING): SYSTEM,
    (Status.DISBURSED, Status.CLOSED): SYSTEM,
    (Status.REPAYING, Status.CLOSED): SYSTEM,
    (Status.DISBURSED, Status.DEFAULTED): SYSTEM,
    (Status.REPAYING, Status.DEFAULTED): SYSTEM,
}


class TransitionError(Exception):
    """Raised when a status change is not allowed from the current status."""


def allowed_role(current, target):
    return TRANSITIONS.get((current, target))


def can_move(application, target, user=None):
    """True if `user` (or the system, when user is None) may move the loan to `target`."""
    role = allowed_role(application.status, target)
    if role is None:
        return False
    if role == SYSTEM:
        return user is None
    return user is not None and (user.is_superuser or user.has_role(role))


def move(application, target, user=None, reason=""):
    """Change the loan's status, or raise if the rule does not allow it."""
    role = allowed_role(application.status, target)
    if role is None:
        raise TransitionError(
            f"A loan cannot go from {application.get_status_display()} to {Status(target).label}."
        )
    if not can_move(application, target, user):
        raise PermissionDenied(f"Only the {role} can make this change.")

    now = timezone.now()
    application.status = target
    if target == Status.SUBMITTED:
        application.submitted_at = now
    if target in (Status.APPROVED, Status.REJECTED):
        application.decided_by = user
        application.decided_at = now
        application.decision_reason = reason
    application.save()
    return application
