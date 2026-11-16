from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts import roles
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from .forms import HouseholdForm
from .models import Household

# Roles that may look at household records.
HOUSEHOLD_VIEW_ROLES = (
    roles.GROUP_EXECUTIVE,
    roles.LC1_CHAIRPERSON,
    roles.PARISH_CHIEF,
    roles.PDC,
    roles.SACCO_OFFICIAL,
    roles.SUBCOUNTY_OFFICIAL,
    roles.DISTRICT_OFFICIAL,
    roles.NATIONAL_OFFICIAL,
    roles.AUDITOR,
)


class HouseholdListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = Household
    allowed_roles = HOUSEHOLD_VIEW_ROLES
    unit_field = "village"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("village", "village__parent", "enterprise_group")
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if query:
            qs = qs.filter(Q(head_name__icontains=query) | Q(nin__icontains=query))
        if status in Household.Verification.values:
            qs = qs.filter(verification=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Household.Verification.choices
        context["can_register"] = self.request.user.has_role(roles.PARISH_CHIEF)
        return context


class HouseholdCreateView(RoleRequiredMixin, CreateView):
    """The Parish Chief registers a household; it then waits for LC I verification."""

    model = Household
    form_class = HouseholdForm
    allowed_roles = (roles.PARISH_CHIEF,)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        messages.success(self.request, "Household registered. It now waits for the LC I Chairperson to verify it.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("registry:household_detail", args=[self.object.pk])


class HouseholdDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = Household
    allowed_roles = HOUSEHOLD_VIEW_ROLES
    unit_field = "village"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "village", "village__parent", "enterprise_group", "verified_by", "registered_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_edit"] = user.has_role(roles.PARISH_CHIEF)
        context["can_verify"] = (
            user.has_role(roles.LC1_CHAIRPERSON)
            and self.object.verification == Household.Verification.PENDING
        )
        return context
