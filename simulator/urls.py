from django.urls import path
from . import views

app_name = "simulator"

urlpatterns = [
    path("", views.simulator_page, name="page"),
    path("run/", views.simulate, name="run"),
]
