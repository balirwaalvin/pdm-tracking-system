from django.urls import path

from . import views

app_name = "saccos"

urlpatterns = [
    path("", views.SaccoListView.as_view(), name="sacco_list"),
    path("<int:pk>/", views.SaccoDetailView.as_view(), name="sacco_detail"),
    path("checklist/<int:pk>/toggle/", views.toggle_checklist_item, name="toggle_checklist"),
    path("<int:sacco_pk>/releases/new/", views.FundReleaseCreateView.as_view(), name="release_create"),
    path("releases/<int:pk>/confirm/", views.confirm_release, name="release_confirm"),
]
