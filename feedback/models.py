"""Complaints from households, and the officials' responses.

A complaint starts at the level that should handle it (usually the parish)
and moves up one level if it is not resolved within ESCALATE_AFTER_DAYS
(a "being handled" reply restarts the clock):
parish, then sub-county, then district. Complaints about bribery start at
the sub-county, so the parish officials involved never handle them.
"""

import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

ESCALATE_AFTER_DAYS = 7


class Complaint(models.Model):
    class Category(models.TextChoices):
        LOAN_DELAY = "loan_delay", "Loan delayed or not paid out"
        VERIFICATION = "verification", "Left out or wrongly rejected"
        REPAYMENT = "repayment", "Repayment not recorded correctly"
        SACCO = "sacco", "SACCO or official conduct"
        BRIBERY = "bribery", "Asked for a bribe or a fee"
        OTHER = "other", "Something else"

    class Channel(models.TextChoices):
        USSD = "ussd", "USSD"
        WEB = "web", "Web"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "Being handled"
        RESOLVED = "resolved", "Resolved"

    class Level(models.TextChoices):
        PARISH = "parish", "Parish"
        SUBCOUNTY = "subcounty", "Sub-county"
        DISTRICT = "district", "District"

    household = models.ForeignKey("registry.Household", on_delete=models.PROTECT, related_name="complaints")
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.WEB)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.PARISH)
    awaiting_since = models.DateTimeField(
        null=True, blank=True, help_text="Start of the current 7-day clock; empty once resolved."
    )
    escalation_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference}: {self.get_category_display()}"

    @property
    def reference(self):
        """Digits only, so it is easy to type on a phone keypad."""
        return f"PDM-{self.pk:06d}" if self.pk else "PDM-new"

    @staticmethod
    def starting_level(category):
        return Complaint.Level.SUBCOUNTY if category == Complaint.Category.BRIBERY else Complaint.Level.PARISH

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.level = self.starting_level(self.category)
            if self.awaiting_since is None:
                self.awaiting_since = self.created_at
        super().save(*args, **kwargs)

    @property
    def response_due(self):
        if self.awaiting_since is None or self.status == self.Status.RESOLVED:
            return None
        return self.awaiting_since + datetime.timedelta(days=ESCALATE_AFTER_DAYS)

    @property
    def is_overdue(self):
        due = self.response_due
        return due is not None and timezone.now() >= due


class ComplaintResponse(models.Model):
    """What an official did about a complaint. The household sees every response."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="responses")
    message = models.TextField()
    status_after = models.CharField(max_length=12, choices=Complaint.Status.choices)
    responded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Response to {self.complaint.reference}"


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(Complaint)
auditlog.register(ComplaintResponse)
