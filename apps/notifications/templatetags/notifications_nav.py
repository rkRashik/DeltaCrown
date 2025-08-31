from django import template
from django.apps import apps

register = template.Library()

def _get_profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)

@register.inclusion_tag("notifications/_bell.html", takes_context=True)
def notifications_bell(context, limit=6):
    """Renders a navbar bell with unread badge and a dropdown of recent notifications."""
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"items": [], "unread_count": 0}

    Notification = apps.get_model("notifications", "Notification")
    p = _get_profile(user)
    if p is None:
        return {"items": [], "unread_count": 0}

    # Grab latest N for the dropdown
    items = (
        Notification.objects.filter(recipient=p)
        .order_by("-created_at")[: int(limit)]
    )

    # Compute unread count across all
    unread_count = Notification.objects.filter(recipient=p, is_read=False).count()

    return {"items": items, "unread_count": unread_count}
