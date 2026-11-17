"""Forms for complaints, responses and success stories."""

from django import forms

from accounts.scoping import scope_queryset
from registry.models import Household

from .models import Complaint, SuccessStory


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["category", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4, "maxlength": 1000})}
        labels = {"category": "What is the problem about?", "description": "Tell us what happened"}

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 10:
            raise forms.ValidationError("Please describe the problem in a few words.")
        return text


class ResponseForm(forms.Form):
    status = forms.ChoiceField(
        choices=[(Complaint.Status.IN_PROGRESS, "Being handled"), (Complaint.Status.RESOLVED, "Resolved")],
        widget=forms.RadioSelect,
        initial=Complaint.Status.IN_PROGRESS,
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="The household receives this by SMS. Say what you did or will do.",
    )


class StoryForm(forms.ModelForm):
    """Draft or edit a success story. Only verified households in the user's area are offered."""

    class Meta:
        model = SuccessStory
        fields = ["household", "title", "story", "consent_given", "consent_method", "show_name"]
        widgets = {"story": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        households = Household.objects.filter(verification=Household.Verification.VERIFIED).select_related("village")
        if user is not None:
            households = scope_queryset(households, user, "village")
        self.fields["household"].queryset = households
        self.fields["consent_method"].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("consent_given") and not cleaned.get("consent_method"):
            self.add_error("consent_method", "Say how the household gave consent.")
        if cleaned.get("show_name") and not cleaned.get("consent_given"):
            self.add_error("show_name", "The household must agree to publication before agreeing to be named.")
        return cleaned


class StoryCheckForm(forms.Form):
    decision = forms.ChoiceField(choices=[("approve", "Approve and publish"), ("reject", "Send back")], widget=forms.RadioSelect)
    records_match = forms.BooleanField(
        required=False, label="I checked this story against the household's records shown on this page"
    )
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Required when sending back.")
