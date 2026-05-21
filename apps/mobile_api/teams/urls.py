"""URL patterns for mobile team endpoints."""
from django.urls import path

from .views import (
    MobileTeamApplyView,
    MobileTeamCreateView,
    MobileTeamDetailView,
    MobileTeamListView,
    MobileTeamRequestAcceptView,
    MobileTeamRequestDeclineView,
    MobileTeamStatusView,
)


urlpatterns = [
    path("me/team-status/", MobileTeamStatusView.as_view(), name="team_status"),
    path("teams/", MobileTeamListView.as_view(), name="teams"),
    path("teams/create/", MobileTeamCreateView.as_view(), name="team_create"),
    path("teams/<str:id_or_slug>/", MobileTeamDetailView.as_view(), name="team_detail"),
    path("teams/<str:id_or_slug>/apply/", MobileTeamApplyView.as_view(), name="team_apply"),
    path(
        "teams/<str:id_or_slug>/requests/<int:request_id>/accept/",
        MobileTeamRequestAcceptView.as_view(),
        name="team_request_accept",
    ),
    path(
        "teams/<str:id_or_slug>/requests/<int:request_id>/decline/",
        MobileTeamRequestDeclineView.as_view(),
        name="team_request_decline",
    ),
]
