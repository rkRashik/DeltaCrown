"""
Team Stats API URL Configuration

Phase 8, Epic 8.3: Team Stats & Ranking System
URL routing for team stats and ranking endpoints.
"""

from django.urls import path
from apps.api.views.team_stats_views import (
    TeamStatsDetailView,
    TeamAllStatsView,
    TeamRankingView,
    GameTeamLeaderboardView,
    TeamStatsSummaryView,
    TeamStatsForGameView,
)

app_name = 'team_stats_api'

urlpatterns = [
    # Team-specific endpoints
    path(
        'teams/<int:team_id>/stats/<str:game_slug>/',
        TeamStatsDetailView.as_view(),
        name='team-stats-detail'
    ),
    path(
        'teams/<int:team_id>/stats/',
        TeamAllStatsView.as_view(),
        name='team-stats-all'
    ),
    path(
        'teams/<int:team_id>/ranking/<str:game_slug>/',
        TeamRankingView.as_view(),
        name='team-ranking'
    ),
    path(
        'teams/<int:team_id>/summary/',
        TeamStatsSummaryView.as_view(),
        name='team-summary'
    ),
    
    # Leaderboard endpoints
    path(
        'leaderboards/teams/<str:game_slug>/',
        GameTeamLeaderboardView.as_view(),
        name='game-team-leaderboard'
    ),
    
    # Game-specific endpoints
    path(
        'games/<str:game_slug>/teams/stats/',
        TeamStatsForGameView.as_view(),
        name='game-teams-stats'
    ),
]
