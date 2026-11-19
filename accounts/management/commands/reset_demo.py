"""Reset the sample data to its starting state.

Usage:
    python manage.py reset_demo --yes

Deletes everything done during a demo (including the audit trail) and
rebuilds the sample data. On the live site, the admin user can do the same
from the "Reset demo data" page.
"""

from django.core.management.base import BaseCommand, CommandError

from accounts.demo import reset_demo_data


class Command(BaseCommand):
    help = "Delete demo activity and rebuild the sample data (sample data only)."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Confirm that you want to delete the demo data.")

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError("This deletes all demo data, including the audit trail. Run it again with --yes.")
        removed = reset_demo_data(self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Demo data reset ({removed} rows removed, sample data rebuilt)."))
