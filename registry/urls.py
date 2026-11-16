from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    path("households/", views.HouseholdListView.as_view(), name="household_list"),
    path("households/new/", views.HouseholdCreateView.as_view(), name="household_create"),
    path("households/<int:pk>/", views.HouseholdDetailView.as_view(), name="household_detail"),
]
