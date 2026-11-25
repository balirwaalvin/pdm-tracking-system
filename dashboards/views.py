"""The home page, the area dashboard and the auditor's audit log."""

import csv
import datetime

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from accounts import access
from accounts.mixins import RoleRequiredMixin
from registry.models import AdminUnit

from feedback.appeals import can_appeal
from registry.eligibility import household_checklist

from . import public, queries, reports, workspace

DASHBOARD_ROLES = access.roles_for("dashboard")  # from the access policy


# The ten stages of the PDM customer journey, for the signed-out landing page.
JOURNEY = [
    ("Register", "The Parish Chief profiles the household; the NIN is checked."),
    ("Verify", "The LC I chairperson confirms the household lives in the village."),
    ("Group", "The CDO registers the enterprise group and links it to the SACCO."),
    ("Apply", "The group executive applies for up to UGX 1,000,000."),
    ("Appraise", "A SACCO official scores the plan and the capacity to repay."),
    ("Decide", "A second SACCO official approves or rejects, with reasons."),
    ("Repay", "A schedule at 6% a year; arrears and defaults are flagged."),
    ("Check", "The household dials USSD and gets SMS alerts and receipts."),
    ("Speak up", "Complaints escalate if unresolved; verified stories are shared."),
    ("Oversee", "Dashboards, reports and an audit trail at every level."),
]


class HomeView(TemplateView):
    """A landing page when signed out; when signed in, the user's own workspace.

    The workspace shows only this role's work and access: the to-do list,
    the pages and actions the access policy allows, and what is outside the role.
    """

    template_name = "dashboards/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not user.is_authenticated:
            context["journey"] = JOURNEY
            return context
        pages = access.pages_for(user)
        context.update(
            area_path=[user.admin_unit, *user.admin_unit.ancestors()] if user.admin_unit else [],
            role_summary=access.summary_for(user),
            tasks=workspace.tasks_for(user),
            pages=pages,
            actions=access.actions_for(user),
        )
        # The sign-in before this one, and failed attempts since, so users can spot misuse.
        successes = list(user.sign_ins.filter(succeeded=True).order_by("-created_at")[:2])
        if successes:
            context["previous_sign_in"] = successes[1] if len(successes) > 1 else None
            context["failed_since"] = user.sign_ins.filter(
                succeeded=False, created_at__gt=successes[-1].created_at
            ).count()
        if access.allows(user, "my_household"):
            context["household"] = getattr(user, "household_record", None)
        return context


class MyHouseholdView(RoleRequiredMixin, TemplateView):
    """The household's own record and loans. A household user sees nothing else."""

    template_name = "dashboards/my_household.html"
    allowed_roles = access.roles_for("my_household")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = getattr(self.request.user, "household_record", None)
        context["household"] = household
        if household is not None:
            loans = household.loans.select_related("sacco", "disbursement").prefetch_related("repayments", "sms_messages")
            context["loans"] = [
                {"loan": loan, "schedule": loan.schedule_with_status(), "sms": loan.sms_messages.all(),
                 "can_appeal": can_appeal(loan, self.request.user), "appeal": getattr(loan, "appeal", None)}
                for loan in loans
            ]
            context["complaints"] = household.complaints.prefetch_related("responses")
            context["checklist"] = household_checklist(household)
        return context


class DashboardView(RoleRequiredMixin, TemplateView):
    """Totals and charts for the user's area, split by the units one level down."""

    template_name = "dashboards/dashboard.html"
    allowed_roles = DASHBOARD_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        summary = queries.summary(user)
        rows = queries.breakdown(user)
        context.update(
            summary=summary,
            rows=rows,
            area_name=user.admin_unit.name if user.admin_unit and not user.is_national else "Uganda (all districts)",
            breakdown_level=rows[0]["unit"].get_level_display() if rows else "",
            chart_data={
                "status_labels": [label for label, _ in summary["loans_by_status"]],
                "status_counts": [count for _, count in summary["loans_by_status"]],
                "verification": [
                    summary["households"]["verified"],
                    summary["households"]["pending"],
                    summary["households"]["rejected"],
                ],
                "units": [row["unit"].name for row in rows],
                "disbursed": [row["disbursed"] for row in rows],
                "repaid": [row["repaid"] for row in rows],
                "arrears": [row["arrears"] for row in rows],
            },
        )
        return context


