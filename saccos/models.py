from django.conf import settings
from django.db import models

from registry.models import AdminUnit


class Sacco(models.Model):
    """The PDM SACCO of one parish. It receives the Parish Revolving Fund and lends to households."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=150)
    registration_number = models.CharField(max_length=50, unique=True)
    parish = models.OneToOneField(
        AdminUnit,
        on_delete=models.PROTECT,
        related_name="sacco",
        limit_choices_to={"level": AdminUnit.Level.PARISH},
    )
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "SACCO"
        verbose_name_plural = "SACCOs"

    def __str__(self):
        return self.name

    def ensure_checklist(self):
        """Create any missing standard checklist items."""
        for requirement in DEFAULT_CHECKLIST:
            SaccoChecklistItem.objects.get_or_create(sacco=self, requirement=requirement)

    @property
    def checklist_met(self):
        return self.checklist.filter(met=True).count()

    @property
    def checklist_total(self):
        return self.checklist.count()

    @property
    def is_eligible(self):
        """A SACCO may receive the fund only when it is active and meets every requirement."""
        total = self.checklist_total
        return self.status == self.Status.ACTIVE and total > 0 and self.checklist_met == total

    @property
    def total_released(self):
        """Confirmed fund releases, in Uganda shillings."""
        return self.releases.exclude(confirmed_at=None).aggregate(total=models.Sum("amount"))["total"] or 0


# Requirements a PDM SACCO must meet before it receives the fund.
DEFAULT_CHECKLIST = [
    "Registered with the Ministry of Trade",
    "Bank account opened in the SACCO's name",
    "Board elected at a general meeting",
    "Loan Committee in place",
    "Supervisory Board in place",
    "Bylaws adopted by members",
    "Members registered with their enterprise groups",
]


class SaccoChecklistItem(models.Model):
    sacco = models.ForeignKey(Sacco, on_delete=models.CASCADE, related_name="checklist")
    requirement = models.CharField(max_length=200)
    met = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["sacco", "requirement"], name="unique_requirement_per_sacco"),
        ]

    def __str__(self):
        return self.requirement


class FundRelease(models.Model):
    """A transfer of the Parish Revolving Fund from MoFPED to a SACCO's bank account."""

    sacco = models.ForeignKey(Sacco, on_delete=models.PROTECT, related_name="releases")
    amount = models.PositiveBigIntegerField(help_text="Uganda shillings")
    financial_year = models.CharField(max_length=9, help_text="For example 2025/26")
    release_date = models.DateField()
    reference = models.CharField(max_length=60, blank=True, help_text="Bank or IFMS reference")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-release_date"]

    def __str__(self):
        return f"UGX {self.amount:,} to {self.sacco} on {self.release_date}"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(Sacco)
auditlog.register(SaccoChecklistItem)
auditlog.register(FundRelease)
