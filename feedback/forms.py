"""Forms for raising a complaint and for an official's response."""

from django import forms

from .models import Complaint


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
