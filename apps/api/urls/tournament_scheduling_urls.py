"""
Tournament Organizer Scheduling API URLs - Phase 7, Epic 7.2

URL configuration for organizer manual scheduling workflows.

Endpoints:
    GET /api/tournaments/v1/organizer/scheduling/ - List matches for scheduling
    POST /api/tournaments/v1/organizer/scheduling/ - Manually assign match
    POST /api/tournaments/v1/organizer/scheduling/bulk-shift/ - Bulk shift matches
    GET /api/tournaments/v1/organizer/scheduling/slots/ - Generate time slots

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from django.urls import path
from apps.api.views.organizer_scheduling_views import (
    OrganizerSchedulingView,
    OrganizerBulkShiftView,
    OrganizerSchedulingSlotsView,
)

app_name = 'organizer_scheduling'

urlpatterns = [
    # Manual scheduling endpoints
    path(
        'organizer/scheduling/',
        OrganizerSchedulingView.as_view(),
        name='organizer_scheduling'
    ),
    path(
        'organizer/scheduling/bulk-shift/',
        OrganizerBulkShiftView.as_view(),
        name='organizer_bulk_shift'
    ),
    path(
        'organizer/scheduling/slots/',
        OrganizerSchedulingSlotsView.as_view(),
        name='organizer_scheduling_slots'
    ),
]
