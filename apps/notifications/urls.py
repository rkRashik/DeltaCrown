from django.urls import path
from . import views
from .sse import notification_stream

app_name = "notifications"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("<int:pk>/mark-read/", views.mark_read, name="mark_read"),
    path("<int:pk>/delete/", views.delete_notification, name="delete"),
    path("clear-all/", views.clear_all_notifications, name="clear_all"),
    path("unread_count/", views.unread_count, name="unread_count"),
    # API endpoints
    path("api/unread-count/", views.unread_count, name="api_unread_count"),  # Real-time polling
    path("api/nav-preview/", views.nav_preview, name="nav_preview"),
    # Follow request inline actions
    path("api/follow-request/<int:request_id>/accept/", views.accept_follow_request_inline, name="accept_follow_request_inline"),
    path("api/follow-request/<int:request_id>/reject/", views.reject_follow_request_inline, name="reject_follow_request_inline"),
    # Team invite inline actions (from bell dropdown / dashboard)
    path("api/team-invite/<int:invite_id>/accept/", views.accept_team_invite_inline, name="accept_team_invite_inline"),
    path("api/team-invite/<int:invite_id>/decline/", views.decline_team_invite_inline, name="decline_team_invite_inline"),
    # SSE endpoint for live updates
    path("stream/", notification_stream, name="stream"),
]
