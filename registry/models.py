from django.core.exceptions import ValidationError
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