class AuditLogView(RoleRequiredMixin, ListView):
    """Every change to every record: who made it, when and what changed. Read-only.

    Add ?format=csv to download the filtered entries.
    """

    allowed_roles = access.roles_for("audit_log")
    template_name = "dashboards/audit_log.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        entries = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")
        params = self.request.GET
        if params.get("model", "").isdigit():
            entries = entries.filter(content_type_id=params["model"])
        if params.get("action", "").isdigit():
            entries = entries.filter(action=params["action"])
        if params.get("actor"):
            entries = entries.filter(actor__username=params["actor"])
        if params.get("q"):
            entries = entries.filter(object_repr__icontains=params["q"])
        for key, lookup in (("from", "timestamp__date__gte"), ("to", "timestamp__date__lte")):
            try:
                entries = entries.filter(**{lookup: datetime.date.fromisoformat(params.get(key, ""))})
            except ValueError:
                pass
        return entries

    def get(self, request, *args, **kwargs):
        if request.GET.get("format") == "csv":
            return self.csv_response()
        return super().get(request, *args, **kwargs)

    def csv_response(self):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="pdm-audit-log.csv"'
        writer = csv.writer(response)
        writer.writerow(["When", "Who", "Action", "Record type", "Record", "Changes"])
        for entry in self.get_queryset()[:5000]:
            changes = "; ".join(f"{field}: {old} -> {new}" for field, (old, new) in (entry.changes_dict or {}).items())
            writer.writerow([
                entry.timestamp.isoformat(timespec="seconds"),
                entry.actor.username if entry.actor else "system",
                entry.get_action_display(),
                entry.content_type.name,
                entry.object_repr,
                changes,
            ])
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        used = LogEntry.objects.values_list("content_type", flat=True).distinct()
        context["models"] = ContentType.objects.filter(pk__in=used).order_by("app_label", "model")
        context["actions"] = LogEntry.Action.choices
        query = self.request.GET.copy()
        query.pop("page", None)
        context["query_string"] = query.urlencode()
        return context


# Public pages: no login. Only anonymised totals and approved, consented stories.


class PublicParishListView(TemplateView):
    template_name = "dashboards/public_parish_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parishes"] = AdminUnit.objects.filter(level=AdminUnit.Level.PARISH).select_related("parent__parent")
        return context


class PublicParishView(TemplateView):
    template_name = "dashboards/public_parish.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parish = get_object_or_404(AdminUnit, pk=kwargs["pk"], level=AdminUnit.Level.PARISH)
        context.update(parish=parish, figures=public.parish_figures(parish), stories=public.approved_stories(parish))
        return context


def parish_open_data(request, pk):
    """The public parish figures as CSV, for anyone to download and reuse."""
    parish = get_object_or_404(AdminUnit, pk=pk, level=AdminUnit.Level.PARISH)
    figures = public.parish_figures(parish)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="pdm-{parish.name.lower()}-parish.csv"'
    writer = csv.writer(response)
    writer.writerow(["parish", "measure", "value", "as_of"])
    for measure, value in figures.items():
        writer.writerow([parish.name, measure, "" if value is None else value, timezone.localdate().isoformat()])
    return response


class QuarterlyReportView(RoleRequiredMixin, TemplateView):
    """The quarterly report for the user's area. ?q=2026-Q4 picks the quarter; it prints to PDF."""

    template_name = "dashboards/quarterly_report.html"
    allowed_roles = access.roles_for("quarterly_report")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        current = reports.current_quarter()
        quarter = reports.Quarter.parse(self.request.GET.get("q", "")) or current
        context.update(
            quarter=quarter,
            quarters=current.recent(4),
            figures=reports.quarterly_figures(user, quarter),
            rows=queries.breakdown(user),
            area_name=user.admin_unit.name if user.admin_unit and not user.is_national else "Uganda (all districts)",
        )
        return context
