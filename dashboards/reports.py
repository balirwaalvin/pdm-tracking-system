"""The quarterly PDM report: what happened in one quarter, in the user's area.

Flows (households registered, loans decided and paid out, repayments,
complaints, stories) count events dated inside the quarter. Positions
(money owed, arrears, defaults) are as of the day the report is opened.
"""

import datetime

from django.db.models import Count, Sum
from django.utils import timezone

from accounts.scoping import scope_queryset
from feedback.models import Complaint, SuccessStory
from loans.models import Disbursement, LoanApplication, Repayment
from registry.models import Household

from . import queries

Status = LoanApplication.Status


class Quarter:
    def __init__(self, year, number):
        if number not in (1, 2, 3, 4):
            raise ValueError("A quarter is 1 to 4.")
        self.year, self.number = year, number
        self.start = datetime.date(year, 3 * number - 2, 1)
        next_start = datetime.date(year + (number == 4), 1 if number == 4 else 3 * number + 1, 1)
        self.end = next_start - datetime.timedelta(days=1)

    def __str__(self):
        return f"{self.year}-Q{self.number}"

    @property
    def label(self):
        return f"Quarter {self.number}, {self.year} ({self.start:%-d %b} to {self.end:%-d %b %Y})"

    @classmethod
    def containing(cls, day):
        return cls(day.year, (day.month - 1) // 3 + 1)

    @classmethod
    def parse(cls, text):
        """'2026-Q4' -> Quarter; anything else -> None."""
        try:
            year, number = text.upper().split("-Q")
            return cls(int(year), int(number))
        except (ValueError, AttributeError):
            return None

    def previous(self):
        return Quarter(self.year - 1, 4) if self.number == 1 else Quarter(self.year, self.number - 1)

    def recent(self, count=4):
        quarters, quarter = [], self
        for _ in range(count):
            quarters.append(quarter)
            quarter = quarter.previous()
        return quarters


def quarterly_figures(user, quarter):
    start, end = quarter.start, quarter.end
    households = scope_queryset(Household.objects.all(), user, "village")
    loans = scope_queryset(LoanApplication.objects.all(), user, "household__village")

    def dated(field):
        """Filter for a date-time field falling inside the quarter."""
        return {f"{field}__date__gte": start, f"{field}__date__lte": end}

    decided = loans.filter(**dated("decided_at"))
    payouts = Disbursement.objects.filter(application__in=loans, disbursed_on__gte=start, disbursed_on__lte=end)
    repayments = Repayment.objects.filter(application__in=loans, paid_on__gte=start, paid_on__lte=end)
    complaints = scope_queryset(Complaint.objects.all(), user, "household__village")
    received = complaints.filter(**dated("created_at"))
    resolved = complaints.filter(**dated("resolved_at"))
    resolve_days = [(c.resolved_at - c.created_at).days for c in resolved]
    money = queries.loan_money(loans)
    return {
        "households_registered": households.filter(**dated("created_at")).count(),
        "households_verified": households.filter(**dated("verified_at"), verification=Household.Verification.VERIFIED).count(),
        "applications_submitted": loans.filter(**dated("submitted_at")).count(),
        "loans_approved": decided.exclude(status=Status.REJECTED).count(),
        "loans_rejected": decided.filter(status=Status.REJECTED).count(),
        "payouts": payouts.aggregate(n=Count("pk"), total=Sum("amount")),
        "repayments": repayments.aggregate(n=Count("pk"), total=Sum("amount")),
        "complaints_received": received.count(),
        "complaints_escalated": received.filter(escalation_count__gt=0).count(),
        "complaints_bribery": received.filter(category=Complaint.Category.BRIBERY).count(),
        "complaints_resolved": resolved.count(),
        "days_to_resolve": round(sum(resolve_days) / len(resolve_days), 1) if resolve_days else None,
        "stories_published": scope_queryset(
            SuccessStory.objects.filter(status=SuccessStory.Status.APPROVED), user, "household__village"
        ).filter(**dated("checked_at")).count(),
        "position": money,
        "defaulted_now": loans.filter(status=Status.DEFAULTED).count(),
        "as_of": timezone.localdate(),
    }


def current_quarter():
    return Quarter.containing(timezone.localdate())
