# apps/tournaments/views/attendance.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import localtime, get_current_timezone

from ..models import Match
from ..models.attendance import MatchAttendance

# Optional notifications service
try:
    from apps.notifications.services import emit as notify_emit
except Exception:
    notify_emit = None


def _redirect_back(request: HttpRequest, default="tournaments:my_matches") -> HttpResponseRedirect:
    nxt = request.POST.get("next") or request.GET.get("next")
    return redirect(nxt) if nxt else redirect(reverse(default))


def _attendance_subject_for(request: HttpRequest):
    """
    Return the object to store in MatchAttendance.user, matching the FK's model.
    Works whether it's auth.User or UserProfile.
    """
    rel_model = MatchAttendance._meta.get_field("user").remote_field.model
    if isinstance(request.user, rel_model):
        return request.user
    prof = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
    if prof and isinstance(prof, rel_model):
        return prof
    label = getattr(rel_model._meta, "label_lower", "")
    if label in ("auth.user", "users.user"):
        return request.user
    return prof or request.user


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
        raise Http404("Unknown attendance action")

    attendee = _attendance_subject_for(request)

    MatchAttendance.objects.update_or_create(
        user=attendee,
        match=match,
        defaults={"status": status},
    )
    messages.success(request, f"Attendance marked “{status}”.")
    return _redirect_back(request)


@login_required
def quick_action(request: HttpRequest, match_id: int, action: str) -> HttpResponseRedirect:
    """
    Organizer/player quick actions:
      /tournaments/match/<id>/quick/<action>/
    Supported:
      • notify      -> (alias of remind_team for now)
      • remind_team -> email teammates about this match (rate-limited)
    """
    if request.method not in ("POST", "GET"):
        raise Http404()

    match = get_object_or_404(Match, id=match_id)

    if action not in ("notify", "remind_team"):
        raise Http404("Unknown quick action")

    # Rate limit: per-user per-match every 10 minutes
    rl_key = f"remind_team:{request.user.id}:{match.id}"
    if cache.get(rl_key):
        messages.info(request, "A reminder was recently sent. Try again in a few minutes.")
        return _redirect_back(request)

    # Determine recipients
    try:
        from apps.teams.models import TeamMembership
        profile = getattr(request.user, "profile", None) or getattr(request.user, "userprofile", None)
        recipients_users = []

        if match.team_a_id or match.team_b_id:
            team = None
            if match.team_a_id and TeamMembership.objects.filter(
                team_id=match.team_a_id, profile=profile, status="ACTIVE"
            ).exists():
                team = match.team_a
            elif match.team_b_id and TeamMembership.objects.filter(
                team_id=match.team_b_id, profile=profile, status="ACTIVE"
            ).exists():
                team = match.team_b

            if team is None:
                messages.error(request, "You’re not on this match roster.")
                return _redirect_back(request)

            member_profiles = TeamMembership.objects.filter(
                team=team, status="ACTIVE"
            ).select_related("profile__user")

            recipients_users = [
                m.profile.user for m in member_profiles
                if getattr(getattr(m.profile, "user", None), "email", "")
            ]
        else:
            # Solo match — remind self if participant
            p = profile
            if match.user_a_id == getattr(p, "id", None) or match.user_b_id == getattr(p, "id", None):
                recipients_users = [request.user]
            else:
                messages.error(request, "You’re not a participant in this match.")
                return _redirect_back(request)
    except Exception:
        recipients_users = [request.user]  # safe fallback

    emailed = 0
    if notify_emit and recipients_users:
        start_local = localtime(match.start_at) if match.start_at else None
        tz = get_current_timezone()
        tname = getattr(match.tournament, "name", "Tournament")
        subject = f"[DeltaCrown] Match reminder — {tname}"
        url = request.build_absolute_uri(reverse("tournaments:match_review", args=[match.id]))
        body = (
            f"Your match in {tname} is coming up."
            + (f" Scheduled start: {start_local.strftime('%Y-%m-%d %H:%M %Z')}" if start_local else "")
        )

        result = notify_emit(
            recipients_users,
            event="match_reminder",
            title="Match reminder",
            body=body,
            url=url,
            tournament=getattr(match, "tournament", None),
            match=match,
            dedupe=True,
            email_subject=subject,
            email_template="match_reminder",
            email_ctx={
                "tournament_name": tname,
                "match": match,
                "start_at": start_local,
                "timezone": tz,
                "cta_url": url,
            },
        )
        emailed = getattr(result, "email_sent", 0)

    cache.set(rl_key, True, timeout=10 * 60)
    messages.success(request, "Reminder sent to your team." if emailed else "Reminder scheduled.")
    return _redirect_back(request)
