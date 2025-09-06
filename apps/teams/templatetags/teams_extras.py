from django import template

register = template.Library()


@register.filter
def exclude_captain(memberships, team):
    """
    Return the memberships iterable minus the captain's membership.

    - Works with a QuerySet or any iterable of membership-like objects.
    - Captain can be a user-like object or an object with `.user`.
    - Membership item may expose `.user`, `.player`, or `.profile.user`.
    """
    cap = getattr(team, "captain", None)
    cap_user = getattr(cap, "user", cap)
    cap_id = getattr(cap_user, "id", None)

    def member_user(obj):
        return (
            getattr(obj, "user", None)
            or getattr(obj, "player", None)
            or getattr(getattr(obj, "profile", None), "user", None)
        )

    try:
        result = []
        for m in memberships:
            u = member_user(m)
            if cap_id is not None and getattr(u, "id", None) == cap_id:
                continue
            result.append(m)
        return result
    except Exception:
        try:
            return list(memberships)
        except Exception:
            return []


@register.simple_tag
def get_active_team(profile, game):
    """Template helper: returns the ACTIVE team for a profile+game, or None."""
    try:
        from apps.teams.utils import get_active_team as _gat
        return _gat(profile, game)
    except Exception:
        return None
