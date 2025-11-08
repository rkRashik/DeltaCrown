# apps/teams/realtime/routing.py
"""
Team WebSocket URL Routing (Module 3.3)

WebSocket URL patterns for team channels.

Traceability:
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md#team-channels
"""
from django.urls import re_path

from .consumers import TeamConsumer

websocket_urlpatterns = [
    re_path(r'ws/teams/(?P<team_id>\d+)/$', TeamConsumer.as_asgi()),
]
