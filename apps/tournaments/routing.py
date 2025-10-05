"""
WebSocket URL Routing
Maps WebSocket connections to consumers
"""
from django.urls import path
from apps.tournaments.consumers import TournamentChatConsumer, TournamentLiveUpdatesConsumer

websocket_urlpatterns = [
    path('ws/tournament/<slug:slug>/chat/', TournamentChatConsumer.as_asgi()),
    path('ws/tournament/<slug:slug>/updates/', TournamentLiveUpdatesConsumer.as_asgi()),
]
