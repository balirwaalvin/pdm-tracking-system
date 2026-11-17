from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("", views.ComplaintListView.as_view(), name="complaint_list"),
    path("new/", views.ComplaintCreateView.as_view(), name="complaint_create"),
    path("<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint_detail"),
    path("<int:pk>/respond/", views.respond_to_complaint, name="complaint_respond"),
]
