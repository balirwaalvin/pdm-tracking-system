from django import forms
from django.urls import reverse
from django.utils.html import format_html

from accounts.scoping import scope_queryset

from .models import AdminUnit, EnterpriseGroup, Household


class HouseholdForm(forms.ModelForm):
    """Register or edit a household. Villages and groups are limited to the user's area."""

    class Meta:
        model = Household
        fields = [
            "head_name",
            "nin",
            "phone",
            "sex",
            "age_group",
            "has_disability",
            "household_size",
            "wealth_rank",
            "village",
            "enterprise_group",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        villages = AdminUnit.objects.filter(level=AdminUnit.Level.VILLAGE)
        groups = EnterpriseGroup.objects.all()
        if user is not None:
            villages = scope_queryset(villages, user, "pk")
            groups = scope_queryset(groups, user, "parish")
        self.fields["village"].queryset = villages.select_related("parent")
        self.fields["enterprise_group"].queryset = groups
        self.fields["enterprise_group"].required = False

    def clean_nin(self):
        nin = self.cleaned_data["nin"].strip().upper().replace(" ", "")
        existing = Household.objects.filter(nin=nin).exclude(pk=self.instance.pk).first()
        if existing:
            url = reverse("registry:household_detail", args=[existing.pk])
            raise forms.ValidationError(
                format_html(
                    'This NIN is already registered to <a href="{}">{}</a> in {}.',
                    url,
                    existing.head_name,
                    existing.village.name,
                )
            )
        return nin

    def clean(self):
        cleaned = super().clean()
        village, group = cleaned.get("village"), cleaned.get("enterprise_group")
        if village and group and group.parish_id != village.parent_id:
            self.add_error("enterprise_group", "The group must be in the same parish as the household.")
        return cleaned


class EnterpriseGroupForm(forms.ModelForm):
    class Meta:
        model = EnterpriseGroup
        fields = ["name", "enterprise", "parish", "registration_number"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        parishes = AdminUnit.objects.filter(level=AdminUnit.Level.PARISH)
        if user is not None:
            parishes = scope_queryset(parishes, user, "pk")
        self.fields["parish"].queryset = parishes
