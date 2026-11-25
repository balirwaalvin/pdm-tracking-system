from django.contrib import admin
from django.urls import include, path

from registry import views as registry_views

admin.site.site_header = "PDM Tracking System administration"
admin.site.site_title = "PDM Tracking System"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("registry/", include("registry.urls")),
    path("saccos/", include("saccos.urls")),
    path("loans/", include("loans.urls")),
    path("ussd/", include("ussd.urls")),
    path("complaints/", include("feedback.urls")),
    path("eligibility/", registry_views.EligibilityView.as_view(), name="eligibility"),
    path("", include("dashboards.urls")),
]
