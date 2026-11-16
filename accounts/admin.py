from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role_name", "admin_unit", "phone", "is_active")
    list_filter = ("groups", "is_active", "admin_unit__level")
    search_fields = ("username", "first_name", "last_name", "phone")
    autocomplete_fields = ("admin_unit",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("PDM details", {"fields": ("phone", "admin_unit")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("PDM details", {"fields": ("first_name", "last_name", "phone", "admin_unit", "groups")}),
    )

    @admin.display(description="Role")
    def role_name(self, obj):
        return obj.role or "-"
