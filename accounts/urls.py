from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import SignInForm

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True, authentication_form=SignInForm),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password/",
        auth_views.PasswordChangeView.as_view(success_url=reverse_lazy("password_change_done")),
        name="password_change",
    ),
    path("password/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("sign-ins/", views.SignInLogView.as_view(), name="sign_in_log"),
    path("reset-demo/", views.ResetDemoView.as_view(), name="reset_demo"),
]
