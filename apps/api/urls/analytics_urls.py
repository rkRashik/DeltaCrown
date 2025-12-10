"""
Analytics API URLs for Epic 8.5 - Advanced Analytics & Leaderboards.

URL routing for analytics endpoints.
"""

from django.urls import path
from apps.api.views.analytics_views import (
    UserAnalyticsView,
    TeamAnalyticsView,
    LeaderboardView,
    LeaderboardRefreshView,
    CurrentSeasonView,
    SeasonsListView,
)

app_name = 'analytics'

urlpatterns = [
    # User analytics
    path('stats/v2/users/<int:user_id>/analytics/', UserAnalyticsView.as_view(), name='user-analytics'),
    
    # Team analytics
    path('stats/v2/teams/<int:team_id>/analytics/', TeamAnalyticsView.as_view(), name='team-analytics'),
    
    # Leaderboards
    path('leaderboards/v2/<str:leaderboard_type>/', LeaderboardView.as_view(), name='leaderboard'),
    path('leaderboards/v2/refresh/', LeaderboardRefreshView.as_view(), name='leaderboard-refresh'),
    
    # Seasons
    path('seasons/current/', CurrentSeasonView.as_view(), name='current-season'),
    path('seasons/', SeasonsListView.as_view(), name='seasons-list'),
]
