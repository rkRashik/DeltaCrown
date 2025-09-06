# apps/tournaments/views/attendance.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from ..models import Match
from ..models.attendance import MatchAttendance


def _redirect_back(request: HttpRequest, default="tournaments:my_matches") -> HttpResponseRedirect:
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect(default)


@login_required
def toggle_attendance(request: HttpRequest, match_id: int, action: str) -> HttpResponseRedirect:
    """
    Self-service attendance:
      /tournaments/match/<id>/attendance/<action>/
    action ∈ {confirm, decline, late, absent}
    """
    if request.method not in ("POST", "GET"):
        raise Http404()

    match = get_object_or_404(Match, id=match_id)
    status_map = {
        "confirm": "confirmed",
        "decline": "declined",
        "late": "late",
        "absent": "absent",
    }
    status = status_map.get(action)
    if not status:
        raise Http404("Invalid action")

    obj, _ = MatchAttendance.objects.get_or_create(user=request.user, match=match)
    obj.status = status
    obj.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Attendance set to {status} for match #{match.id}.")
    return _redirect_back(request)


@login_required
def quick_action(request: HttpRequest, match_id: int, action: str) -> HttpResponseRedirect:
    """
    Organizer/player quick actions placeholders:
      /tournaments/match/<id>/quick/<action>/
    Supported (safe no-ops or lightweight):
      • notify      -> success toast (wire later to real notifications)
      • remind_team -> success toast (stub)
    """
    if request.method not in ("POST", "GET"):
        raise Http404()

    _ = get_object_or_404(Match, id=match_id)

    if action in ("notify", "remind_team"):
        messages.success(request, "Reminder scheduled. (Stub — wire to notifications later.)")
        return _redirect_back(request)
    raise Http404("Unknown quick action")
