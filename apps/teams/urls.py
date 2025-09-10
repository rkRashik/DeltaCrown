# apps/teams/urls.py
from django.urls import path
from .views.public import (
    team_list,
    team_detail,
    create_team_view,
    invite_member_view,
    my_invites,
    accept_invite_view,
    decline_invite_view,
    leave_team_view,
    manage_team_view,
)

app_name = "teams"

urlpatterns = [
    # Public index
    path("", team_list, name="index"),
    path("create/", create_team_view, name="create"),

    # Detail + captain actions (slug-based)
    path("<slug:slug>/", team_detail, name="detail"),
    path("<slug:slug>/manage/", manage_team_view, name="manage"),
    path("<slug:slug>/invite/", invite_member_view, name="invite_member"),
    path("<slug:slug>/leave/", leave_team_view, name="leave_team"),

    # Invites
    path("invites/", my_invites, name="my_invites"),
    path("invites/<str:token>/accept/", accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", decline_invite_view, name="decline_invite"),
]
