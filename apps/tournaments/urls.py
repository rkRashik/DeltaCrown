from django.urls import path

from .views.public import hub, list_by_game, detail
from .views.registration import register

# Optional "My Matches" — include if you have the view; else safely skip.
try:
    from .views.my_matches import my_matches  # pragma: no cover
    HAS_MY_MATCHES = True
except Exception:  # pragma: no cover
    HAS_MY_MATCHES = False
    my_matches = None  # type: ignore

app_name = "tournaments"

urlpatterns = [
    # Hub / landing
    path("", hub, name="hub"),

    # Browse by game
    # e.g. /tournaments/game/valorant/
    path("game/<slug:game>/", list_by_game, name="game"),

    # Detail
    # e.g. /tournaments/t/valorant-delta-masters/
    path("t/<slug:slug>/", detail, name="detail"),

    # Register
    # e.g. /tournaments/register/valorant-delta-masters/
    path("register/<slug:slug>/", register, name="register"),
]

# Optional: My Matches (dashboard-like surface under tournaments)
if HAS_MY_MATCHES:
    urlpatterns += [
        # e.g. /tournaments/my/matches/
        path("my/matches/", my_matches, name="my_matches"),
    ]
