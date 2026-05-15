"""Dropzone API URL configuration."""
from django.urls import path

from .views import (
    MyRoyaleEntriesView,
    RoyaleCancelReservationView,
    RoyaleLobbyDetailView,
    RoyaleLobbyListView,
    RoyaleReserveView,
)


app_name = 'royale_api'

urlpatterns = [
    path(
        'lobbies/',
        RoyaleLobbyListView.as_view(),
        name='lobby-list',
    ),
    path(
        'lobbies/<uuid:lobby_id>/',
        RoyaleLobbyDetailView.as_view(),
        name='lobby-detail',
    ),
    path(
        'lobbies/<uuid:lobby_id>/reserve/',
        RoyaleReserveView.as_view(),
        name='lobby-reserve',
    ),
    path(
        'entries/<uuid:entry_id>/cancel/',
        RoyaleCancelReservationView.as_view(),
        name='entry-cancel',
    ),
    path(
        'my/',
        MyRoyaleEntriesView.as_view(),
        name='my-entries',
    ),
]
