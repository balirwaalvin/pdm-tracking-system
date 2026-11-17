"""The USSD callback that Africa's Talking calls for each step of a session."""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .menu import respond


@csrf_exempt
@require_POST
def callback(request):
    """Africa's Talking posts sessionId, serviceCode, phoneNumber and text; we reply in plain text."""
    reply = respond(request.POST.get("phoneNumber", ""), request.POST.get("text", ""))
    return HttpResponse(reply, content_type="text/plain")
