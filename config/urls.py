from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "PDM Tracking System administration"
admin.site.site_title = "PDM Tracking System"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("registry/", include("registry.urls")),
    path("saccos/", include("saccos.urls")),
    path("loans/", include("loans.urls")),
    path("", include("dashboards.urls")),
]
