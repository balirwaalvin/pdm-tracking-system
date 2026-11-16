from decimal import Decimal

from django.conf import settings
from django.db import models

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
