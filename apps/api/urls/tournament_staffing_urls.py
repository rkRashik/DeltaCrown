"""
Tournament Staffing API URLs - Phase 7, Epic 7.3

URL routing for staff and referee management endpoints.

Reference: Phase 7, Epic 7.3 - Staff & Referee Role System
"""

from django.urls import path
from apps.api.views import organizer_staffing_views as views

app_name = 'tournament_staffing'

urlpatterns = [
    # Staff Role Endpoints
    path(
        'roles/',
        views.get_staff_roles,
        name='get_staff_roles'
    ),
    
    # Tournament Staff Management Endpoints
    path(
        'tournaments/<int:tournament_id>/staff/',
        views.get_tournament_staff,
        name='get_tournament_staff'
    ),
    path(
        'tournaments/<int:tournament_id>/staff/assign/',
        views.assign_staff,
        name='assign_staff'
    ),
    path(
        'staff/assignments/<int:assignment_id>/',
        views.remove_staff,
        name='remove_staff'
    ),
    
    # Match Referee Management Endpoints
    path(
        'matches/<int:match_id>/referees/',
        views.get_match_referees,
        name='get_match_referees'
    ),
    path(
        'matches/<int:match_id>/referees/assign/',
        views.assign_referee,
        name='assign_referee'
    ),
    path(
        'referees/assignments/<int:assignment_id>/',
        views.unassign_referee,
        name='unassign_referee'
    ),
    
    # Staff Load Endpoints
    path(
        'tournaments/staff/load/',
        views.get_staff_load,
        name='get_staff_load'
    ),
]
