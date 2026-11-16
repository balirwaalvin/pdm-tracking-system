from django import forms

from .models import FundRelease


class FundReleaseForm(forms.ModelForm):
    class Meta:
        model = FundRelease
        fields = ["amount", "financial_year", "release_date", "reference"]
        widgets = {"release_date": forms.DateInput(attrs={"type": "date"})}
