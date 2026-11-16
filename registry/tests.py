from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import AdminUnit

Level = AdminUnit.Level


class AdminUnitTests(TestCase):
    def setUp(self):
        self.district = AdminUnit.objects.create(name="Mukono", level=Level.DISTRICT)
        self.subcounty = AdminUnit.objects.create(name="Goma", level=Level.SUBCOUNTY, parent=self.district)
        self.parish = AdminUnit.objects.create(name="Seeta", level=Level.PARISH, parent=self.subcounty)
        self.village = AdminUnit.objects.create(name="Kitega", level=Level.VILLAGE, parent=self.parish)

    def test_descendants_of_district_include_every_level(self):
        ids = self.district.descendant_ids()
        self.assertCountEqual(ids, [self.district.pk, self.subcounty.pk, self.parish.pk, self.village.pk])

    def test_descendants_can_exclude_self(self):
        self.assertEqual(self.parish.descendant_ids(include_self=False), [self.village.pk])

    def test_ancestors_run_nearest_first(self):
        self.assertEqual(self.village.ancestors(), [self.parish, self.subcounty, self.district])

    def test_parish_must_sit_inside_a_subcounty(self):
        bad = AdminUnit(name="Wrong", level=Level.PARISH, parent=self.district)
        with self.assertRaises(ValidationError):
            bad.clean()

    def test_district_cannot_have_a_parent(self):
        bad = AdminUnit(name="Wrong", level=Level.DISTRICT, parent=self.district)
        with self.assertRaises(ValidationError):
            bad.clean()
