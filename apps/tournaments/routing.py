"""
WebSocket routing for tournaments app
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/tournaments/match/(?P<match_id>\d+)/$', consumers.MatchConsumer.as_asgi()),
    re_path(r'ws/tournaments/(?P<tournament_slug>[\w-]+)/bracket/$', consumers.TournamentBracketConsumer.as_asgi()),
]
