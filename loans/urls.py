from django.urls import path

from . import views

app_name = "loans"

urlpatterns = [
    path("", views.LoanListView.as_view(), name="loan_list"),
    path("new/", views.LoanCreateView.as_view(), name="loan_create"),
    path("<int:pk>/", views.LoanDetailView.as_view(), name="loan_detail"),
    path("<int:pk>/submit/", views.submit_loan, name="loan_submit"),
    path("<int:pk>/appraise/", views.AppraisalCreateView.as_view(), name="loan_appraise"),
    path("<int:pk>/decide/", views.decide_loan, name="loan_decide"),
]
