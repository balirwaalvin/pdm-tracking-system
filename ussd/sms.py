"""Send SMS alerts through Africa's Talking.

`send_sms()` is the only way the system sends a text. Every message is
saved in SmsMessage. With no AT_API_KEY set (local work, tests, or before
the sandbox account exists) the message is logged, not sent. A failure at
Africa's Talking is logged too; it never stops the action that caused it.
"""

import logging

from django.conf import settings

from .models import SmsMessage

logger = logging.getLogger("ussd")


def normalise_phone(phone):
    """Turn 0772..., +256772... or 256772... into 256772... (digits only)."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("0"):
        digits = "256" + digits[1:]
    return digits


def send_sms(phone, message, loan=None):
    """Send `message` to `phone`. Returns the saved SmsMessage. Never raises."""
    number = normalise_phone(phone)
    if not number:
        logger.info("SMS not sent: no phone number. %s", message)
        return None

    if not settings.AT_API_KEY:
        logger.info("SMS (logged only, no AT_API_KEY) to %s: %s", number, message)
        return SmsMessage.objects.create(phone=number, message=message, status=SmsMessage.Status.LOGGED, loan=loan)

    try:
        import africastalking

        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        sender = settings.AT_SENDER_ID or None
        africastalking.SMS.send(message, [f"+{number}"], sender)
    except Exception as error:  # the alert must never break the workflow
        logger.warning("SMS to %s failed: %s", number, error)
        return SmsMessage.objects.create(
            phone=number, message=message, status=SmsMessage.Status.FAILED, error=str(error)[:255], loan=loan
        )
    logger.info("SMS sent to %s", number)
    return SmsMessage.objects.create(phone=number, message=message, status=SmsMessage.Status.SENT, loan=loan)
