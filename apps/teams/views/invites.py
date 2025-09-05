# apps/teams/views/invites.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.apps import apps


def _profile(user):
    return getattr(user, "userprofile", None) or getattr(user, "profile", None)


@login_required
def my_invites(request):
    TeamInvite = apps.get_model("teams", "TeamInvite")
    me = _profile(request.user)
    if not me:
        return render(request, "teams/invite_invalid.html", status=403)

    invites = (
        TeamInvite.objects.select_related("team", "inviter")
        .filter(invited_user=me)
        .order_by("-created_at")
    )
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
def decline_invite_view(request, token: str):
    TeamInvite = apps.get_model("teams", "TeamInvite")
    me = _profile(request.user)
    inv = TeamInvite.objects.filter(token=token).select_related("team", "invited_user").first()
    if not inv or not me or (inv.invited_user_id and inv.invited_user_id != me.id):
        return render(request, "teams/invite_invalid.html", status=404)

    if inv.status == "PENDING":
        inv.status = "DECLINED"
        if inv.invited_user_id is None:
            inv.invited_user = me  # bind who declined, if not bound yet
        inv.save(update_fields=["status", "invited_user"])
        messages.info(request, f"Invite to join {inv.team.name} declined.")

    return redirect("teams:my_invites")
