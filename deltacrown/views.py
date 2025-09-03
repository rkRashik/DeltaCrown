from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    """
    Public homepage.
    """
    return render(request, "homepage.html")


def healthz(request):
    """Simple health check endpoint."""
    return HttpResponse("OK")
