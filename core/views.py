from django.shortcuts import render
from django.conf import settings


def home(request):
    return render(request, "core/home.html", {
        "tracker_url": settings.TRACKER_LIVE_URL,
    })
