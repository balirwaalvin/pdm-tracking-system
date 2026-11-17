"""The USSD menu a household reaches by dialling the PDM short code.

Africa's Talking sends the whole session's input as `text`, with each
answer separated by "*" (for example "" first, then "1", then "1*2").
Replies start with "CON" (wait for another answer) or "END" (close).
The household is found by the phone number it dials from, and answered
in its own language (English or Luganda; "0" on the main menu switches).
All screen texts live in texts.py.
"""

from feedback import services as feedback
from feedback.models import Complaint
from loans.models import LoanApplication
from registry.models import Household

from .sms import normalise_phone
from .texts import CATEGORY_LABELS, t, word

Status = LoanApplication.Status
MAX_LENGTH = 182  # longest screen most phones show


def _fit(reply):
    """Shorten a reply that would not fit on one screen, ending it with an ellipsis."""
    return reply if len(reply) <= MAX_LENGTH else reply[: MAX_LENGTH - 1].rstrip() + "…"


def con(text):
    return _fit(f"CON {text}")


def end(text):
    return _fit(f"END {text}")


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
        return end(t("en", "not_registered"))

    answers = [part for part in (text or "").split("*") if part != ""]
    if answers and answers[0] == "0":  # switch language, then show the menu again
        household.language = "en" if household.language == "lg" else "lg"
        household.save(update_fields=["language"])
        answers = answers[1:]
    lang = household.language
    if not answers:
        return con(t(lang, "menu", name=household.head_name))
    if answers[0] == "1":
        return end(status_text(household, lang))
    if answers[0] == "2":
        return end(loan_text(household, lang))
    if answers[0] == "3":
        return report_problem(household, answers[1:], lang)
    if answers[0] == "4":
        return track_complaint(household, answers[1:], lang)
    return end(t(lang, "invalid"))


def status_text(household, lang="en"):
    lines = [household.head_name, t(lang, "village", village=household.village.name)]
    if household.verification == Household.Verification.VERIFIED:
        lines.append(t(lang, "verified"))
    elif household.verification == Household.Verification.REJECTED:
        lines.append(t(lang, "rejected", note=household.verification_note))
    else:
        lines.append(t(lang, "pending"))
    group = household.enterprise_group
    lines.append(t(lang, "group", group=group.name) if group else t(lang, "no_group"))
    if group and group.sacco:
        lines.append(t(lang, "sacco", sacco=group.sacco.name))
    return "\n".join(lines)


def loan_text(household, lang="en"):
    loan = household.loans.select_related("sacco", "disbursement").order_by("-created_at").first()
    if loan is None:
        return t(lang, "no_loan")

    amount, sacco = f"UGX {loan.amount:,}", loan.sacco.name
    if loan.status == Status.DRAFT:
        return t(lang, "loan_draft", amount=amount)
    if loan.status in (Status.SUBMITTED, Status.APPRAISED):
        return t(lang, "loan_waiting", amount=amount, sacco=sacco)
    if loan.status == Status.APPROVED:
        return t(lang, "loan_approved", amount=amount, sacco=sacco)
    if loan.status == Status.REJECTED:
        return t(lang, "loan_rejected", amount=amount, reason=loan.decision_reason)
    if loan.status == Status.CLOSED:
        return t(lang, "loan_closed", amount=amount)

    lines = [
        t(lang, "loan", amount=amount),
        t(lang, "repaid", value=f"{loan.total_repaid:,}"),
        t(lang, "balance", value=f"{loan.balance:,}"),
    ]
    arrears = loan.arrears()
    if arrears:
        lines.append(t(lang, "overdue", value=f"{arrears:,}", days=loan.days_in_arrears()))
    else:
        upcoming = next((row for row in loan.schedule_with_status() if row["state"] != "paid"), None)
        if upcoming:
            due = upcoming["instalment"]
            lines.append(t(lang, "next", value=f"{due.amount - upcoming['paid']:,}", date=f"{due.due_date:%d %b %Y}"))
    if loan.status == Status.DEFAULTED:
        lines.append(t(lang, "defaulted"))
    return "\n".join(lines)


# Complaint categories in menu order (labels are in texts.CATEGORY_LABELS).
CATEGORIES = [
    Complaint.Category.LOAN_DELAY,
    Complaint.Category.VERIFICATION,
    Complaint.Category.REPAYMENT,
    Complaint.Category.SACCO,
    Complaint.Category.BRIBERY,
    Complaint.Category.OTHER,
]


def report_problem(household, answers, lang="en"):
    """3 -> choose a category -> describe -> reference number."""
    if not answers:
        options = "\n".join(f"{i}. {label}" for i, label in enumerate(CATEGORY_LABELS[lang], start=1))
        return con(t(lang, "categories", options=options))
    choice = answers[0]
    if not choice.isdigit() or not 1 <= int(choice) <= len(CATEGORIES):
        return end(t(lang, "invalid"))
    if len(answers) == 1:
        return con(t(lang, "describe"))
    description = "*".join(answers[1:]).strip()
    if len(description) < 3:
        return end(t(lang, "too_short"))
    complaint = feedback.raise_complaint(household, CATEGORIES[int(choice) - 1], description, Complaint.Channel.USSD)
    return end(t(lang, "received", reference=complaint.reference))


def track_complaint(household, answers, lang="en"):
    """4 -> enter the reference number -> status and the latest reply. Own complaints only."""
    if not answers:
        return con(t(lang, "ask_reference"))
    digits = "".join(ch for ch in answers[0] if ch.isdigit())
    complaint = household.complaints.filter(pk=int(digits)).first() if digits else None
    if complaint is None:
        return end(t(lang, "no_complaint"))
    lines = [
        t(lang, "complaint_status", reference=complaint.reference, status=word(lang, complaint.status)),
        t(lang, "with_office", level=word(lang, complaint.level)),
    ]
    latest = complaint.responses.order_by("-created_at").first()
    if latest:
        lines.append(t(lang, "reply", message=latest.message))
    return end("\n".join(lines))
