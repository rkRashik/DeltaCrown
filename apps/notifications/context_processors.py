from django.apps import apps


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
    user = getattr(request, "user", None)
    count = _get_unread_count_for_user(user)
    return {"notif_unread": count, "unread_notifications_count": count}


# Back-compat shim (legacy setting name)
def unread_notifications(request):
    return notification_counts(request)

