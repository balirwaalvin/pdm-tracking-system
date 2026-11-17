"""Move complaints up a level when they are not resolved within 7 days.

Usage:
    python manage.py escalate_complaints

Parish complaints go to the sub-county, sub-county complaints to the
district. The deploy script runs it; in production it would run daily.
"""

from django.core.management.base import BaseCommand

from feedback.services import escalate_overdue


class Command(BaseCommand):
    help = "Escalate complaints not resolved within 7 days at their level."

    def handle(self, *args, **options):
        moved = escalate_overdue()
        for complaint in moved:
            self.stdout.write(f"  {complaint.reference} now with the {complaint.get_level_display().lower()} office")
        self.stdout.write(self.style.SUCCESS(f"{len(moved)} complaint(s) escalated."))
