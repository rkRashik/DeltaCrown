"""
Audit Log API URLs - Phase 7, Epic 7.5

URL routing for Audit Log System endpoints.

Reference: Phase 7, Epic 7.5 - Audit Log System
"""

from django.urls import path
from apps.api.views import organizer_audit_log_views as views

app_name = 'audit_logs'

urlpatterns = [
    # List and Filter
    path(
        '',
        views.AuditLogListView.as_view(),
        name='list_audit_logs'
    ),
    
    # Context-Specific Trails
    path(
        'tournament/<int:tournament_id>/',
        views.TournamentAuditTrailView.as_view(),
        name='tournament_audit_trail'
    ),
    path(
        'match/<int:match_id>/',
        views.MatchAuditTrailView.as_view(),
        name='match_audit_trail'
    ),
    path(
        'user/<int:user_id>/',
        views.UserAuditTrailView.as_view(),
        name='user_audit_trail'
    ),
    
    # Export and Activity
    path(
        'export/',
        views.AuditLogExportView.as_view(),
        name='export_audit_logs'
    ),
    path(
        'activity/',
        views.RecentActivityView.as_view(),
        name='recent_activity'
    ),
]
