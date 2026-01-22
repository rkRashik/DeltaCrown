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

    items = Notification.objects.filter(recipient=user).order_by("-created_at")[: int(limit)]
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    return {"items": items, "unread_count": unread_count}
