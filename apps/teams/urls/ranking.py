# apps/teams/urls/ranking.py
"""
URL patterns for Team Ranking System API
"""
from django.urls import path
from ..views.ranking_api import (
    TeamRankingAPIView,
    TeamRankingManagementAPIView, 
    TeamRankingStatsAPIView
)

app_name = 'teams_ranking'

urlpatterns = [
    # Public API endpoints
    path('api/rankings/', TeamRankingAPIView.as_view(), name='rankings_list'),
    path('api/rankings/<int:team_id>/', TeamRankingAPIView.as_view(), name='team_ranking_detail'),
    path('api/rankings/stats/', TeamRankingStatsAPIView.as_view(), name='ranking_stats'),
    
    # Admin API endpoints (require staff permissions)
    path('api/admin/team/<int:team_id>/<str:action>/', 
         TeamRankingManagementAPIView.as_view(), 
         name='admin_team_ranking_action'),
]