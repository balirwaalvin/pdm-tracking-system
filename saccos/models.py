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
