from django.urls import path
from . import views
from .views import manage as views_actions  # tag-based actions (leave/transfer)
from .views.public import team_list, leave_team_view as leave_team_by_id

app_name = "teams"

urlpatterns = [
    path("", team_list, name="index"),

    # Static first
    path("invites/", views.my_invites, name="my_invites"),
    path("invites/<str:token>/accept/", views.accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", views.decline_invite_view, name="decline_invite"),
    path("create-quick/", views.create_team_quick, name="create_quick"),

    # --- ID-based endpoints (must come BEFORE tag-based to satisfy tests) ---
    path("<int:team_id>/", views.team_detail, name="team_detail"),
    path("<int:team_id>/invite/", views.invite_member_view, name="invite_member"),
    path("<int:team_id>/transfer/<int:user_id>/", views.transfer_captain_view, name="transfer_captain"),
    # IMPORTANT: use the ID-based view from the public module so it accepts `team_id`
    path("<int:team_id>/leave/", leave_team_by_id, name="leave_team"),

    # --- Tag-based actions (keep for convenience, AFTER int routes) ---
    path("<str:tag>/leave/", views_actions.leave_team_view, name="leave"),
    path("<str:tag>/transfer/", views_actions.transfer_captain_view, name="transfer"),
]
