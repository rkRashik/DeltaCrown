"""URL patterns for mobile notification endpoints."""
from django.urls import path

from .views import (
    MobileDeviceTokenView,
    MobileNotificationListView,
    MobileNotificationReadAllView,
    MobileNotificationReadView,
    MobileNotificationUnreadCountView,
)


urlpatterns = [
    path("notifications/", MobileNotificationListView.as_view(), name="notifications"),
    path("notifications/unread-count/", MobileNotificationUnreadCountView.as_view(), name="unread_count"),
    path("notifications/read-all/", MobileNotificationReadAllView.as_view(), name="read_all"),
    path("notifications/device-token/", MobileDeviceTokenView.as_view(), name="device_token"),
    path("notifications/<int:notification_id>/read/", MobileNotificationReadView.as_view(), name="mark_read"),
]
