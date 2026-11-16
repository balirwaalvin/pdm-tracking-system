"""Flag loans as defaulted once an instalment is 90 or more days overdue.

Usage:
    python manage.py flag_defaults                    # check against today
    python manage.py flag_defaults --as-of 2026-12-31 # check against another date

Run it daily (the deploy script also runs it). The change is made by the
system, so the audit log shows no person against it.
"""

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from loans import workflow
from loans.models import LoanApplication


class Command(BaseCommand):
    help = "Move loans with an instalment 90 or more days overdue to Defaulted."

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of", type=datetime.date.fromisoformat, default=None, help="Date to check against (YYYY-MM-DD)."
        )

    def handle(self, *args, **options):
        day = options["as_of"] or timezone.localdate()
        loans = LoanApplication.objects.filter(
            status__in=[LoanApplication.Status.DISBURSED, LoanApplication.Status.REPAYING]
        ).select_related("disbursement", "household")
        flagged = [loan for loan in loans if workflow.flag_default(loan, day)]
        for loan in flagged:
            self.stdout.write(f"  Defaulted: {loan}")
        self.stdout.write(self.style.SUCCESS(f"{len(flagged)} loan(s) flagged as defaulted on {day}."))
