# apps/tournaments/urls.py
from django.urls import path

from .views.public import hub, list_by_game, detail
from .views.registration import register

app_name = "tournaments"

# Optional "My Matches" — safely import all extras if present.
try:  # pragma: no cover
    from .views.my_matches import (
        my_matches,
        save_default_filter,
        toggle_pin,
        my_matches_bulk,
        my_matches_csv,
        my_matches_ics_link,
        my_matches_ics_regen,
        my_matches_ics,
    )
    HAS_MY_MATCHES = True
except Exception:  # pragma: no cover
    HAS_MY_MATCHES = False

urlpatterns = [
    # Hub / landing
    path("", hub, name="hub"),

    # Browse by game (e.g. /tournaments/game/valorant/)
    path("game/<slug:game>/", list_by_game, name="game"),

    # Detail (e.g. /tournaments/t/valorant-delta-masters/)
    path("t/<slug:slug>/", detail, name="detail"),

    # Register (e.g. /tournaments/register/valorant-delta-masters/)
    path("register/<slug:slug>/", register, name="register"),
]

# Optional: My Matches surface and helpers
if HAS_MY_MATCHES:
    urlpatterns += [
        # Dashboard-like list
        path("my/matches/", my_matches, name="my_matches"),
        # Save default filter
        path("my/matches/save-default/", save_default_filter, name="my_matches_save_default"),
        # Pin/unpin tournaments
        path("my/matches/pin/<int:tournament_id>/", toggle_pin, name="my_matches_toggle_pin"),
        # Bulk attendance actions
        path("my/matches/bulk/", my_matches_bulk, name="my_matches_bulk"),
        # Export CSV
        path("my/matches.csv", my_matches_csv, name="my_matches_csv"),
        # ICS help + management
        path("my/matches/ics/", my_matches_ics_link, name="my_matches_ics_link"),
        path("my/matches/ics/regen/", my_matches_ics_regen, name="my_matches_ics_regen"),
        # ICS feed (tokenized)
        path("my/matches/ics/<str:token>.ics", my_matches_ics, name="my_matches_ics"),
    ]
