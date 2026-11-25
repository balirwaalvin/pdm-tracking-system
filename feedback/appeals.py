"""Appeals against rejected loans: who may appeal, filing, and the sub-county's decision.

A household (or its group executive) may appeal a rejection once, within
APPEAL_WITHIN_DAYS. The sub-county, which is independent of the SACCO, either
dismisses the appeal or refers the loan back to the SACCO for a fresh decision.
Every step texts the household.
"""

import datetime

from django.db import transaction
from django.utils import timezone

from accounts import roles
from accounts.scoping import unit_in_scope
from loans import workflow
from loans.models import LoanApplication
from ussd.sms import send_sms

from .models import APPEAL_WITHIN_DAYS, Appeal

Status = LoanApplication.Status


class AppealError(Exception):
    """A step that is not allowed; the message says why, for the user."""


def deadline(loan):
    return loan.decided_at + datetime.timedelta(days=APPEAL_WITHIN_DAYS) if loan.decided_at else None


def can_appeal(loan, user):
    """True if `user` may appeal this loan's rejection now."""
    if loan.status != Status.REJECTED or hasattr(loan, "appeal") or not user.is_authenticated:
        return False
    if deadline(loan) and timezone.now() > deadline(loan):
        return False
    own_household = getattr(user, "household_record", None) == loan.household
    group_executive = user.has_role(roles.GROUP_EXECUTIVE) and unit_in_scope(user, loan.household.village)
    return own_household or group_executive


def _text(loan, message):
    phone = loan.household.phone
    transaction.on_commit(lambda: send_sms(phone, message[:160], loan=loan))


@transaction.atomic
def file_appeal(loan, user, grounds):
    if not can_appeal(loan, user):
        raise AppealError("This decision cannot be appealed: it is not a rejection, it was already appealed, "
                          f"or the {APPEAL_WITHIN_DAYS}-day window has passed.")
    if len(grounds.strip()) < 10:
        raise AppealError("Explain in a sentence or two why the decision should be looked at again.")
    appeal = Appeal.objects.create(loan=loan, grounds=grounds.strip(), filed_by=user)
    _text(loan, f"PDM: Appeal {appeal.reference} received for your loan of UGX {loan.amount:,}. "
                "The sub-county office will decide it.")
    return appeal


@transaction.atomic
def decide_appeal(appeal, user, uphold, note):
    if appeal.status != Appeal.Status.PENDING:
        raise AppealError("This appeal has already been decided.")
    if not note.strip():
        raise AppealError("Give the reason for your decision; the household will see it.")
    appeal.status = Appeal.Status.REFERRED if uphold else Appeal.Status.DISMISSED
    appeal.decided_by, appeal.decided_at, appeal.decision_note = user, timezone.now(), note.strip()
    appeal.save()
    loan = appeal.loan
    if uphold:
        workflow.move(loan, Status.APPRAISED)  # back to the SACCO; maker-checker still applies
        _text(loan, f"PDM: Your appeal {appeal.reference} was upheld. {loan.sacco.name} will decide your loan again.")
    else:
        _text(loan, f"PDM: Your appeal {appeal.reference} was dismissed. Reason: {appeal.decision_note}")
    return appeal
