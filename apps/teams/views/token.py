# apps/teams/views/token.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.apps import apps
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse


def _profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


def _team_detail_url(team_id: int) -> str:
    # Prefer named route; fall back to generic teams index if not wired
    try:
        return reverse("teams:team_detail", kwargs={"team_id": team_id})
    except Exception:
        return "/teams/"


@login_required
def accept_invite_view(request: HttpRequest, token: str) -> HttpResponse:
    """
    Accept a team invite by token with expiry checks and friendly errors.
    Idempotent: re-accepting does not duplicate membership.
    """
    TeamInvite = apps.get_model("teams", "TeamInvite")
    TeamMembership = apps.get_model("teams", "TeamMembership")

    invite = (
        TeamInvite.objects.select_related("team", "invited_user")
        .filter(token=token)
        .first()
    )
    if not invite:
        # Friendly invalid page
        return render(request, "teams/invite_invalid.html", status=404)

    me = _profile(request.user)
    if not me or (invite.invited_user_id and invite.invited_user_id != me.id):
        # Token not for this user
        return render(request, "teams/invite_invalid.html", status=403)

    # Expiry check (and sync status if needed)
    try:
        if hasattr(invite, "mark_expired_if_needed"):
            invite.mark_expired_if_needed()
    except Exception:
        # safe fallback
        if getattr(invite, "expires_at", None) and timezone.now() > invite.expires_at:
            invite.status = "EXPIRED"
            invite.save(update_fields=["status"])

    if invite.status == "EXPIRED":
        return render(request, "teams/invite_expired.html", {"invite": invite}, status=410)

    if invite.status != "PENDING":
        # Already accepted/declined/cancelled → treat as invalid for UX
        return render(request, "teams/invite_invalid.html", status=400)

    # Idempotent join
    # Field is `profile` in TeamMembership
    mem_kwargs = {"team": invite.team, "profile": me}
    TeamMembership.objects.get_or_create(
        **mem_kwargs,
        defaults={"role": "CAPTAIN" if invite.role == "CAPTAIN" else "PLAYER", "status": "ACTIVE"},
    )

    # Mark invite accepted (and bind invited_user if missing)
    updates = {"status": "ACCEPTED"}
    if getattr(invite, "invited_user_id", None) is None:
        updates["invited_user"] = me
    TeamInvite.objects.filter(pk=invite.pk).update(**updates)

    # Redirect to team page
    return HttpResponseRedirect(_team_detail_url(invite.team_id))
