"""URL patterns for mobile tournament endpoints."""
from django.urls import path

from .views import (
    MobileMyTournamentsView,
    MobileTournamentDetailView,
    MobileTournamentJoinView,
    MobileTournamentListView,
)


urlpatterns = [
    path("tournaments/", MobileTournamentListView.as_view(), name="tournaments"),
    path("me/tournaments/", MobileMyTournamentsView.as_view(), name="my_tournaments"),
    path("tournaments/<str:id_or_slug>/", MobileTournamentDetailView.as_view(), name="tournament_detail"),
    path("tournaments/<str:id_or_slug>/join/", MobileTournamentJoinView.as_view(), name="tournament_join"),
]
