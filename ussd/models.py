"""A record of every SMS alert the system tried to send, so officials and auditors can see it."""

from django.db import models


class SmsMessage(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        LOGGED = "logged", "Recorded (SMS gateway off)"
        FAILED = "failed", "Failed"

    phone = models.CharField(max_length=16)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.CharField(max_length=255, blank=True)
    loan = models.ForeignKey(
        "loans.LoanApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS message"

    def __str__(self):
        return f"SMS to {self.phone} ({self.get_status_display()})"


from auditlog.registry import auditlog  # noqa: E402

auditlog.register(SmsMessage)
