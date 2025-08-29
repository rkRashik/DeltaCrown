def unread_notifications(request):
    try:
        if request.user.is_authenticated:
            p = getattr(request.user, "profile", None)
            if not p:
                return {"unread_notifications_count": 0}
            from .models import Notification
            count = Notification.objects.filter(recipient=p, is_read=False).count()
            return {"unread_notifications_count": count}
    except Exception:
        pass
    return {"unread_notifications_count": 0}
