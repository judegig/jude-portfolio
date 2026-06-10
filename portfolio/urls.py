from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls", namespace="core")),
    path("agent/", include("agent.urls", namespace="agent")),
    path("showcase/", include("showcase.urls", namespace="showcase")),
    path("simulator/", include("simulator.urls", namespace="simulator")),
]
