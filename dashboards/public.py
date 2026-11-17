"""Public parish figures: anonymised totals anyone can see without signing in.

No names, NINs or phone numbers. Success stories appear only once approved
by the PDC, and with the household's full name only if they agreed to it.
"""

from django.db.models import Count, Q
from django.utils import timezone

from feedback.models import Complaint, SuccessStory
from loans.models import LoanApplication
from registry.models import EnterpriseGroup, Household

from .queries import PAID_OUT_STATUSES, loan_money


def parish_figures(parish):
    unit_ids = parish.descendant_ids()
    households = Household.objects.filter(village__in=unit_ids)
    counts = households.aggregate(
        total=Count("pk"),
        verified=Count("pk", filter=Q(verification=Household.Verification.VERIFIED)),
        women=Count("pk", filter=Q(sex=Household.Sex.FEMALE)),
        youth=Count("pk", filter=Q(age_group=Household.AgeGroup.YOUTH)),
        disability=Count("pk", filter=Q(has_disability=True)),
    )
    loans = LoanApplication.objects.filter(household__village__in=unit_ids)
    paid_out = loans.filter(status__in=PAID_OUT_STATUSES).select_related("disbursement").prefetch_related("repayments")
    money = loan_money(loans)
    today = timezone.localdate()
    due_so_far = sum(loan.amount_due_by(today) for loan in paid_out)
    repaid_on_due = sum(min(loan.total_repaid, loan.amount_due_by(today)) for loan in paid_out)
    complaints = Complaint.objects.filter(household__village__in=unit_ids)
    resolved = complaints.filter(status=Complaint.Status.RESOLVED).count()
    sacco = getattr(parish, "sacco", None)
    return {
        "households": counts["total"],
        "verified": counts["verified"],
        "women": counts["women"],
        "youth": counts["youth"],
        "disability": counts["disability"],
        "groups": EnterpriseGroup.objects.filter(parish=parish).count(),
        "sacco_name": sacco.name if sacco else "",
        "sacco_eligible": bool(sacco and sacco.is_eligible),
        "loans_paid_out": paid_out.count(),
        "amount_paid_out": money["disbursed"],
        "amount_repaid": money["repaid"],
        "repayment_rate": round(100 * repaid_on_due / due_so_far) if due_so_far else None,
        "complaints": complaints.count(),
        "complaints_resolved": resolved,
    }


def approved_stories(parish):
    return (
        SuccessStory.objects.filter(status=SuccessStory.Status.APPROVED, household__village__in=parish.descendant_ids())
        .select_related("household__village")
        .order_by("-checked_at")
    )
