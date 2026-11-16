from django.urls import path

from . import views

app_name = "registry"

urlpatterns = [
    path("households/", views.HouseholdListView.as_view(), name="household_list"),
]
