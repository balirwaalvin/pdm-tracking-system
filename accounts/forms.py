"""The sign-in form, with lockout after repeated failed attempts."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .security import LOCKOUT_MINUTES, is_locked_out


class SignInForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username")
        if username and is_locked_out(username):
            raise forms.ValidationError(
                f"Too many failed attempts for this account. Wait {LOCKOUT_MINUTES} minutes and try again, "
                "or ask your administrator.",
                code="locked_out",
            )
        return super().clean()
