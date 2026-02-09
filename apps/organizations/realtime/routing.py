# apps/organizations/realtime/routing.py
"""
Team WebSocket URL Routing — migrated from apps.teams.realtime.routing
"""
from django.urls import re_path

from .consumers import TeamConsumer

websocket_urlpatterns = [
    re_path(r'ws/teams/(?P<team_id>\d+)/$', TeamConsumer.as_asgi()),
]
