"""Build a sample parish and one user for every PDM role.

Usage:
    python manage.py seed_demo            # create or update the demo data
    python manage.py seed_demo --password secret123

All data is sample data for demonstrations. Running the command again
updates the same records instead of making duplicates.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts import roles
from accounts.models import User
from registry.models import AdminUnit

Level = AdminUnit.Level

# district -> sub-county -> parish -> villages
UNITS = {
    "Mukono": {
        "Goma": {
            "Seeta": ["Seeta Central", "Kitega", "Bajjo"],
            "Nantabulirwa": ["Nantabulirwa A", "Nantabulirwa B"],
        },
    },
}

# username, first name, last name, role, unit name (None = national), phone
DEMO_USERS = [
    ("household", "Grace", "Nakato", roles.HOUSEHOLD, "Seeta Central", "256700000001"),
    ("groupexec", "Peter", "Ssali", roles.GROUP_EXECUTIVE, "Seeta", "256700000002"),
    ("lc1", "Joseph", "Mukasa", roles.LC1_CHAIRPERSON, "Seeta Central", "256700000003"),
    ("parishchief", "Sarah", "Namubiru", roles.PARISH_CHIEF, "Seeta", "256700000004"),
    ("pdc", "Moses", "Kato", roles.PDC, "Seeta", "256700000005"),
    ("sacco", "Ruth", "Nabirye", roles.SACCO_OFFICIAL, "Seeta", "256700000006"),
    ("subcounty", "David", "Ouma", roles.SUBCOUNTY_OFFICIAL, "Goma", "256700000007"),
    ("district", "Agnes", "Akello", roles.DISTRICT_OFFICIAL, "Mukono", "256700000008"),
    ("national", "Samuel", "Okello", roles.NATIONAL_OFFICIAL, None, "256700000009"),
    ("auditor", "Esther", "Namata", roles.AUDITOR, None, "256700000010"),
]


class Command(BaseCommand):
    help = "Create a sample parish and one demo user for each of the ten PDM roles."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="pdm12345", help="Password for every demo user.")

    @transaction.atomic
    def handle(self, *args, **options):
        units = self.create_units()
        self.create_users(units, options["password"])
        self.stdout.write(self.style.SUCCESS("Demo data ready."))

    def create_units(self):
        units = {}
        for district_name, subcounties in UNITS.items():
            district, _ = AdminUnit.objects.get_or_create(
                name=district_name, level=Level.DISTRICT, parent=None
            )
            units[district_name] = district
            for subcounty_name, parishes in subcounties.items():
                subcounty, _ = AdminUnit.objects.get_or_create(
                    name=subcounty_name, level=Level.SUBCOUNTY, parent=district
                )
                units[subcounty_name] = subcounty
                for parish_name, villages in parishes.items():
                    parish, _ = AdminUnit.objects.get_or_create(
                        name=parish_name, level=Level.PARISH, parent=subcounty
                    )
                    units[parish_name] = parish
                    for village_name in villages:
                        village, _ = AdminUnit.objects.get_or_create(
                            name=village_name, level=Level.VILLAGE, parent=parish
                        )
                        units[village_name] = village
        self.stdout.write(f"  {len(units)} administrative units")
        return units

    def create_users(self, units, password):
        for username, first, last, role, unit_name, phone in DEMO_USERS:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": phone,
                    "admin_unit": units[unit_name] if unit_name else None,
                },
            )
            user.set_password(password)
            user.save()
            user.groups.set([Group.objects.get(name=role)])

        admin, created = User.objects.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password(password)
            admin.save()
        self.stdout.write(f"  {len(DEMO_USERS)} role users and an admin (password: {password})")
