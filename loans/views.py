from auditlog.models import LogEntry
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


class LoanCreateView(RoleRequiredMixin, CreateView):
    """The enterprise group executive starts an application for a member household."""

    model = LoanApplication
    form_class = LoanApplicationForm
    allowed_roles = (roles.GROUP_EXECUTIVE,)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        household = form.cleaned_data["household"]
        form.instance.enterprise_group = household.enterprise_group
        form.instance.sacco = household.enterprise_group.sacco
        form.instance.created_by = self.request.user
        messages.success(self.request, "Application saved as a draft. Check it, then submit it to the SACCO.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("loans:loan_detail", args=[self.object.pk])


class LoanDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = LoanApplication
    allowed_roles = LOAN_VIEW_ROLES
    unit_field = "household__village"
    context_object_name = "loan"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "household", "household__village", "enterprise_group", "sacco", "created_by", "decided_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan, user = self.object, self.request.user
        context["appraisal"] = getattr(loan, "appraisal", None)
        context["can_submit"] = workflow.can_move(loan, Status.SUBMITTED, user)
        context["can_appraise"] = workflow.can_move(loan, Status.APPRAISED, user)
        context["history"] = LogEntry.objects.get_for_object(loan).select_related("actor").order_by("timestamp")
        return context


def _get_scoped_loan(request, pk):
    loan = get_object_or_404(LoanApplication.objects.select_related("household__village"), pk=pk)
    check_unit_in_scope(request.user, loan.household.village)
    return loan


@require_POST
@role_required(roles.GROUP_EXECUTIVE)
def submit_loan(request, pk):
    loan = _get_scoped_loan(request, pk)
    try:
        workflow.move(loan, Status.SUBMITTED, request.user)
    except workflow.TransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Application submitted. The SACCO Loan Committee will appraise it.")
    return redirect("loans:loan_detail", pk=pk)
