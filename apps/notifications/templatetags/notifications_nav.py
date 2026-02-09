from django import template
from django.apps import apps

register = template.Library()


def _logo_url(obj, field="logo"):
    """Safely get a logo URL from a model with an ImageField."""
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


@register.inclusion_tag("notifications/_bell.html", takes_context=True)
def notifications_bell(context, limit=6):
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"items": [], "unread_count": 0, "invite_details": {}}

    Notification = apps.get_model("notifications", "Notification")

    items = list(
        Notification.objects.filter(recipient=user).order_by("-created_at")[: int(limit)]
    )
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    # ── Enrich team invite notifications with team details ──
    invite_details = {}
    invite_ids = [
        n.action_object_id
        for n in items
        if n.type == "invite_sent"
        and getattr(n, "action_type", "") == "team_invite"
        and n.action_object_id
    ]
    if invite_ids:
        try:
            TeamInvite = apps.get_model("organizations", "TeamInvite")
            Game = apps.get_model("games", "Game")
            game_map = {}
            try:
                game_map = {g.id: g.name for g in Game.objects.all().only("id", "name")}
            except Exception:
                pass

            invites = (
                TeamInvite.objects
                .filter(id__in=invite_ids)
                .select_related("team", "inviter")
            )
            for inv in invites:
                invite_details[inv.id] = {
                    "team_name": inv.team.name,
                    "team_slug": inv.team.slug,
                    "team_logo": _logo_url(inv.team),
                    "team_tag": getattr(inv.team, "tag", "") or "",
                    "game_name": game_map.get(inv.team.game_id, ""),
                    "role": inv.role,
                    "inviter": inv.inviter.username if inv.inviter else "Unknown",
                    "status": inv.status,
                }
        except Exception:
            pass

    return {"items": items, "unread_count": unread_count, "invite_details": invite_details}
