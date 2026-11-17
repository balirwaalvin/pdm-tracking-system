from auditlog.models import LogEntry
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView

from accounts import access
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from . import notifications, workflow
from .forms import AppraisalForm, DecisionForm, DisbursementForm, LoanApplicationForm, RepaymentForm
from .models import LoanApplication

Status = LoanApplication.Status

LOAN_VIEW_ROLES = access.roles_for("loans")  # from the access policy
SACCO_LOAN_ROLES = access.roles_for("appraise_loan")


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
        context["can_apply"] = access.allows(self.request.user, "apply_loan")
        return context


class LoanCreateView(RoleRequiredMixin, CreateView):
    """The enterprise group executive starts an application for a member household."""

    model = LoanApplication
    form_class = LoanApplicationForm
    allowed_roles = access.roles_for("apply_loan")

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
        context["can_decide"] = workflow.can_move(loan, Status.APPROVED, user)
        context["disbursement"] = getattr(loan, "disbursement", None)
        context["can_disburse"] = workflow.can_move(loan, Status.DISBURSED, user)
        context["schedule"] = loan.schedule_with_status()
        context["repayments"] = loan.repayments.select_related("recorded_by")
        context["can_repay"] = loan.status in workflow.ACTIVE_STATUSES and (
            access.allows(user, "appraise_loan")
        )
        if context["can_decide"]:
            context["decision_form"] = DecisionForm()
        context["sms_messages"] = loan.sms_messages.all()
        context["history"] = LogEntry.objects.get_for_object(loan).select_related("actor").order_by("timestamp")
        return context


def _get_scoped_loan(request, pk):
    loan = get_object_or_404(LoanApplication.objects.select_related("household__village"), pk=pk)
    check_unit_in_scope(request.user, loan.household.village)
    return loan


@require_POST
@role_required(*access.roles_for("apply_loan"))
def submit_loan(request, pk):
    loan = _get_scoped_loan(request, pk)
    try:
        workflow.move(loan, Status.SUBMITTED, request.user)
    except workflow.TransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Application submitted. The SACCO Loan Committee will appraise it.")
    return redirect("loans:loan_detail", pk=pk)


class AppraisalCreateView(RoleRequiredMixin, CreateView):
    """The SACCO Loan Committee scores a submitted application and gives reasons."""

    form_class = AppraisalForm
    allowed_roles = SACCO_LOAN_ROLES
    template_name = "loans/appraisal_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.loan = _get_scoped_loan(request, kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.loan.status != Status.SUBMITTED:
            messages.warning(request, "Only submitted applications can be appraised.")
            return redirect("loans:loan_detail", pk=self.loan.pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["loan"] = self.loan
        return context

    def form_valid(self, form):
        try:
            workflow.move(self.loan, Status.APPRAISED, self.request.user)
        except workflow.TransitionError as error:
            messages.error(self.request, str(error))
            return redirect("loans:loan_detail", pk=self.loan.pk)
        form.instance.application = self.loan
        form.instance.appraised_by = self.request.user
        form.save()
        messages.success(self.request, "Appraisal saved. The SACCO Board can now decide.")
        return redirect("loans:loan_detail", pk=self.loan.pk)


@require_POST
@role_required(*SACCO_LOAN_ROLES)
def decide_loan(request, pk):
    """The SACCO approves or rejects an appraised application. A rejection must give a reason."""
    loan = _get_scoped_loan(request, pk)
    form = DecisionForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("loans:loan_detail", pk=pk)

    approve = form.cleaned_data["decision"] == DecisionForm.APPROVE
    target = Status.APPROVED if approve else Status.REJECTED
    try:
        workflow.move(loan, target, request.user, reason=form.cleaned_data["reason"].strip())
    except workflow.TransitionError as error:
        messages.error(request, str(error))
    else:
        notifications.notify_decision(loan)
        if approve:
            messages.success(request, "Loan approved. Record the disbursement when the money is paid out.")
        else:
            messages.success(request, "Loan rejected. The reason is kept on the record.")
    return redirect("loans:loan_detail", pk=pk)


class DisbursementCreateView(RoleRequiredMixin, CreateView):
    """The SACCO records paying out an approved loan, which moves it to Disbursed."""

    form_class = DisbursementForm
    allowed_roles = SACCO_LOAN_ROLES
    template_name = "loans/disbursement_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.loan = _get_scoped_loan(request, kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def refuse_unless_approved(self):
        if self.loan.status != Status.APPROVED:
            messages.warning(self.request, "Only approved loans can be paid out.")
            return redirect("loans:loan_detail", pk=self.loan.pk)
        return None

    def get(self, request, *args, **kwargs):
        return self.refuse_unless_approved() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.refuse_unless_approved() or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["loan"] = self.loan
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["loan"] = self.loan
        return context

    def form_valid(self, form):
        with transaction.atomic():
            try:
                workflow.move(self.loan, Status.DISBURSED, self.request.user)
            except workflow.TransitionError as error:
                messages.error(self.request, str(error))
                return redirect("loans:loan_detail", pk=self.loan.pk)
            form.instance.application = self.loan
            form.instance.recorded_by = self.request.user
            form.save()
            notifications.notify_disbursement(self.loan)
        messages.success(self.request, "Disbursement recorded. The loan has been paid out to the household.")
        return redirect("loans:loan_detail", pk=self.loan.pk)


class RepaymentCreateView(RoleRequiredMixin, CreateView):
    """The SACCO records a repayment. The system then moves the loan to Repaying or Closed."""

    form_class = RepaymentForm
    allowed_roles = SACCO_LOAN_ROLES
    template_name = "loans/repayment_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.loan = _get_scoped_loan(request, kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def refuse_unless_active(self):
        if self.loan.status not in workflow.ACTIVE_STATUSES:
            messages.warning(self.request, "Repayments can only be recorded on a loan that has been paid out and is not closed.")
            return redirect("loans:loan_detail", pk=self.loan.pk)
        return None

    def get(self, request, *args, **kwargs):
        return self.refuse_unless_active() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.refuse_unless_active() or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["loan"] = self.loan
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["loan"] = self.loan
        return context

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.application = self.loan
            form.instance.recorded_by = self.request.user
            form.save()
            workflow.after_repayment(self.loan)
            notifications.notify_repayment(form.instance)
        if self.loan.status == Status.CLOSED:
            messages.success(self.request, "Repayment recorded. The loan is now fully repaid and closed.")
        else:
            messages.success(self.request, f"Repayment recorded. UGX {self.loan.balance:,} is still owed.")
        return redirect("loans:loan_detail", pk=self.loan.pk)


class ArrearsListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    """Paid-out loans with instalments overdue, oldest arrears first."""

    model = LoanApplication
    allowed_roles = access.roles_for("arrears")
    unit_field = "household__village"
    template_name = "loans/arrears_list.html"
    context_object_name = "rows"

    def get_queryset(self):
        loans = (
            super()
            .get_queryset()
            .filter(status__in=workflow.ACTIVE_STATUSES)
            .select_related("household", "household__village", "sacco", "disbursement")
        )
        rows = []
        for loan in loans:
            arrears = loan.arrears()
            if arrears:
                rows.append({"loan": loan, "arrears": arrears, "days": loan.days_in_arrears(), "balance": loan.balance})
        return sorted(rows, key=lambda row: row["days"], reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_arrears"] = sum(row["arrears"] for row in context["rows"])
        context["default_after_days"] = workflow.DEFAULT_AFTER_DAYS
        return context
