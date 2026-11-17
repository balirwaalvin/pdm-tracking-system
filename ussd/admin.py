from django.contrib import admin

from .models import SmsMessage


@admin.register(SmsMessage)
class SmsMessageAdmin(admin.ModelAdmin):
    list_display = ["created_at", "phone", "status", "message"]
    list_filter = ["status"]
    search_fields = ["phone", "message"]
    readonly_fields = [field.name for field in SmsMessage._meta.fields]
