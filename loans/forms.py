from django import forms
from django.utils import timezone

from accounts.scoping import scope_queryset
from registry.models import Household

from .models import LOAN_CEILING, Appraisal, Disbursement, LoanApplication

OPEN_STATUSES = [
    LoanApplication.Status.DRAFT,
    LoanApplication.Status.SUBMITTED,
    LoanApplication.Status.APPRAISED,
    LoanApplication.Status.APPROVED,
    LoanApplication.Status.DISBURSED,
    LoanApplication.Status.REPAYING,
    LoanApplication.Status.DEFAULTED,
]


class LoanApplicationForm(forms.ModelForm):
    """Only verified households in a group linked to a SACCO can apply, one open loan at a time."""

    class Meta:
        model = LoanApplication
        fields = ["household", "amount", "enterprise", "business_plan", "term_months"]
        widgets = {"business_plan": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        households = Household.objects.filter(
            verification=Household.Verification.VERIFIED,
            enterprise_group__sacco__isnull=False,
        ).select_related("enterprise_group__sacco", "village")
        if user is not None:
            households = scope_queryset(households, user, "village")
        self.fields["household"].queryset = households
        self.fields["household"].help_text = (
            "Only verified households in an enterprise group linked to a SACCO are listed."
        )
        self.fields["amount"].help_text = f"Up to UGX {LOAN_CEILING:,}."
        self.fields["term_months"].help_text = "Months to repay, between 3 and 24."

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < 10_000:
            raise forms.ValidationError("The smallest loan is UGX 10,000.")
        if amount > LOAN_CEILING:
            raise forms.ValidationError(f"A PDM loan cannot be more than UGX {LOAN_CEILING:,}.")
        return amount

    def clean_term_months(self):
        term = self.cleaned_data["term_months"]
        if not 3 <= term <= 24:
            raise forms.ValidationError("Choose between 3 and 24 months.")
        return term

    def clean_household(self):
        household = self.cleaned_data["household"]
        open_loans = household.loans.filter(status__in=OPEN_STATUSES).exclude(pk=self.instance.pk)
        if open_loans.exists():
            raise forms.ValidationError("This household already has an open loan.")
        return household


class AppraisalForm(forms.ModelForm):
    class Meta:
        model = Appraisal
        fields = ["viability_score", "repayment_score", "group_score", "recommendation", "reasons"]
        widgets = {
            "viability_score": forms.RadioSelect,
            "repayment_score": forms.RadioSelect,
            "group_score": forms.RadioSelect,
            "reasons": forms.Textarea(attrs={"rows": 4}),
        }


class DecisionForm(forms.Form):
    """The SACCO's decision on an appraised application. Refusals must say why."""

    APPROVE = "approve"
    REJECT = "reject"

    decision = forms.ChoiceField(
        choices=[(APPROVE, "Approve"), (REJECT, "Reject")], widget=forms.RadioSelect
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Required when rejecting. The applicant can see it.",
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == self.REJECT and not cleaned.get("reason", "").strip():
            self.add_error("reason", "Give the reason for rejecting this application.")
        return cleaned


class DisbursementForm(forms.ModelForm):
    """The SACCO records paying out an approved loan.

    The amount cannot be more than was approved, nor more than the SACCO
    still holds from its confirmed fund releases.
    """

    class Meta:
        model = Disbursement
        fields = ["amount", "disbursed_on", "method", "reference"]
        widgets = {"disbursed_on": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, loan, **kwargs):
        super().__init__(*args, **kwargs)
        self.loan = loan
        if not self.is_bound:
            self.initial.setdefault("amount", loan.amount)
            self.initial.setdefault("disbursed_on", timezone.localdate())
        self.fields["amount"].help_text = (
            f"Approved: UGX {loan.amount:,}. The SACCO holds UGX {loan.sacco.funds_available:,} "
            "from confirmed fund releases."
        )

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Enter the amount paid out.")
        if amount > self.loan.amount:
            raise forms.ValidationError(
                f"You cannot pay out more than the approved UGX {self.loan.amount:,}."
            )
        available = self.loan.sacco.funds_available
        if amount > available:
            raise forms.ValidationError(
                f"The SACCO only holds UGX {available:,} from confirmed fund releases."
            )
        return amount

    def clean_disbursed_on(self):
        day = self.cleaned_data["disbursed_on"]
        if day > timezone.localdate():
            raise forms.ValidationError("The payment date cannot be in the future.")
        decided = self.loan.decided_at
        if decided and day < timezone.localtime(decided).date():
            raise forms.ValidationError("The payment date cannot be before the loan was approved.")
        return day
