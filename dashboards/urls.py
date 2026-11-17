from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("my-household/", views.MyHouseholdView.as_view(), name="my_household"),
    path("audit/", views.AuditLogView.as_view(), name="audit_log"),
    path("parishes/", views.PublicParishListView.as_view(), name="public_parishes"),
    path("parishes/<int:pk>/", views.PublicParishView.as_view(), name="public_parish"),
    path("parishes/<int:pk>/data.csv", views.parish_open_data, name="public_parish_data"),
]
