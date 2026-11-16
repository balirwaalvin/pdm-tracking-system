from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class AdminUnit(models.Model):
    """A level of local government: district, sub-county, parish or village.

    Units form a tree. Every PDM record is linked to a unit, and users only
    see records inside their own unit and the units below it.
    """

    class Level(models.TextChoices):
        DISTRICT = "district", "District"
        SUBCOUNTY = "subcounty", "Sub-county"
        PARISH = "parish", "Parish"
        VILLAGE = "village", "Village"

    # The level each unit's parent must have.
    PARENT_LEVEL = {
        Level.DISTRICT: None,
        Level.SUBCOUNTY: Level.DISTRICT,
        Level.PARISH: Level.SUBCOUNTY,
        Level.VILLAGE: Level.PARISH,
    }

    name = models.CharField(max_length=120)
    level = models.CharField(max_length=20, choices=Level.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    class Meta:
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="unique_unit_name_per_parent"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

    def clean(self):
        expected = self.PARENT_LEVEL.get(self.level)
        if expected is None and self.parent is not None:
            raise ValidationError("A district cannot have a parent unit.")
        if expected is not None and (self.parent is None or self.parent.level != expected):
            raise ValidationError(
                f"A {self.get_level_display().lower()} must sit inside a {expected.label.lower()}."
            )

    def descendant_ids(self, include_self=True):
        """IDs of this unit and every unit below it."""
        ids = [self.pk] if include_self else []
        frontier = [self.pk]
        while frontier:
            children = list(AdminUnit.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            ids.extend(children)
            frontier = children
        return ids

    def ancestors(self):
        """Units above this one, nearest first."""
        chain, unit = [], self.parent
        while unit is not None:
            chain.append(unit)
            unit = unit.parent
        return chain



class EnterpriseGroup(models.Model):
    """A group of 10 to 30 households that share an enterprise and apply for loans together."""

    class Enterprise(models.TextChoices):
        POULTRY = "poultry", "Poultry"
        PIGGERY = "piggery", "Piggery"
        DAIRY = "dairy", "Dairy cattle"
        GOATS = "goats", "Goats"
        COFFEE = "coffee", "Coffee"
        PRODUCE = "produce", "Food crops"
        FISH = "fish", "Fish farming"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150)
    enterprise = models.CharField(max_length=20, choices=Enterprise.choices)
    parish = models.ForeignKey(
        AdminUnit,
        on_delete=models.PROTECT,
        related_name="enterprise_groups",
        limit_choices_to={"level": AdminUnit.Level.PARISH},
    )
    registration_number = models.CharField(max_length=50, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["parish", "name"], name="unique_group_name_per_parish"),
        ]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


nin_validator = RegexValidator(
    r"^[A-Z0-9]{14}$",
    "A National Identification Number has 14 letters and digits, for example CM90012345ABCD.",
)


class Household(models.Model):
    """A household profiled under PDM, identified by the NIN of its head."""

    class Sex(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"

    class AgeGroup(models.TextChoices):
        YOUTH = "youth", "Youth (18 to 35)"
        ADULT = "adult", "Adult (36 to 59)"
        OLDER = "older", "Older person (60 and above)"

    class WealthRank(models.TextChoices):
        VERY_POOR = "very_poor", "Very poor"
        POOR = "poor", "Poor"
        MIDDLE = "middle", "Middle"
        BETTER_OFF = "better_off", "Better off"

    class Verification(models.TextChoices):
        PENDING = "pending", "Waiting for LC I"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    head_name = models.CharField("Head of household", max_length=150)
    nin = models.CharField("NIN", max_length=14, unique=True, validators=[nin_validator])
    phone = models.CharField(max_length=15, blank=True, help_text="Format: 2567XXXXXXXX")
    sex = models.CharField(max_length=1, choices=Sex.choices)
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices)
    has_disability = models.BooleanField("Person with disability", default=False)
    household_size = models.PositiveSmallIntegerField(default=1)
    wealth_rank = models.CharField(max_length=12, choices=WealthRank.choices)
    village = models.ForeignKey(
        AdminUnit,
        on_delete=models.PROTECT,
        related_name="households",
        limit_choices_to={"level": AdminUnit.Level.VILLAGE},
    )
    enterprise_group = models.ForeignKey(
        EnterpriseGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="members"
    )

    verification = models.CharField(
        max_length=10, choices=Verification.choices, default=Verification.PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.CharField(max_length=255, blank=True)

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["head_name"]

    def __str__(self):
        return f"{self.head_name} ({self.nin})"

    def save(self, *args, **kwargs):
        self.nin = self.nin.strip().upper()
        super().save(*args, **kwargs)

    @property
    def parish(self):
        return self.village.parent


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(AdminUnit)
