from django.contrib import admin

from .models import Appraisal, LoanApplication


class AppraisalInline(admin.StackedInline):
    model = Appraisal
    extra = 0
    readonly_fields = ("appraised_by", "appraised_at")


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("pk", "household", "sacco", "amount", "status", "created_at")
    list_filter = ("status", "sacco")
    search_fields = ("household__head_name", "household__nin")
    inlines = [AppraisalInline]
