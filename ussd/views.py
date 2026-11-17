"""The USSD callback that Africa's Talking calls, and an in-browser simulator for demonstrations."""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts import access
from accounts.mixins import RoleRequiredMixin
from accounts.scoping import scope_queryset
from registry.models import Household

from .menu import respond

SIMULATOR_ROLES = access.roles_for("ussd_simulator")  # from the access policy


@csrf_exempt
@require_POST
def callback(request):
    """Africa's Talking posts sessionId, serviceCode, phoneNumber and text; we reply in plain text."""
    reply = respond(request.POST.get("phoneNumber", ""), request.POST.get("text", ""))
    return HttpResponse(reply, content_type="text/plain")


class SimulatorView(RoleRequiredMixin, TemplateView):
    """A phone screen in the browser that runs the real USSD menu, for demonstrations.

    Officials can only dial as households inside their own area.
    """

    template_name = "ussd/simulator.html"
    allowed_roles = SIMULATOR_ROLES

    def households(self):
        return scope_queryset(
            Household.objects.exclude(phone="").select_related("village"), self.request.user, "village"
        ).order_by("head_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["households"] = self.households()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        phone = request.POST.get("phone", "")
        if not self.households().filter(phone=phone).exists():
            context["error"] = "Choose a household in your area."
            return self.render_to_response(context)

        previous = request.POST.get("session_text", "")
        answer = request.POST.get("answer", "").strip()
        if request.POST.get("action") == "dial":
            text = ""
        else:
            text = f"{previous}*{answer}" if previous else answer
        reply = respond(phone, text)
        context.update(phone=phone, session_text=text, screen=reply[4:], waiting=reply.startswith("CON"))
        return self.render_to_response(context)
