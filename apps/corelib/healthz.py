# apps/corelib/healthz.py
from __future__ import annotations

from django.http import HttpResponse
from django.db import connection


def healthz(request):
    """
    Lightweight health endpoint.
    - Always returns 200 OK with 'ok' body.
    - Optional DB ping if query param db=1/true is present.
    """
    db_param = (request.GET.get("db") or "").lower()
    if db_param in {"1", "true", "yes"}:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            # Still return 200 to avoid flapping orchestration; keep it ultra fast.
            # If you want to fail on DB issues, change to: return HttpResponse("db-fail", status=500)
            pass
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")
