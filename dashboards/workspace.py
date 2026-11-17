"""The to-do list on each user's home page: work waiting for their role, in their area.

Each role gets only the items that are its job. Counts use the same area
scoping as every other page, and each item links to the page that does it.
"""

from django.db.models import Q
from django.urls import reverse

from accounts import roles as r
from accounts.scoping import scope_queryset
from loans.models import LoanApplication
from loans.workflow import ACTIVE_STATUSES
from registry.models import EnterpriseGroup, Household
from saccos.models import FundRelease, Sacco

Status = LoanApplication.Status
Verification = Household.Verification


def _item(label, count, url, hint=""):
    return {"label": label, "count": count, "url": url, "hint": hint, "urgent": count > 0}


def _households(user):
    return scope_queryset(Household.objects.all(), user, "village")


def _loans(user):
    return scope_queryset(LoanApplication.objects.all(), user, "household__village")


def _saccos(user):
    return scope_queryset(Sacco.objects.prefetch_related("checklist"), user, "parish")


def _loan_list(status):
    return f"{reverse('loans:loan_list')}?status={status}"


def _household_list(status):
    return f"{reverse('registry:household_list')}?status={status}"


def _in_arrears(user):
    loans = _loans(user).filter(status__in=ACTIVE_STATUSES).select_related("disbursement").prefetch_related("repayments")
    return sum(1 for loan in loans if loan.arrears())


def _arrears_item(user):
    return _item("Loans in arrears", _in_arrears(user), reverse("loans:arrears_list"), "Follow up with the household and SACCO.")


def tasks_for(user):
    """Work waiting for this user, by role."""
    role = user.role
    if role == r.LC1_CHAIRPERSON:
        return [
            _item("Households waiting for you to verify",
                  _households(user).filter(verification=Verification.PENDING).count(),
                  _household_list(Verification.PENDING), "Confirm or reject each one; give a reason if you reject."),
        ]
    if role == r.PARISH_CHIEF:
        households = _households(user)
        return [
            _item("Households waiting for LC I", households.filter(verification=Verification.PENDING).count(),
                  _household_list(Verification.PENDING), "Remind the LC I chairperson."),
            _item("Rejected households to correct", households.filter(verification=Verification.REJECTED).count(),
                  _household_list(Verification.REJECTED), "Fix the record or follow up the reason."),
            _item("Verified households not in a group",
                  households.filter(verification=Verification.VERIFIED, enterprise_group=None).count(),
                  _household_list(Verification.VERIFIED), "They need a group before they can borrow."),
            _arrears_item(user),
        ]
    if role == r.GROUP_EXECUTIVE:
        loans = _loans(user)
        open_loans = Q(loans__status__in=[s for s in Status.values if s not in (Status.REJECTED, Status.CLOSED)])
        eligible = (
            _households(user)
            .filter(verification=Verification.VERIFIED, enterprise_group__sacco__isnull=False)
            .exclude(open_loans)
            .distinct()
        )
        return [
            _item("Draft applications to submit", loans.filter(status=Status.DRAFT).count(), _loan_list(Status.DRAFT),
                  "Check each draft, then submit it to the SACCO."),
            _item("Verified members who can apply", eligible.count(), reverse("loans:loan_create"),
                  "Start an application for a member."),
            _item("Applications with the SACCO", loans.filter(status__in=[Status.SUBMITTED, Status.APPRAISED]).count(),
                  _loan_list(Status.SUBMITTED), "Waiting for appraisal or a decision."),
        ]
    if role == r.PDC:
        return [
            _item("Loans waiting for the SACCO's decision", _loans(user).filter(status=Status.APPRAISED).count(),
                  _loan_list(Status.APPRAISED)),
            _item("Households waiting for LC I", _households(user).filter(verification=Verification.PENDING).count(),
                  _household_list(Verification.PENDING)),
            _arrears_item(user),
        ]
    if role == r.SACCO_OFFICIAL:
        loans = _loans(user)
        unmet = sum(sacco.checklist_total - sacco.checklist_met for sacco in _saccos(user))
        return [
            _item("Applications to appraise", loans.filter(status=Status.SUBMITTED).count(), _loan_list(Status.SUBMITTED)),
            _item("Appraised loans to decide", loans.filter(status=Status.APPRAISED).count(), _loan_list(Status.APPRAISED),
                  "Approve, or reject with a reason."),
            _item("Approved loans to pay out", loans.filter(status=Status.APPROVED).count(), _loan_list(Status.APPROVED)),
            _arrears_item(user),
            _item("Checklist requirements not met", unmet, reverse("saccos:sacco_list"), "Your SACCO needs all of them to receive funds."),
        ]
    if role == r.SUBCOUNTY_OFFICIAL:
        groups = scope_queryset(EnterpriseGroup.objects.all(), user, "parish")
        return [
            _item("Groups not linked to a SACCO", groups.filter(sacco=None).count(), reverse("registry:group_list")),
            _item("SACCOs not yet eligible", sum(1 for s in _saccos(user) if not s.is_eligible), reverse("saccos:sacco_list")),
            _item("Households waiting for LC I", _households(user).filter(verification=Verification.PENDING).count(),
                  _household_list(Verification.PENDING)),
            _arrears_item(user),
        ]
    if role == r.DISTRICT_OFFICIAL:
        releases = scope_queryset(FundRelease.objects.filter(confirmed_at=None), user, "sacco__parish")
        return [
            _item("Fund releases to confirm", releases.count(), reverse("saccos:sacco_list"),
                  "Confirm once the money reaches the SACCO's account."),
            _item("SACCOs not yet eligible", sum(1 for s in _saccos(user) if not s.is_eligible), reverse("saccos:sacco_list")),
            _arrears_item(user),
        ]
    if role == r.NATIONAL_OFFICIAL:
        saccos = list(_saccos(user).prefetch_related("releases"))
        return [
            _item("Eligible SACCOs with no fund release",
                  sum(1 for s in saccos if s.is_eligible and not s.releases.exists()), reverse("saccos:sacco_list")),
            _item("Releases not yet confirmed by the district",
                  FundRelease.objects.filter(confirmed_at=None).count(), reverse("saccos:sacco_list")),
            _item("Defaulted loans", _loans(user).filter(status=Status.DEFAULTED).count(), _loan_list(Status.DEFAULTED)),
        ]
    if role == r.AUDITOR:
        from auditlog.models import LogEntry
        from django.utils import timezone

        return [
            _item("Changes recorded today", LogEntry.objects.filter(timestamp__date=timezone.localdate()).count(),
                  f"{reverse('audit_log')}?from={timezone.localdate().isoformat()}"),
            _item("Rejected loan applications", _loans(user).filter(status=Status.REJECTED).count(), _loan_list(Status.REJECTED),
                  "Check each refusal has a reason."),
            _item("Defaulted loans", _loans(user).filter(status=Status.DEFAULTED).count(), _loan_list(Status.DEFAULTED)),
        ]
    return []
