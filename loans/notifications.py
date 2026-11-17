"""SMS alerts to the household when its loan is decided, paid out or repaid.

Each alert is sent after the database change is committed, so a rolled-back
change never sends a text. Messages stay short enough for one SMS.
"""

from django.db import transaction

from ussd.sms import send_sms

from .models import LoanApplication

Status = LoanApplication.Status


def _send_after_commit(loan, message):
    phone = loan.household.phone
    transaction.on_commit(lambda: send_sms(phone, message, loan=loan))


def notify_decision(loan):
    if loan.status == Status.APPROVED:
        message = (
            f"PDM: Your loan of UGX {loan.amount:,} has been approved by {loan.sacco.name}. "
            "The SACCO will tell you when it is paid out."
        )
    elif loan.status == Status.REJECTED:
        message = (
            f"PDM: Your loan application to {loan.sacco.name} was not approved. "
            "Ask your group executive or the SACCO for the reason."
        )
    else:
        return
    _send_after_commit(loan, message)


def notify_disbursement(loan):
    disbursement = loan.disbursement
    first = loan.schedule()[0]
    _send_after_commit(
        loan,
        f"PDM: UGX {disbursement.amount:,} has been paid to you by {disbursement.get_method_display().lower()}, "
        f"ref {disbursement.reference}. First instalment UGX {first.amount:,} due {first.due_date:%d %b %Y}.",
    )


def notify_repayment(repayment):
    loan = repayment.application
    if loan.status == Status.CLOSED:
        tail = "Your loan is fully repaid. Thank you."
    else:
        tail = f"Balance UGX {loan.balance:,}."
    _send_after_commit(
        loan,
        f"PDM: {loan.sacco.name} received UGX {repayment.amount:,} on {repayment.paid_on:%d %b %Y}, "
        f"receipt {repayment.receipt_number}. {tail}",
    )
