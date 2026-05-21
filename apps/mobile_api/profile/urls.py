"""URL patterns for mobile profile and game passport endpoints."""
from django.urls import path

from .views import (
    MobileGamePassportDetailView,
    MobileGamePassportListCreateView,
    MobileGamesView,
    MobileProfileView,
)


urlpatterns = [
    path("me/profile/", MobileProfileView.as_view(), name="profile"),
    path("games/", MobileGamesView.as_view(), name="games"),
    path("me/game-passports/", MobileGamePassportListCreateView.as_view(), name="game_passports"),
    path(
        "me/game-passports/<int:passport_id>/",
        MobileGamePassportDetailView.as_view(),
        name="game_passport_detail",
    ),
]
