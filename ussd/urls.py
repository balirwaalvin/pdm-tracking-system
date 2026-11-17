from django.urls import path

from . import views

app_name = "ussd"

urlpatterns = [
    path("callback/", views.callback, name="callback"),
    path("simulator/", views.SimulatorView.as_view(), name="simulator"),
]
