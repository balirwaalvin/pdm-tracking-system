"""The USSD callback that Africa's Talking calls, and an in-browser simulator for demonstrations."""

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts import access, roles
from accounts.mixins import RoleRequiredMixin
from accounts.scoping import scope_queryset
from registry.models import Household

from .menu import respond

SIMULATOR_ROLES = access.roles_for("ussd_simulator")  # from the access policy


@csrf_exempt
@require_POST
def callback(request):
    """Africa's Talking posts sessionId, serviceCode, phoneNumber and text; we reply in plain text.

    If USSD_CALLBACK_TOKEN is set, the callback address must carry ?token=<it>, so strangers
    cannot read a household's status by posting its phone number.
    """
    expected = settings.USSD_CALLBACK_TOKEN
    if expected and not constant_time_compare(request.GET.get("token", ""), expected):
        return HttpResponseForbidden("END Not allowed.", content_type="text/plain")
    reply = respond(request.POST.get("phoneNumber", ""), request.POST.get("text", ""))
    return HttpResponse(reply, content_type="text/plain")


class SimulatorView(RoleRequiredMixin, TemplateView):
    """A phone screen in the browser that runs the real USSD menu.

    A household dials with its own number only. Officials (the help-desk roles)
    can dial as any household inside their area, to help residents who ask.
    """

    template_name = "ussd/simulator.html"
    allowed_roles = SIMULATOR_ROLES

    def households(self):
        user = self.request.user
        if user.has_role(roles.HOUSEHOLD):  # never a neighbour's number, even in the same village
            return Household.objects.filter(account=user).exclude(phone="").select_related("village")
        return scope_queryset(
            Household.objects.exclude(phone="").select_related("village"), self.request.user, "village"
        ).order_by("head_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["households"] = self.households()
        context["own_phone"] = self.request.user.has_role(roles.HOUSEHOLD)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        phone = request.POST.get("phone", "")
        if not self.households().filter(phone=phone).exists():
            context["error"] = "You can only dial with your own number." if context["own_phone"] else "Choose a household in your area."
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
