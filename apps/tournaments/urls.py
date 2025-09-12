# apps/tournaments/urls.py
from django.urls import path
from .views import dashboard as dashboard_views
from .views import my_matches as my_matches_views
from .views import evidence as evidence_views
from .views import attendance as attendance_views
from .views import public as public
from .views import public as views
# from .views.public import (
#     hub,
#     by_game,
#     detail,
#     tournament_list,  # legacy
#     register_view,
#     register_success,
#     watch,
#     registration_receipt,
# )

app_name = "tournaments"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("<str:game>/", views.list_by_game, name="by_game"),
    path("view/<slug:slug>/", views.detail, name="detail"),

    # Existing registration-related routes in your project; ensure names/args:
    path("register/<slug:slug>/", views.detail, name="register"),  # point to your actual register view if different
    path("receipt/<slug:slug>/", views.detail, name="registration_receipt"),
    path("check-in/<slug:slug>/", views.detail, name="check_in"),
    path("ics/<slug:slug>/", views.detail, name="ics"),
    path("my-matches/", views.hub, name="my_matches"),

    # Brackets (public or staff)
    path("brackets/<slug:slug>/", dashboard_views.bracket_view, name="bracket_view"),
    path("<slug:slug>/standings/", dashboard_views.standings_view, name="standings"),

    # Dashboard: My Matches suite (routing invariants)
    path("my-matches/", my_matches_views.my_matches, name="my_matches"),
    path("my-matches/save-default/", my_matches_views.save_default_filter, name="my_matches_save_default"),
    path("my-matches/bulk/", my_matches_views.my_matches_bulk, name="my_matches_bulk"),

    # Export/Calendar
    path("my-matches/csv/", my_matches_views.my_matches_csv, name="my_matches_csv"),
    path("my-matches/ics-link/", my_matches_views.my_matches_ics_link, name="my_matches_ics_link"),
    path("my-matches/ics-regen/", my_matches_views.my_matches_ics_regen, name="my_matches_ics_regen"),
    path("my-matches/ics/<str:token>/", my_matches_views.my_matches_ics, name="my_matches_ics"),

    # Pins / Attendance / Quick actions
    path("my-matches/toggle-pin/<int:tournament_id>/", my_matches_views.toggle_pin, name="my_matches_toggle_pin"),
    path("match/<int:match_id>/attendance/<str:action>/", attendance_views.toggle_attendance, name="match_attendance_toggle"),
    path("match/<int:match_id>/quick/<str:action>/", attendance_views.quick_action, name="match_quick_action"),

    # Match review/report/dispute (if you use these)
    path("match/<int:match_id>/", dashboard_views.match_review_view, name="match_review"),
    path("match/<int:match_id>/report/", dashboard_views.report_match_view, name="match_report"),
    path("match/<int:match_id>/confirm/", dashboard_views.match_confirm_view, name="match_confirm"),
    path("match/<int:match_id>/dispute/", dashboard_views.match_dispute_view, name="match_dispute"),
    path("staff/match/<int:match_id>/resolve/", dashboard_views.match_dispute_resolve_view, name="match_dispute_resolve"),
    # Signed evidence downloads
    path("evidence/<int:evidence_id>/", evidence_views.evidence_download, name="evidence_download"),
]
