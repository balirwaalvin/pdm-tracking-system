from django.contrib import admin

from .models import AdminUnit


@admin.register(AdminUnit)
class AdminUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent")
    list_filter = ("level",)
    search_fields = ("name",)
    autocomplete_fields = ("parent",)
