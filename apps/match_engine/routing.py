"""
WebSocket URL routing for match-engine consumers.

Phase 6 extraction: match-specific WS routes now owned by match_engine app.
"""

from django.urls import path

from apps.match_engine.consumers import MatchConsumer

websocket_urlpatterns = [
    # Match room — real-time updates for specific match (Module 4.5)
    # URL: ws://domain/ws/match/<match_id>/?token=<jwt_access_token>
    path('ws/match/<int:match_id>/', MatchConsumer.as_asgi()),
]
