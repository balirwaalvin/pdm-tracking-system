"""Account pages: the auditor's sign-in log, and the administrator's demo reset."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from . import access
from .demo import reset_demo_data
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


class ResetDemoView(LoginRequiredMixin, TemplateView):
    """The administrator resets the sample data from the browser (Render's free tier has no shell).

    Superusers only; a POST with the word RESET typed in, so it cannot happen by accident.
    """

    template_name = "accounts/reset_demo.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            raise PermissionDenied("Only the system administrator can reset the demo data.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get("confirm", "").strip() != "RESET":
            messages.error(request, "Type RESET in capitals to confirm.")
            return redirect("reset_demo")
        removed = reset_demo_data()
        messages.success(request, f"Demo data reset: {removed} records removed and the sample data rebuilt.")
        return redirect("home")
