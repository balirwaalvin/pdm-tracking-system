from django.urls import path

from . import views

app_name = "saccos"

urlpatterns = [
    path("", views.SaccoListView.as_view(), name="sacco_list"),
    path("<int:pk>/", views.SaccoDetailView.as_view(), name="sacco_detail"),
]
