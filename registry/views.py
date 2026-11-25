from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accounts import access
from dashboards.exports import CsvExportMixin
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from .forms import EnterpriseGroupForm, HouseholdForm
from . import eligibility
from .mock_register import MATCHED, check_identity
from .models import EnterpriseGroup, Household

# Who may open what comes from the access policy (accounts/access.py).
HOUSEHOLD_VIEW_ROLES = access.roles_for("households")
GROUP_VIEW_ROLES = access.roles_for("groups")


class HouseholdListView(RoleRequiredMixin, ScopedQuerysetMixin, CsvExportMixin, ListView):
    csv_filename = "households"
    csv_header = ["NIN", "Head of household", "Sex", "Age group", "Disability", "Size", "Wealth rank",
                  "Village", "Parish", "Group", "Verification", "Phone"]

    def csv_row(self, h):
        return [h.nin, h.head_name, h.get_sex_display(), h.get_age_group_display(), "Yes" if h.has_disability else "No",
                h.household_size, h.get_wealth_rank_display(), h.village.name, h.village.parent.name,
                h.enterprise_group.name if h.enterprise_group else "", h.get_verification_display(), h.phone]

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
        context["can_register"] = access.allows(self.request.user, "register_household")
        return context


class HouseholdCreateView(RoleRequiredMixin, CreateView):
    """The Parish Chief registers a household; it then waits for LC I verification."""

    model = Household
    form_class = HouseholdForm
    allowed_roles = access.roles_for("register_household")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        result, note = check_identity(form.cleaned_data["nin"], form.cleaned_data["head_name"])
        messages.success(self.request, "Household registered. It now waits for the LC I Chairperson to verify it.")
        (messages.info if result == MATCHED else messages.warning)(self.request, f"Identity check: {note}")
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
        context["can_edit"] = access.allows(user, "register_household")
        context["can_verify"] = (
            access.allows(user, "verify_household")
            and self.object.verification == Household.Verification.PENDING
        )
        context["identity_result"], context["identity_note"] = check_identity(self.object.nin, self.object.head_name)
        return context


class HouseholdUpdateView(RoleRequiredMixin, ScopedQuerysetMixin, UpdateView):
    """Edit a household. Changing the NIN, village or wealth rank sends it back to LC I."""

    model = Household
    form_class = HouseholdForm
    allowed_roles = access.roles_for("register_household")
    unit_field = "village"
    RECHECK_FIELDS = {"nin", "village", "wealth_rank"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.RECHECK_FIELDS & set(form.changed_data):
            household = form.instance
            household.verification = Household.Verification.PENDING
            household.verified_by = None
            household.verified_at = None
            household.verification_note = ""
            messages.info(self.request, "Key details changed, so the household goes back to LC I for verification.")
        messages.success(self.request, "Household updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("registry:household_detail", args=[self.object.pk])


@require_POST
@role_required(*access.roles_for("verify_household"))
def verify_household(request, pk):
    """The LC I Chairperson confirms or rejects a household in their own village."""
    household = get_object_or_404(Household.objects.select_related("village"), pk=pk)
    check_unit_in_scope(request.user, household.village)

    if household.verification != Household.Verification.PENDING:
        messages.warning(request, "This household has already been checked.")
        return redirect("registry:household_detail", pk=pk)

    decision = request.POST.get("decision")
    note = request.POST.get("note", "").strip()
    if decision == "reject" and not note:
        messages.error(request, "Give a reason when you reject a household.")
        return redirect("registry:household_detail", pk=pk)
    if decision not in ("verify", "reject"):
        messages.error(request, "Choose confirm or reject.")
        return redirect("registry:household_detail", pk=pk)

    household.verification = (
        Household.Verification.VERIFIED if decision == "verify" else Household.Verification.REJECTED
    )
    household.verified_by = request.user
    household.verified_at = timezone.now()
    household.verification_note = note
    household.save()
    messages.success(request, f"{household.head_name} marked as {household.get_verification_display().lower()}.")
    return redirect("registry:household_detail", pk=pk)


class EnterpriseGroupListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = EnterpriseGroup
    allowed_roles = GROUP_VIEW_ROLES
    unit_field = "parish"
    template_name = "registry/group_list.html"
    context_object_name = "groups"

    def get_queryset(self):
        from django.db.models import Count

        return super().get_queryset().select_related("parish").annotate(members_total=Count("members"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_register"] = access.allows(self.request.user, "register_group")
        return context


class EnterpriseGroupCreateView(RoleRequiredMixin, CreateView):
    """The sub-county CDO registers enterprise groups in parishes under them."""

    model = EnterpriseGroup
    form_class = EnterpriseGroupForm
    allowed_roles = access.roles_for("register_group")
    template_name = "registry/group_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Register the group and link it to its parish's PDM SACCO, so members can apply for loans."""
        form.instance.registered_by = self.request.user
        sacco = getattr(form.cleaned_data["parish"], "sacco", None)
        form.instance.sacco = sacco
        if sacco is None:
            messages.warning(self.request, "Enterprise group registered, but its parish has no PDM SACCO yet, so members cannot apply for loans.")
        elif not sacco.is_eligible:
            messages.warning(self.request, f"Enterprise group registered and linked to {sacco.name}, which has not yet met every requirement to receive the fund.")
        else:
            messages.success(self.request, f"Enterprise group registered and linked to {sacco.name}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("registry:group_detail", args=[self.object.pk])


class EnterpriseGroupDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = EnterpriseGroup
    allowed_roles = GROUP_VIEW_ROLES
    unit_field = "parish"
    template_name = "registry/group_detail.html"
    context_object_name = "group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = self.object.members.select_related("village")
        return context


class EligibilityView(TemplateView):
    """Public self-check (no sign-in, nothing stored): could I get a PDM loan, and what next?"""

    template_name = "registry/eligibility.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(rows=[(key, question, "") for key, question, _ in eligibility.QUESTIONS], next_steps=eligibility.NEXT_STEPS)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        answers = {key: request.POST.get(key, "") for key, _, _ in eligibility.QUESTIONS}
        context["rows"] = [(key, question, answers[key]) for key, question, _ in eligibility.QUESTIONS]
        context["submitted"] = True
        context["answered"] = all(answers.values())
        context["likely"], context["gaps"] = eligibility.screen(answers)
        return self.render_to_response(context)
