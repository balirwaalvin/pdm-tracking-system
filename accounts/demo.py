"""Put the sample data back to its starting state, for rehearsals and the presentation.

Everything people did during a demo goes: households, groups, SACCOs, loans,
complaints, stories, SMS messages, sign-ins and the audit trail. Then the
sample data is created again (with dates relative to today), loans that
are 90 days overdue are flagged, and overdue complaints are escalated.
Administrative units and user accounts are kept and their passwords reset.

This is for sample data only. A real system would never delete its audit trail.
"""

from auditlog.models import LogEntry
from django.apps import apps
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connection, transaction

from feedback.models import Complaint, ComplaintResponse, SuccessStory
from loans.models import Appraisal, Disbursement, LoanApplication, Repayment
from registry.models import EnterpriseGroup, Household
from saccos.models import FundRelease, Sacco, SaccoChecklistItem
from ussd.models import SmsMessage

from .models import SignInEvent

# Children before parents, so protected foreign keys never block a delete.
RESET_ORDER = [
    SmsMessage, ComplaintResponse, Complaint, SuccessStory, Repayment, Disbursement, Appraisal,
    LoanApplication, Household, EnterpriseGroup, FundRelease, SaccoChecklistItem, Sacco, SignInEvent,
]


def reset_demo_data(stdout=None):
    """Delete demo activity and rebuild the sample data. Returns how many rows were removed."""
    quiet = open("/dev/null", "w")
    removed = 0
    with transaction.atomic():
        for model in RESET_ORDER:
            count, _ = model.objects.all().delete()
            removed += count
        # Restart numbering, so "Loan 1" and complaint PDM-000001 are the same in every rehearsal.
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), RESET_ORDER):
                cursor.execute(sql)
        call_command("seed_demo", stdout=stdout or quiet)
        call_command("flag_defaults", stdout=stdout or quiet)
        call_command("escalate_complaints", stdout=stdout or quiet)
        # The rebuilt records start with a clean audit trail.
        LogEntry.objects.all().delete()
    return removed


APPS_WITH_DEMO_DATA = ("accounts", "registry", "saccos", "loans", "feedback", "ussd")


def sync_sequences():
    """Set each table's numbering to follow its highest existing record.

    PostgreSQL does not undo a numbering change when a transaction rolls back, so a
    reset cut off half-way (for example by a server time limit) can leave numbering
    behind existing rows, and every new record would then collide. Running this
    before seeding repairs that.
    """
    models = [m for m in apps.get_models() if m._meta.app_label in APPS_WITH_DEMO_DATA]
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), models):
            cursor.execute(sql)
