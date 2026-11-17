"""The home page, the area dashboard and the auditor's audit log."""

from django.views.generic import TemplateView

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
