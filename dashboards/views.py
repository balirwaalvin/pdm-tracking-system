"""The home page, the area dashboard and the auditor's audit log."""

import csv
import datetime

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.views.generic import ListView, TemplateView

from accounts import roles
from accounts.mixins import RoleRequiredMixin
from accounts.scoping import scope_queryset
from registry.models import AdminUnit

from . import queries

# Officials who oversee a parish or more (households and LC I work at village level).
DASHBOARD_ROLES = (
    roles.GROUP_EXECUTIVE,
    roles.PARISH_CHIEF,
    roles.PDC,
    roles.SACCO_OFFICIAL,
    roles.SUBCOUNTY_OFFICIAL,
    roles.DISTRICT_OFFICIAL,
    roles.NATIONAL_OFFICIAL,
    roles.AUDITOR,
)


class HomeView(TemplateView):
    template_name = "dashboards/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            visible = scope_queryset(AdminUnit.objects.select_related("parent"), user, "pk")
            context["area_path"] = (
                [user.admin_unit, *user.admin_unit.ancestors()] if user.admin_unit else []
            )
            context["visible_units"] = visible.order_by("level", "name")
            context["visible_count"] = visible.count()
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

    allowed_roles = (roles.AUDITOR,)
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
