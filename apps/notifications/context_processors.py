from django.apps import apps

from deltacrown.middleware.bot_probe import is_bot_probe_path


def _get_unread_count_for_user(user) -> int:
    """
    Your Notification.recipient FK points to accounts.User (not UserProfile),
    so count by the authenticated request.user directly.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    Notification = apps.get_model("notifications", "Notification")
    return Notification.objects.filter(recipient=user, is_read=False).count()


def notification_counts(request):
    """
    Provides: notif_unread, unread_notifications_count
    """
    # Skip on admin pages — admin has its own notification system
    if request.path.startswith('/admin/'):
        return {'notif_unread': 0, 'unread_notifications_count': 0}

    # Skip bot probe paths to keep 404 handling cheap.
    if is_bot_probe_path(request.path):
        return {'notif_unread': 0, 'unread_notifications_count': 0}

    if hasattr(request, '_cached_notif_unread'):
        cached = int(request._cached_notif_unread)
        return {'notif_unread': cached, 'unread_notifications_count': cached}

    user = getattr(request, "user", None)
    count = _get_unread_count_for_user(user)
    request._cached_notif_unread = count
    return {"notif_unread": count, "unread_notifications_count": count}


# Back-compat shim (legacy setting name)
def unread_notifications(request):
    return notification_counts(request)

