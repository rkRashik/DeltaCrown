from django import template
from django.apps import apps

register = template.Library()

@register.inclusion_tag("notifications/_bell.html", takes_context=True)
def notifications_bell(context, limit=6):
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"items": [], "unread_count": 0}

    Notification = apps.get_model("notifications", "Notification")
    UserProfile = apps.get_model("user_profile", "UserProfile")

    p = getattr(user, "profile", None) or getattr(user, "userprofile", None)
    if not p:
        p = UserProfile.objects.create(user=user, display_name=getattr(user, "username", "Player"))

    items = Notification.objects.filter(recipient=p).order_by("-created_at")[: int(limit)]
    unread_count = Notification.objects.filter(recipient=p, is_read=False).count()
    return {"items": items, "unread_count": unread_count}
