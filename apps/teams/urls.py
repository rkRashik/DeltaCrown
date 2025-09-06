from django.urls import path
from . import views
from .views import manage as manage_views  # tag-based actions (leave/transfer)
from .views.public import team_list, leave_team_view as leave_team_by_id
from .views import token as token_views

app_name = "teams"

urlpatterns = [
    path("", team_list, name="index"),

    # Static first
    path("invites/", views.my_invites, name="my_invites"),
    path("invites/<str:token>/accept/", token_views.accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", views.decline_invite_view, name="decline_invite"),
    path("create-quick/", views.create_team_quick, name="create_quick"),

    # --- ID-based endpoints (must come BEFORE tag-based to satisfy tests) ---
    path("<int:team_id>/", views.team_detail, name="team_detail"),
    path("<int:team_id>/invite/", views.invite_member_view, name="invite_member"),
    path("<int:team_id>/transfer/<int:user_id>/", views.transfer_captain_view, name="transfer_captain"),
    # IMPORTANT: use the ID-based view from the public module so it accepts `team_id`
    path("<int:team_id>/leave/", leave_team_by_id, name="leave_team"),

    # --- Tag-based actions (keep for convenience, AFTER int routes) ---
    path("<str:tag>/leave/", manage_views.leave_team_view, name="leave"),
    path("<str:tag>/transfer/", manage_views.transfer_captain_view, name="transfer"),

    # My invites + token actions
    path("invites/", views.my_invites, name="my_invites"),
    path("invites/<str:token>/accept/", token_views.accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", views.decline_invite_view, name="decline_invite"),

    # Team detail / actions (ID-based)
    path("<int:team_id>/", views.team_detail, name="team_detail"),
    path("<int:team_id>/invite/", views.invite_member_view, name="invite_member"),
    path("<int:team_id>/transfer/<int:user_id>/", views.transfer_captain_view, name="transfer_captain"),
    path("<int:team_id>/leave/", leave_team_by_id, name="leave_team"),

    # Optional: tag-based convenience routes (after int routes)
    path("<str:tag>/leave/", manage_views.leave_team_view, name="leave"),
    path("<str:tag>/transfer/", manage_views.transfer_captain_view, name="transfer"),

]


from .views import presets as presets_views
urlpatterns += [
    path("presets/", presets_views.my_presets, name="my_presets"),
    path("presets/<str:kind>/<int:preset_id>/delete/", presets_views.delete_preset, name="delete_preset"),
]
