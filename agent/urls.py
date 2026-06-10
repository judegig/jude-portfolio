from django.urls import path
from . import views

app_name = "agent"

urlpatterns = [
    path("", views.agent_page, name="page"),
    path("chat/", views.agent_chat, name="chat"),
    path("clear/", views.agent_clear, name="clear"),
]
