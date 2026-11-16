from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from accounts import roles
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from .forms import FundReleaseForm
from .models import FundRelease, Sacco, SaccoChecklistItem

SACCO_VIEW_ROLES = (
    roles.GROUP_EXECUTIVE,
    roles.PARISH_CHIEF,
    roles.PDC,
    roles.SACCO_OFFICIAL,
    roles.SUBCOUNTY_OFFICIAL,
    roles.DISTRICT_OFFICIAL,
    roles.NATIONAL_OFFICIAL,
    roles.AUDITOR,
)


class SaccoListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = Sacco
    allowed_roles = SACCO_VIEW_ROLES
    unit_field = "parish"
    context_object_name = "saccos"

    def get_queryset(self):
        return super().get_queryset().select_related("parish", "parish__parent")


class SaccoDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = Sacco
    allowed_roles = SACCO_VIEW_ROLES
    unit_field = "parish"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["checklist"] = self.object.checklist.select_related("checked_by")
        context["releases"] = self.object.releases.select_related("recorded_by", "confirmed_by")
        context["groups"] = self.object.enterprise_groups.all()
        context["can_tick"] = user.has_role(roles.SACCO_OFFICIAL)
        context["can_record_release"] = user.has_role(roles.NATIONAL_OFFICIAL)
        context["can_confirm_release"] = user.has_role(roles.DISTRICT_OFFICIAL)
        return context
