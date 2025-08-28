# apps/teams/urls.py
from django.urls import path
from . import views

app_name = "teams"

urlpatterns = [
    path("<int:team_id>/", views.team_detail, name="team_detail"),
    path("<int:team_id>/invite/", views.invite_member_view, name="invite_member"),
    path("<int:team_id>/transfer/<int:user_id>/", views.transfer_captain_view, name="transfer_captain"),
    path("<int:team_id>/leave/", views.leave_team_view, name="leave_team"),

    path("invites/", views.my_invites, name="my_invites"),
    path("invites/<str:token>/accept/", views.accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", views.decline_invite_view, name="decline_invite"),
]
