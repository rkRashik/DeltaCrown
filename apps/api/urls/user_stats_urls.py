"""
URL Configuration for User Stats API

Phase 8, Epic 8.2: User Stats Service
URL patterns for user statistics REST endpoints.
"""

from django.urls import path
from apps.api.views.user_stats_views import (
    UserStatsDetailView,
    UserAllStatsView,
    CurrentUserStatsView,
    UserStatsSummaryView,
    GameLeaderboardView,
)

app_name = 'user_stats'

urlpatterns = [
    # Current user stats
    path('me/', CurrentUserStatsView.as_view(), name='current-user-stats'),
    
    # User-specific stats
    path('users/<int:user_id>/', UserStatsDetailView.as_view(), name='user-stats-detail'),
    path('users/<int:user_id>/all/', UserAllStatsView.as_view(), name='user-all-stats'),
    path('users/<int:user_id>/summary/', UserStatsSummaryView.as_view(), name='user-stats-summary'),
    
    # Game leaderboard
    path('games/<str:game_slug>/leaderboard/', GameLeaderboardView.as_view(), name='game-leaderboard'),
]
