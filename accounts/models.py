from django.contrib.auth.models import AbstractUser
from django.db import models

from . import roles


class User(AbstractUser):
    """A PDM stakeholder who can log in.

    `admin_unit` is the area the user acts for: a village for an LC I
    Chairperson, a parish for a Parish Chief, a district for a district
    official. National roles have no unit and see the whole country.
    """

    phone = models.CharField(max_length=15, blank=True, help_text="Format: 2567XXXXXXXX")
    admin_unit = models.ForeignKey(
        "registry.AdminUnit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
        help_text="The area this user acts for. Leave empty for national roles.",
    )

    @property
    def role(self):
        group = self.groups.first()
        return group.name if group else None

    def has_role(self, *role_names):
        return self.groups.filter(name__in=role_names).exists()

    @property
    def is_national(self):
        return self.is_superuser or self.has_role(*roles.NATIONAL_ROLES)

    def scope_unit_ids(self):
        """IDs of the units this user may see, or None for the whole country."""
        if self.is_national:
            return None
        if self.admin_unit is None:
            return []
        return self.admin_unit.descendant_ids()

    def __str__(self):
        return self.get_full_name() or self.username


class SignInEvent(models.Model):
    """Every sign-in attempt, successful or not, for the auditor and for lockout."""

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sign_ins")
    username = models.CharField(max_length=150, help_text="As typed, even if no such user exists.")
    succeeded = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{'Sign-in' if self.succeeded else 'Failed sign-in'} by {self.username} at {self.created_at:%Y-%m-%d %H:%M}"


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(User, exclude_fields=["password", "last_login"])
auditlog.register(SignInEvent)
