from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

# Parish Revolving Fund rules (MoFPED PRF handbook).
LOAN_CEILING = 1_000_000  # Uganda shillings per household
ANNUAL_INTEREST_RATE = Decimal("0.06")
DEFAULT_AFTER_DAYS = 90


class LoanApplication(models.Model):
    """A household's request for a Parish Revolving Fund loan, and its whole life after that."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPRAISED = "appraised", "Appraised"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DISBURSED = "disbursed", "Disbursed"
        REPAYING = "repaying", "Repaying"
        CLOSED = "closed", "Closed (fully repaid)"
        DEFAULTED = "defaulted", "Defaulted"

    household = models.ForeignKey("registry.Household", on_delete=models.PROTECT, related_name="loans")
    enterprise_group = models.ForeignKey(
        "registry.EnterpriseGroup", on_delete=models.PROTECT, related_name="loans"
    )
    sacco = models.ForeignKey("saccos.Sacco", on_delete=models.PROTECT, related_name="loans")
    amount = models.PositiveIntegerField("Amount requested (UGX)")
    enterprise = models.CharField(max_length=150, help_text="What the money will start or grow")
    business_plan = models.TextField(help_text="Short summary: inputs to buy, expected income, repayment plan")
    term_months = models.PositiveSmallIntegerField(default=12)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Loan {self.pk}: {self.household.head_name}, UGX {self.amount:,}"

    # Repayment figures. They exist only once the loan has been paid out.

    def schedule(self):
        """The monthly instalments, or an empty list before disbursement."""
        from .schedule import build_schedule

        disbursement = getattr(self, "disbursement", None)
        if disbursement is None:
            return []
        return build_schedule(disbursement.amount, self.term_months, disbursement.disbursed_on)

    @property
    def total_due(self):
        """Amount paid out plus interest for the whole term."""
        return sum(instalment.amount for instalment in self.schedule())

    @property
    def total_repaid(self):
        return self.repayments.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def balance(self):
        return max(self.total_due - self.total_repaid, 0)

    def amount_due_by(self, day):
        return sum(i.amount for i in self.schedule() if i.due_date <= day)

    def arrears(self, day=None):
        """Instalments fallen due by `day` (default today) and not yet repaid."""
        day = day or timezone.localdate()
        return max(self.amount_due_by(day) - self.total_repaid, 0)

    def days_in_arrears(self, day=None):
        """Days since the oldest instalment that is not fully repaid fell due (0 if none)."""
        day = day or timezone.localdate()
        repaid, paid_up_to = self.total_repaid, 0
        for instalment in self.schedule():
            paid_up_to += instalment.amount
            if paid_up_to > repaid:
                return max((day - instalment.due_date).days, 0)
        return 0

    def schedule_with_status(self, day=None):
        """Each instalment with how much of it the repayments so far cover."""
        day = day or timezone.localdate()
        left, rows = self.total_repaid, []
        for instalment in self.schedule():
            paid = min(left, instalment.amount)
            left -= paid
            if paid == instalment.amount:
                state = "paid"
            elif instalment.due_date < day:
                state = "overdue"
            else:
                state = "due"
            rows.append({"instalment": instalment, "paid": paid, "state": state})
        return rows


class Appraisal(models.Model):
    """The SACCO Loan Committee's assessment of an application, with scores and reasons."""

    class Recommendation(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]

    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, related_name="appraisal")
    viability_score = models.PositiveSmallIntegerField(
        "Business viability (1 to 5)", choices=SCORE_CHOICES
    )
    repayment_score = models.PositiveSmallIntegerField(
        "Capacity to repay (1 to 5)", choices=SCORE_CHOICES
    )
    group_score = models.PositiveSmallIntegerField(
        "Group's recommendation (1 to 5)", choices=SCORE_CHOICES
    )
    recommendation = models.CharField(max_length=10, choices=Recommendation.choices)
    reasons = models.TextField(help_text="Why the committee recommends this. The applicant can see it.")
    appraised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    appraised_at = models.DateTimeField(auto_now_add=True)

    @property
    def score_rows(self):
        """(label, score) pairs for display, out of 5 each."""
        return [
            ("Business viability", self.viability_score),
            ("Capacity to repay", self.repayment_score),
            ("Group’s recommendation", self.group_score),
        ]

    @property
    def total_score(self):
        return self.viability_score + self.repayment_score + self.group_score

    def __str__(self):
        return f"Appraisal of loan {self.application_id}: {self.total_score}/15"


class Disbursement(models.Model):
    """The SACCO paying an approved loan out to the household. One per loan."""

    class Method(models.TextChoices):
        BANK = "bank", "Bank transfer"
        MOBILE = "mobile", "Mobile money"
        CHEQUE = "cheque", "Cheque"

    application = models.OneToOneField(
        LoanApplication, on_delete=models.PROTECT, related_name="disbursement"
    )
    amount = models.PositiveIntegerField("Amount paid out (UGX)")
    disbursed_on = models.DateField("Date paid out")
    method = models.CharField(max_length=10, choices=Method.choices)
    reference = models.CharField(
        max_length=60, help_text="Bank, cheque or mobile money transaction reference"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-disbursed_on"]

    def __str__(self):
        return f"UGX {self.amount:,} paid on loan {self.application_id} on {self.disbursed_on}"


class Repayment(models.Model):
    """Money a household paid back to the SACCO on its loan."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash at the SACCO (receipted)"
        MOBILE = "mobile", "Mobile money"
        BANK = "bank", "Bank deposit"

    application = models.ForeignKey(LoanApplication, on_delete=models.PROTECT, related_name="repayments")
    amount = models.PositiveIntegerField("Amount repaid (UGX)")
    paid_on = models.DateField("Date paid")
    method = models.CharField(max_length=10, choices=Method.choices)
    reference = models.CharField(max_length=60, help_text="Receipt or transaction reference")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["paid_on", "pk"]

    def __str__(self):
        return f"UGX {self.amount:,} repaid on loan {self.application_id} on {self.paid_on}"

    @property
    def receipt_number(self):
        return f"RCPT-{self.pk:06d}"


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(LoanApplication)
auditlog.register(Appraisal)
auditlog.register(Disbursement)
auditlog.register(Repayment)
