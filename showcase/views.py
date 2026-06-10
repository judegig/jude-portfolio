from django.shortcuts import render
from django.conf import settings


def showcase_page(request):
    return render(request, "showcase/showcase.html", {
        "tracker_url": settings.TRACKER_LIVE_URL,
    })
