from django.views.generic import TemplateView

from accounts.scoping import scope_queryset
from registry.models import AdminUnit


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
