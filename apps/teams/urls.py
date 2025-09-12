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
    join_team_view,
    kick_member_view,
)

app_name = "teams"

urlpatterns = [
    # Public index
    path("", team_list, name="index"),
    # Alias for templates expecting 'teams:list'
    path("", team_list, name="list"),
    path("create/", create_team_view, name="create"),

    # Detail + captain actions (slug-based)
    path("<slug:slug>/", team_detail, name="detail"),
    path("<slug:slug>/manage/", manage_team_view, name="manage"),
    # Aliases commonly referenced by templates
    path("<slug:slug>/manage/", manage_team_view, name="edit"),
    path("<slug:slug>/invite/", invite_member_view, name="invite_member"),
    path("<slug:slug>/invite/", invite_member_view, name="invite"),
    path("<slug:slug>/leave/", leave_team_view, name="leave"),
    path("<slug:slug>/join/", join_team_view, name="join"),
    path("<slug:slug>/kick/<int:profile_id>/", kick_member_view, name="kick"),

    # Invites
    path("invites/", my_invites, name="my_invites"),
    # Alias for 'invitations' link
    path("invitations/", my_invites, name="invitations"),
    path("invites/<str:token>/accept/", accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", decline_invite_view, name="decline_invite"),
]
