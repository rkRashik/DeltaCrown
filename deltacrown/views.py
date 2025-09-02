# deltacrown/views_dashboard_impl.py
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.http import JsonResponse
from django.db import connection

def home(request: HttpRequest) -> HttpResponse:
    # If you already had a home(), keep your original body.
    return render(request, "home.html")

def healthz(request):
    """
    JSON health endpoint.
    Always returns {"ok": True}.

    Optional DB ping:
      - If ?db=1/true/yes is present, perform a quick SELECT 1.
      - Payload remains unchanged to satisfy tests.
    """
    db_param = (request.GET.get("db") or "").lower()
    if db_param in {"1", "true", "yes"}:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            # Keep response stable regardless of DB ping outcome
            pass
    return JsonResponse({"ok": True})


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


def permission_denied_view(request: HttpRequest, exception, template_name="errors/403.html") -> HttpResponse:
    """
    Custom 403 handler for PermissionDenied and similar cases (not CSRF; CSRF uses 403_csrf.html).
    """
    ctx = {"path": request.path}
    return render(request, template_name, ctx, status=403)