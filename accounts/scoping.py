"""Limit what each user can see to their own area.

Every PDM record links (directly or through other records) to an
administrative unit. `scope_queryset` keeps only the records inside the
user's unit and the units below it. National roles see everything.
"""

from django.core.exceptions import PermissionDenied


def scope_queryset(queryset, user, unit_field="admin_unit"):
    """Filter `queryset` to records whose `unit_field` is inside the user's area.

    `unit_field` is a Django lookup path that ends at an AdminUnit, for
    example "admin_unit" or "household__village".
    """
    if not user.is_authenticated:
        return queryset.none()
    unit_ids = user.scope_unit_ids()
    if unit_ids is None:
        return queryset
    return queryset.filter(**{f"{unit_field}__in": unit_ids})


def unit_in_scope(user, unit):
    """True if `unit` is inside the user's area."""
    unit_ids = user.scope_unit_ids()
    return unit_ids is None or (unit is not None and unit.pk in unit_ids)


def check_unit_in_scope(user, unit):
    if not unit_in_scope(user, unit):
        raise PermissionDenied("This record is outside your area.")
