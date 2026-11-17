"""Account pages: the auditor's sign-in log."""

from django.views.generic import ListView

from . import access
from .mixins import RoleRequiredMixin
from .models import SignInEvent


class SignInLogView(RoleRequiredMixin, ListView):
    """Every sign-in attempt, newest first. Read-only, for the auditor."""

    allowed_roles = access.roles_for("sign_in_log")
    template_name = "accounts/sign_in_log.html"
    context_object_name = "events"
    paginate_by = 50

    def get_queryset(self):
        events = SignInEvent.objects.select_related("user")
        if self.request.GET.get("result") == "failed":
            events = events.filter(succeeded=False)
        if self.request.GET.get("username"):
            events = events.filter(username=self.request.GET["username"])
        return events
