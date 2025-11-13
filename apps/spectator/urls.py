"""
Spectator URL Configuration

Phase G: Spectator Live Views

Read-only routes for tournament spectators.
"""

from django.urls import path
from . import views

app_name = 'spectator'

urlpatterns = [
    # Tournament list (spectator entry point)
    path('', views.tournament_list_view, name='tournament_list'),
    
    # Tournament spectator page
    path(
        'tournaments/<int:tournament_id>/',
        views.tournament_spectator_view,
        name='tournament_detail'
    ),
    
    # Tournament leaderboard fragment (htmx partial refresh)
    path(
        'tournaments/<int:tournament_id>/leaderboard/fragment/',
        views.tournament_leaderboard_fragment,
        name='tournament_leaderboard_fragment'
    ),
    
    # Tournament matches fragment (htmx partial refresh)
    path(
        'tournaments/<int:tournament_id>/matches/fragment/',
        views.tournament_matches_fragment,
        name='tournament_matches_fragment'
    ),
    
    # Match spectator page
    path(
        'matches/<int:match_id>/',
        views.match_spectator_view,
        name='match_detail'
    ),
    
    # Match scoreboard fragment (htmx partial refresh)
    path(
        'matches/<int:match_id>/scoreboard/fragment/',
        views.match_scoreboard_fragment,
        name='match_scoreboard_fragment'
    ),
]
