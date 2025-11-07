"""
WebSocket URL Routing Configuration

Defines URL patterns for WebSocket connections to tournament rooms.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates

Usage:
    # In asgi.py
    from apps.tournaments.realtime.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        "websocket": JWTAuthMiddleware(
            AllowedHostsOriginValidator(
                URLRouter(websocket_urlpatterns)
            )
        ),
    })
"""

from django.urls import path
from . import consumers

# WebSocket URL patterns
websocket_urlpatterns = [
    # Tournament room - real-time updates for specific tournament
    # URL: ws://domain/ws/tournament/<tournament_id>/?token=<jwt_access_token>
    path('ws/tournament/<int:tournament_id>/', consumers.TournamentConsumer.as_asgi()),
]
