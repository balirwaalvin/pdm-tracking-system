from django.contrib import admin

from .models import Complaint, ComplaintResponse


class ResponseInline(admin.TabularInline):
    model = ComplaintResponse
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["reference", "household", "category", "level", "status", "created_at"]
    list_filter = ["status", "level", "category", "channel"]
    inlines = [ResponseInline]
