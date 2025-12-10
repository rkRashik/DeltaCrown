"""
URL Configuration for Match History API

Phase 8, Epic 8.4: Match History Engine
URL patterns for match history REST endpoints.
"""

from django.urls import path
from apps.api.views.match_history_views import (
    UserMatchHistoryView,
    TeamMatchHistoryView,
    CurrentUserMatchHistoryView,
)

app_name = 'match_history'

urlpatterns = [
    # Current user match history
    path('me/', CurrentUserMatchHistoryView.as_view(), name='current-user-history'),
    
    # User match history
    path('users/<int:user_id>/', UserMatchHistoryView.as_view(), name='user-history'),
    
    # Team match history
    path('teams/<int:team_id>/', TeamMatchHistoryView.as_view(), name='team-history'),
]
