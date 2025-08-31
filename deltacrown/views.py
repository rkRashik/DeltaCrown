# deltacrown/views.py
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse


def home(request: HttpRequest) -> HttpResponse:
    # If you already had a home(), keep your original body.
    return render(request, "home.html")


def page_not_found_view(request: HttpRequest, exception, template_name="errors/404.html") -> HttpResponse:
    """
    Custom 404 handler. Django calls this with (request, exception).
    """
    ctx = {"path": request.path}
    return render(request, template_name, ctx, status=404)


def server_error_view(request: HttpRequest, template_name="errors/500.html") -> HttpResponse:
    """
    Custom 500 handler. Called without 'exception'.
    """
    return render(request, template_name, status=500)
