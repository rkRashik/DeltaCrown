"""
Match Operations API URLs - Phase 7, Epic 7.4

URL routing for Match Operations Command Center (MOCC) endpoints.

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from django.urls import path
from apps.api.views import organizer_match_ops_views as views

app_name = 'match_ops'

urlpatterns = [
    # Live Match Control
    path(
        'mark-live/',
        views.mark_match_live,
        name='mark_match_live'
    ),
    path(
        'pause/',
        views.pause_match,
        name='pause_match'
    ),
    path(
        'resume/',
        views.resume_match,
        name='resume_match'
    ),
    
    # Admin Operations
    path(
        'force-complete/',
        views.force_complete_match,
        name='force_complete_match'
    ),
    path(
        'override-result/',
        views.override_match_result,
        name='override_match_result'
    ),
    
    # Communication
    path(
        'add-note/',
        views.add_match_note,
        name='add_match_note'
    ),
    
    # Match Timeline & Dashboard
    path(
        'timeline/<int:match_id>/',
        views.get_match_timeline,
        name='get_match_timeline'
    ),
    path(
        'dashboard/<int:tournament_id>/',
        views.view_operations_dashboard,
        name='view_operations_dashboard'
    ),
]
