"""Figures for the PDM dashboards, always limited to the user's area.

`summary(user)` gives the totals for everything the user may see.
`breakdown(user)` splits the same figures by the units one level below the
user's own unit: districts for national users, then sub-counties, parishes
and villages. Money is in Uganda shillings.
"""

from django.db.models import Count, Q, Sum

from accounts.scoping import scope_queryset
from loans.models import LoanApplication
from loans.workflow import ACTIVE_STATUSES
from registry.models import AdminUnit, EnterpriseGroup, Household
from saccos.models import FundRelease, Sacco

Status = LoanApplication.Status
PAID_OUT_STATUSES = (*ACTIVE_STATUSES, Status.CLOSED)


def _households(user):
    return scope_queryset(Household.objects.all(), user, "village")


def _loans(user):
    return scope_queryset(LoanApplication.objects.all(), user, "household__village")


def loan_money(loans):
    """Paid out, repaid, still owed and overdue, for loans that have been paid out."""
    paid_out = loans.filter(status__in=PAID_OUT_STATUSES).select_related("disbursement")
    figures = {"disbursed": 0, "repaid": 0, "outstanding": 0, "arrears": 0, "at_risk": 0}
    for loan in paid_out.prefetch_related("repayments"):
        figures["disbursed"] += loan.disbursement.amount if hasattr(loan, "disbursement") else 0
        figures["repaid"] += loan.total_repaid
        if loan.status in ACTIVE_STATUSES:
            balance, arrears = loan.balance, loan.arrears()
            figures["outstanding"] += balance
            figures["arrears"] += arrears
            if arrears:
                figures["at_risk"] += balance  # whole balance of a loan with anything overdue
    outstanding = figures["outstanding"]
    figures["portfolio_at_risk"] = round(100 * figures["at_risk"] / outstanding, 1) if outstanding else 0
    return figures


def summary(user):
    households = _households(user)
    loans = _loans(user)
    saccos = scope_queryset(Sacco.objects.prefetch_related("checklist"), user, "parish")
    releases = scope_queryset(FundRelease.objects.exclude(confirmed_at=None), user, "sacco__parish")

    counts = households.aggregate(
        total=Count("pk"),
        verified=Count("pk", filter=Q(verification=Household.Verification.VERIFIED)),
        pending=Count("pk", filter=Q(verification=Household.Verification.PENDING)),
        rejected=Count("pk", filter=Q(verification=Household.Verification.REJECTED)),
        women=Count("pk", filter=Q(sex=Household.Sex.FEMALE)),
        youth=Count("pk", filter=Q(age_group=Household.AgeGroup.YOUTH)),
        disability=Count("pk", filter=Q(has_disability=True)),
    )
    by_status = dict(loans.values_list("status").annotate(n=Count("pk")))
    return {
        "households": counts,
        "groups": scope_queryset(EnterpriseGroup.objects.all(), user, "parish").count(),
        "saccos": saccos.count(),
        "eligible_saccos": sum(1 for sacco in saccos if sacco.is_eligible),
        "released": releases.aggregate(total=Sum("amount"))["total"] or 0,
        "loans_total": loans.count(),
        "loans_by_status": [(label, by_status.get(value, 0)) for value, label in Status.choices],
        "money": loan_money(loans),
    }


def breakdown_units(user):
    """The units one level below the user's unit (districts for national users)."""
    if user.scope_unit_ids() is None:
        return AdminUnit.objects.filter(level=AdminUnit.Level.DISTRICT).order_by("name")
    if user.admin_unit is None:
        return AdminUnit.objects.none()
    return user.admin_unit.children.order_by("name")


def breakdown(user):
    """One row of figures per unit below the user's unit."""
    rows = []
    for unit in breakdown_units(user):
        unit_ids = unit.descendant_ids()
        households = _households(user).filter(village__in=unit_ids)
        loans = _loans(user).filter(household__village__in=unit_ids)
        money = loan_money(loans)
        rows.append(
            {
                "unit": unit,
                "households": households.count(),
                "verified": households.filter(verification=Household.Verification.VERIFIED).count(),
                "loans": loans.count(),
                **money,
            }
        )
    return rows
