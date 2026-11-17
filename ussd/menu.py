"""The USSD menu a household reaches by dialling the PDM short code.

Africa's Talking sends the whole session's input as `text`, with each
answer separated by "*" (for example "" first, then "1", then "1*2").
Replies start with "CON" (wait for another answer) or "END" (close).
The household is found by the phone number it dials from.
"""

from loans.models import LoanApplication
from registry.models import Household

from .sms import normalise_phone

Status = LoanApplication.Status
MAX_LENGTH = 182  # longest screen most phones show


def con(text):
    return f"CON {text}"[:MAX_LENGTH]


def end(text):
    return f"END {text}"[:MAX_LENGTH]


def find_household(phone):
    number = normalise_phone(phone)
    if not number:
        return None
    return (
        Household.objects.filter(phone=number)
        .select_related("village__parent", "enterprise_group__sacco")
        .order_by("-created_at")
        .first()
    )


def respond(phone, text):
    """The reply for one step of a USSD session."""
    household = find_household(phone)
    if household is None:
        return end("This number is not registered under PDM. Visit your Parish Chief to be profiled.")

    answers = [part for part in (text or "").split("*") if part != ""]
    if not answers:
        return con(f"PDM (prototype)\n{household.head_name}\n1. My PDM status\n2. My loan")
    if answers[0] == "1":
        return end(status_text(household))
    if answers[0] == "2":
        return end(loan_text(household))
    return end("Invalid choice. Please dial again.")


def status_text(household):
    lines = [household.head_name, f"Village: {household.village.name}"]
    if household.verification == Household.Verification.VERIFIED:
        lines.append("Verified by LC I")
    elif household.verification == Household.Verification.REJECTED:
        lines.append(f"Not verified: {household.verification_note}")
    else:
        lines.append("Waiting for LC I to verify")
    group = household.enterprise_group
    lines.append(f"Group: {group.name}" if group else "Not yet in an enterprise group")
    if group and group.sacco:
        lines.append(f"SACCO: {group.sacco.name}")
    return "\n".join(lines)


def loan_text(household):
    loan = household.loans.select_related("sacco", "disbursement").order_by("-created_at").first()
    if loan is None:
        return "You have no PDM loan application. Ask your enterprise group executive."

    amount = f"UGX {loan.amount:,}"
    if loan.status == Status.DRAFT:
        return f"Loan of {amount} is a draft with your group executive."
    if loan.status in (Status.SUBMITTED, Status.APPRAISED):
        return f"Loan of {amount} is with {loan.sacco.name} for a decision."
    if loan.status == Status.APPROVED:
        return f"Loan of {amount} is approved. {loan.sacco.name} will pay it out soon."
    if loan.status == Status.REJECTED:
        return f"Loan of {amount} was not approved. Reason: {loan.decision_reason}"
    if loan.status == Status.CLOSED:
        return f"Loan of {amount} is fully repaid. Thank you."

    lines = [f"Loan {amount}", f"Repaid UGX {loan.total_repaid:,}", f"Balance UGX {loan.balance:,}"]
    arrears = loan.arrears()
    if arrears:
        lines.append(f"Overdue UGX {arrears:,} ({loan.days_in_arrears()} days)")
    else:
        upcoming = next((row for row in loan.schedule_with_status() if row["state"] != "paid"), None)
        if upcoming:
            due = upcoming["instalment"]
            lines.append(f"Next UGX {due.amount - upcoming['paid']:,} by {due.due_date:%d %b %Y}")
    if loan.status == Status.DEFAULTED:
        lines.append("In default: visit your SACCO.")
    return "\n".join(lines)
