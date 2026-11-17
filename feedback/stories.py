"""The success story workflow: draft, record consent, submit, PDC check.

A story reaches the public only when the household has given recorded
consent, the household is verified, and the PDC has checked the story
against the household's records and approved it.
"""

from django.utils import timezone

from registry.models import Household

from .models import SuccessStory

Status = SuccessStory.Status


class StoryError(Exception):
    """Raised when a step is not allowed; the message says why, for the user."""


def record_consent(story, user):
    """Stamp who recorded the consent and when, the first time it is given."""
    if story.consent_given and story.consent_recorded_at is None:
        story.consent_recorded_by = user
        story.consent_recorded_at = timezone.now()
    if not story.consent_given:
        story.consent_recorded_by = None
        story.consent_recorded_at = None
        story.show_name = False


def submit(story, user):
    if story.status not in (Status.DRAFT, Status.REJECTED):
        raise StoryError("Only a draft, or a story the PDC sent back, can be submitted.")
    if not (story.consent_given and story.consent_method):
        raise StoryError("Record the household's consent, and how it was given, before submitting.")
    if story.household.verification != Household.Verification.VERIFIED:
        raise StoryError("Only stories about verified households can be published.")
    story.status = Status.SUBMITTED
    story.save()


def check(story, user, approve, note="", records_match=False):
    """The PDC approves (after checking the records) or sends the story back with a reason."""
    if story.status != Status.SUBMITTED:
        raise StoryError("This story is not waiting for a check.")
    if approve and not records_match:
        raise StoryError("Confirm that you checked the story against the household's records.")
    if not approve and not note.strip():
        raise StoryError("Say why the story is sent back, so it can be corrected.")
    story.status = Status.APPROVED if approve else Status.REJECTED
    story.checked_by = user
    story.checked_at = timezone.now()
    story.check_note = note.strip()
    story.save()
