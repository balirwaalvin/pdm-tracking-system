"""Complaint pages: households raise them; officials read, respond and see escalations."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from accounts import access
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from . import services
from .forms import ComplaintForm, ResponseForm
from .models import Complaint


class ComplaintListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = Complaint
    allowed_roles = access.roles_for("complaints")
    unit_field = "household__village"
    paginate_by = 25
    context_object_name = "complaints"

    def get_queryset(self):
        qs = super().get_queryset().select_related("household", "household__village")
        status, level = self.request.GET.get("status", ""), self.request.GET.get("level", "")
        if status in Complaint.Status.values:
            qs = qs.filter(status=status)
        elif status == "unresolved":
            qs = qs.exclude(status=Complaint.Status.RESOLVED)
        if level in Complaint.Level.values:
            qs = qs.filter(level=level)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Complaint.Status.choices
        context["levels"] = Complaint.Level.choices
        return context


class ComplaintDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = Complaint
    allowed_roles = access.roles_for("complaints")
    unit_field = "household__village"
    context_object_name = "complaint"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["responses"] = self.object.responses.select_related("responded_by")
        if services.can_handle(self.request.user, self.object):
            context["response_form"] = ResponseForm()
        return context


@require_POST
@role_required(*access.roles_for("respond_complaint"))
def respond_to_complaint(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("household__village"), pk=pk)
    check_unit_in_scope(request.user, complaint.household.village)
    if not services.can_handle(request.user, complaint):
        messages.error(request, f"This complaint is with the {complaint.get_level_display().lower()} office, not yours.")
        return redirect("feedback:complaint_detail", pk=pk)
    form = ResponseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a status and write a response for the household.")
        return redirect("feedback:complaint_detail", pk=pk)
    services.respond(complaint, request.user, form.cleaned_data["message"], form.cleaned_data["status"])
    messages.success(request, "Response saved and sent to the household by SMS.")
    return redirect("feedback:complaint_detail", pk=pk)


class ComplaintCreateView(RoleRequiredMixin, CreateView):
    """A household raises a complaint about its own PDM experience."""

    form_class = ComplaintForm
    allowed_roles = access.roles_for("raise_complaint")
    template_name = "feedback/complaint_form.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # The role check comes first, so officials get "forbidden", not a redirect.
        if access.allows(user, "raise_complaint") and getattr(user, "household_record", None) is None:
            messages.error(request, "Your login is not linked to a household record yet. Ask your Parish Chief.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        complaint = services.raise_complaint(
            self.request.user.household_record,
            form.cleaned_data["category"],
            form.cleaned_data["description"],
            Complaint.Channel.WEB,
        )
        messages.success(self.request, f"Complaint received. Your reference is {complaint.reference}.")
        return redirect("my_household")
