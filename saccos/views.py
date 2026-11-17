from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from accounts import access
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from .forms import FundReleaseForm
from .models import FundRelease, Sacco, SaccoChecklistItem

SACCO_VIEW_ROLES = access.roles_for("saccos")  # from the access policy


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
        context["can_tick"] = access.allows(user, "tick_checklist")
        context["can_record_release"] = access.allows(user, "record_release")
        context["can_confirm_release"] = access.allows(user, "confirm_release")
        return context


@require_POST
@role_required(*access.roles_for("tick_checklist"))
def toggle_checklist_item(request, pk):
    item = get_object_or_404(SaccoChecklistItem.objects.select_related("sacco__parish"), pk=pk)
    check_unit_in_scope(request.user, item.sacco.parish)
    item.met = not item.met
    item.checked_by = request.user
    item.checked_at = timezone.now()
    item.save()
    messages.success(request, f"“{item.requirement}” marked as {'met' if item.met else 'not met'}.")
    return redirect("saccos:sacco_detail", pk=item.sacco_id)


class FundReleaseCreateView(RoleRequiredMixin, CreateView):
    """MoFPED or the PDM Secretariat records a transfer to a SACCO."""

    model = FundRelease
    form_class = FundReleaseForm
    allowed_roles = access.roles_for("record_release")

    def dispatch(self, request, *args, **kwargs):
        self.sacco = get_object_or_404(Sacco, pk=kwargs["sacco_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sacco"] = self.sacco
        return context

    def form_valid(self, form):
        if not self.sacco.is_eligible:
            form.add_error(None, "This SACCO has not met every checklist requirement, so it cannot receive the fund yet.")
            return self.form_invalid(form)
        form.instance.sacco = self.sacco
        form.instance.recorded_by = self.request.user
        messages.success(self.request, "Release recorded. The district now confirms that the SACCO received it.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("saccos:sacco_detail", args=[self.sacco.pk])


@require_POST
@role_required(*access.roles_for("confirm_release"))
def confirm_release(request, pk):
    release = get_object_or_404(FundRelease.objects.select_related("sacco__parish"), pk=pk)
    check_unit_in_scope(request.user, release.sacco.parish)
    if release.is_confirmed:
        messages.warning(request, "This release was already confirmed.")
    else:
        release.confirmed_by = request.user
        release.confirmed_at = timezone.now()
        release.save()
        messages.success(request, "Release confirmed as received by the SACCO.")
    return redirect("saccos:sacco_detail", pk=release.sacco_id)
