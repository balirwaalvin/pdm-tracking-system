from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from accounts import roles
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope, scope_queryset

from . import workflow
from .forms import AppraisalForm, LoanApplicationForm
from .models import LoanApplication

Status = LoanApplication.Status

LOAN_VIEW_ROLES = (
    roles.GROUP_EXECUTIVE,
    roles.PARISH_CHIEF,
    roles.PDC,
    roles.SACCO_OFFICIAL,
    roles.SUBCOUNTY_OFFICIAL,
    roles.DISTRICT_OFFICIAL,
    roles.NATIONAL_OFFICIAL,
    roles.AUDITOR,
)


class LoanListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = LoanApplication
    allowed_roles = LOAN_VIEW_ROLES
    unit_field = "household__village"
    paginate_by = 25
    context_object_name = "loans"

    def get_queryset(self):
        qs = super().get_queryset().select_related("household", "household__village", "sacco", "enterprise_group")
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if query:
            qs = qs.filter(Q(household__head_name__icontains=query) | Q(household__nin__icontains=query))
        if status in Status.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Status.choices
        context["can_apply"] = self.request.user.has_role(roles.GROUP_EXECUTIVE)
        return context
