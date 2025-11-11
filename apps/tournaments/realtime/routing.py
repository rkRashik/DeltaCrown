"""
WebSocket URL Routing Configuration

Defines URL patterns for WebSocket connections to tournament and match rooms.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates

Phase 4: Tournament Operations API
Module 4.5: WebSocket Enhancement (match-specific channels)

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
from .match_consumer import MatchConsumer

# WebSocket URL patterns
websocket_urlpatterns = [
    # Tournament room - real-time updates for specific tournament
    # URL: ws://domain/ws/tournament/<tournament_id>/?token=<jwt_access_token>
    path('ws/tournament/<int:tournament_id>/', consumers.TournamentConsumer.as_asgi()),
    
    # Match room - real-time updates for specific match (Module 4.5)
    # URL: ws://domain/ws/match/<match_id>/?token=<jwt_access_token>
    path('ws/match/<int:match_id>/', MatchConsumer.as_asgi()),
]
