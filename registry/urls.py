from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    path("households/", views.HouseholdListView.as_view(), name="household_list"),
    path("households/new/", views.HouseholdCreateView.as_view(), name="household_create"),
    path("households/<int:pk>/", views.HouseholdDetailView.as_view(), name="household_detail"),
    path("households/<int:pk>/edit/", views.HouseholdUpdateView.as_view(), name="household_edit"),
    path("households/<int:pk>/verify/", views.verify_household, name="household_verify"),
    path("groups/", views.EnterpriseGroupListView.as_view(), name="group_list"),
    path("groups/new/", views.EnterpriseGroupCreateView.as_view(), name="group_create"),
    path("groups/<int:pk>/", views.EnterpriseGroupDetailView.as_view(), name="group_detail"),
]
