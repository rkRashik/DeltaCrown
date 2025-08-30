from django.apps import apps


def _get_profile(user):
    return getattr(user, "profile", None) or getattr(user, "userprofile", None)


def _get_unread_count(profile) -> int:
    if not profile:
        return 0
    Notification = apps.get_model("notifications", "Notification")
    return Notification.objects.filter(recipient=profile, is_read=False).count()


def notification_counts(request):
    """
    Preferred context processor.
    Provides both `notif_unread` (new) and `unread_notifications_count` (legacy) keys.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"notif_unread": 0, "unread_notifications_count": 0}

    profile = _get_profile(request.user)
    count = _get_unread_count(profile)
    return {"notif_unread": count, "unread_notifications_count": count}


# ---- Backwards-compat shim ----
def unread_notifications(request):
    """
    Kept for compatibility with existing settings.py entries:
    'apps.notifications.context_processors.unread_notifications'
    """
    return notification_counts(request)
