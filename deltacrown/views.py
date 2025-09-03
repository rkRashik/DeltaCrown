from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    """
    Temporary homepage renderer.
    Renders base.html so the site loads while we add homepage.html next.
    """
    return render(request, "base.html")


def healthz(request):
    """Simple health check endpoint."""
    return HttpResponse("OK")
