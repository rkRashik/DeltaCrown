"""
Competition App URLs

Phase 3A-C: Match reporting and verification URLs
Phase 3A-D: Ranking documentation URLs
Phase 3A-E: Leaderboards URLs
"""

from django.urls import path
from . import views
from . import leaderboards

app_name = 'competition'

urlpatterns = [
    # Match reporting
    path('matches/report/', views.match_report_form, name='match_report_form'),
    path('matches/<int:match_id>/', views.match_report_detail, name='match_report_detail'),
    path('matches/', views.match_report_list, name='match_report_list'),
    
    # Verification actions
    path('matches/<int:match_id>/confirm/', views.match_report_confirm, name='match_report_confirm'),
    path('matches/<int:match_id>/dispute/', views.match_report_dispute, name='match_report_dispute'),
    
    # Ranking documentation (Phase 3A-D)
    path('ranking/about/', views.ranking_about, name='ranking_about'),
    
    # Leaderboards (Phase 3A-E)
    path('leaderboards/', leaderboards.leaderboard_global, name='leaderboard_global'),
    path('leaderboards/<str:game_id>/', leaderboards.leaderboard_game, name='leaderboard_game'),
    
    # Rankings URL aliases (for navigation compatibility)
    path('rankings/', leaderboards.leaderboard_global, name='rankings_global'),
    path('rankings/<str:game_id>/', leaderboards.leaderboard_game, name='rankings_game'),
]
