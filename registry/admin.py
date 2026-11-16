from django.contrib import admin

from .models import AdminUnit


@admin.register(AdminUnit)
class AdminUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent")
    list_filter = ("level",)
    search_fields = ("name",)
    autocomplete_fields = ("parent",)


from .models import EnterpriseGroup, Household  # noqa: E402


@admin.register(EnterpriseGroup)
class EnterpriseGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "enterprise", "parish", "registration_number")
    list_filter = ("enterprise", "parish")
    search_fields = ("name", "registration_number")


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("head_name", "nin", "village", "wealth_rank", "verification", "enterprise_group")
    list_filter = ("verification", "wealth_rank", "sex", "age_group", "has_disability")
    search_fields = ("head_name", "nin", "phone")
    autocomplete_fields = ("village",)
    readonly_fields = ("verified_by", "verified_at", "registered_by", "created_at")
