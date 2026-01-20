from django.urls import path
from . import views
from .sse import notification_stream

app_name = "notifications"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("<int:pk>/mark-read/", views.mark_read, name="mark_read"),
    path("unread_count/", views.unread_count, name="unread_count"),
    # SSE endpoint for live updates
    path("stream/", notification_stream, name="stream"),
]
