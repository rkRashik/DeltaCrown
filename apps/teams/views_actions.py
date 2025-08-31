from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.apps import apps
from django.db import transaction

def _profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)

def _notify(recipient_profile, title, url="/teams/"):
    """Best-effort notification (does nothing if your Notification API differs)."""
    try:
        Notification = apps.get_model("notifications", "Notification")
        Notification.notify_once(
            recipient=recipient_profile,
            type="team_update",
            title=title,
            url=url,
        )
    except Exception:
        pass


@login_required
@transaction.atomic
def leave_team_view(request, tag):
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")

    team = get_object_or_404(Team, tag=tag)
    me = _profile(request.user)
    if not me:
        messages.error(request, "Profile not found.")
        # CHANGED: go to tournaments list (we do NOT have teams:list)
        return redirect("tournaments:list")

    membership = TeamMembership.objects.filter(team=team, user=me).first()
    if not membership:
        messages.error(request, "You are not a member of this team.")
        # CHANGED: go to existing numeric-detail route
        return redirect("teams:team_detail", team_id=team.id)

    if request.method != "POST":
        other_members = TeamMembership.objects.filter(team=team).exclude(user=me).exists()
        will_delete = (membership.role == "captain" and not other_members)
        return render(request, "teams/confirm_leave.html", {"team": team, "will_delete": will_delete})

    if membership.role == "captain":
        others = TeamMembership.objects.filter(team=team).exclude(user=me)
        if others.exists():
            messages.error(request, "Transfer captaincy to another member before leaving.")
            # CHANGED
            return redirect("teams:team_detail", team_id=team.id)
        # captain & sole member → delete the team
        TeamMembership.objects.filter(team=team).delete()
        team.delete()
        messages.success(request, "Team deleted because you were the only member.")
        # CHANGED
        return redirect("tournaments:list")

    # regular member → simply remove membership
    membership.delete()
    messages.success(request, "You left the team.")
    # notify (best effort)
    if getattr(team, "captain_id", None):
        _notify(team.captain, f"{me.display_name} left team {team.tag}", url=f"/teams/{team.id}/")
    # CHANGED
    return redirect("teams:team_detail", team_id=team.id)


@login_required
@transaction.atomic
def transfer_captain_view(request, tag):
    Team = apps.get_model("teams", "Team")
    TeamMembership = apps.get_model("teams", "TeamMembership")

    team = get_object_or_404(Team, tag=tag)
    me = _profile(request.user)
    if not me:
        # CHANGED
        return redirect("tournaments:list")

    my_mem = TeamMembership.objects.filter(team=team, user=me).first()
    if not my_mem or my_mem.role != "captain":
        messages.error(request, "Only the current captain can transfer captaincy.")
        # CHANGED
        return redirect("teams:team_detail", team_id=team.id)

    if request.method == "POST":
        new_cap_id = request.POST.get("new_captain_id")
        if not new_cap_id:
            messages.error(request, "Select a member to transfer captaincy to.")
            # reload form
            options = TeamMembership.objects.filter(team=team).exclude(user=me).select_related("user__user")
            return render(request, "teams/transfer_captain.html", {"team": team, "options": options})

        new_mem = get_object_or_404(TeamMembership, id=new_cap_id, team=team)

        my_mem.role = "player"
        new_mem.role = "captain"
        my_mem.save(update_fields=["role"])
        new_mem.save(update_fields=["role"])

        if hasattr(team, "captain_id"):
            team.captain = new_mem.user
            team.save(update_fields=["captain"])

        messages.success(request, f"Captaincy transferred.")
        _notify(new_mem.user, f"You are now captain of {team.tag}", url=f"/teams/{team.id}/")
        # CHANGED
        return redirect("teams:team_detail", team_id=team.id)

    options = TeamMembership.objects.filter(team=team).exclude(user=me).select_related("user__user")
    return render(request, "teams/transfer_captain.html", {"team": team, "options": options})
