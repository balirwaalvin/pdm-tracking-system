from django.urls import path

from . import views

app_name = "loans"

urlpatterns = [
    path("", views.LoanListView.as_view(), name="loan_list"),
    path("new/", views.LoanCreateView.as_view(), name="loan_create"),
]
