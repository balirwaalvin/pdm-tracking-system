from django.contrib import admin

from .models import FundRelease, Sacco, SaccoChecklistItem


class ChecklistInline(admin.TabularInline):
    model = SaccoChecklistItem
    extra = 0
    readonly_fields = ("checked_by", "checked_at")


@admin.register(Sacco)
class SaccoAdmin(admin.ModelAdmin):
    list_display = ("name", "registration_number", "parish", "status")
    list_filter = ("status",)
    search_fields = ("name", "registration_number")
    inlines = [ChecklistInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.ensure_checklist()


@admin.register(FundRelease)
class FundReleaseAdmin(admin.ModelAdmin):
    list_display = ("sacco", "amount", "financial_year", "release_date", "confirmed_by")
    list_filter = ("financial_year",)
    readonly_fields = ("recorded_by", "confirmed_by", "confirmed_at")
