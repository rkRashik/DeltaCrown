"""
API URL Configuration for Tournament Models

This module provides URL routing for all tournament API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import (
    TournamentViewSet,
    TournamentScheduleViewSet,
    TournamentCapacityViewSet,
    TournamentFinanceViewSet,
    TournamentMediaViewSet,
    TournamentRulesViewSet,
    TournamentArchiveViewSet,
)


# Create router and register viewsets
router = DefaultRouter()

# Register all viewsets
router.register(r'tournaments', TournamentViewSet, basename='tournament')
router.register(r'schedules', TournamentScheduleViewSet, basename='schedule')
router.register(r'capacity', TournamentCapacityViewSet, basename='capacity')
router.register(r'finance', TournamentFinanceViewSet, basename='finance')
router.register(r'media', TournamentMediaViewSet, basename='media')
router.register(r'rules', TournamentRulesViewSet, basename='rules')
router.register(r'archive', TournamentArchiveViewSet, basename='archive')


# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]


# API Endpoints Documentation
"""
Available API Endpoints:

TOURNAMENTS:
  GET    /api/tournaments/                    - List all tournaments
  POST   /api/tournaments/                    - Create tournament
  GET    /api/tournaments/{id}/               - Tournament detail
  PUT    /api/tournaments/{id}/               - Update tournament
  PATCH  /api/tournaments/{id}/               - Partial update
  DELETE /api/tournaments/{id}/               - Delete tournament
  GET    /api/tournaments/published/          - Published tournaments
  GET    /api/tournaments/upcoming/           - Upcoming tournaments
  GET    /api/tournaments/in_progress/        - Tournaments in progress
  GET    /api/tournaments/completed/          - Completed tournaments
  GET    /api/tournaments/registration_open/  - Registration open
  GET    /api/tournaments/{id}/full_details/  - Full details with all data

SCHEDULES:
  GET    /api/schedules/                      - List all schedules
  POST   /api/schedules/                      - Create schedule
  GET    /api/schedules/{id}/                 - Schedule detail
  PUT    /api/schedules/{id}/                 - Update schedule
  PATCH  /api/schedules/{id}/                 - Partial update
  DELETE /api/schedules/{id}/                 - Delete schedule
  GET    /api/schedules/registration_open/    - Open registrations
  GET    /api/schedules/upcoming/             - Upcoming tournaments
  GET    /api/schedules/in_progress/          - In progress
  GET    /api/schedules/{id}/status/          - Detailed status

CAPACITY:
  GET    /api/capacity/                       - List all capacity records
  POST   /api/capacity/                       - Create capacity record
  GET    /api/capacity/{id}/                  - Capacity detail
  PUT    /api/capacity/{id}/                  - Update capacity
  PATCH  /api/capacity/{id}/                  - Partial update
  DELETE /api/capacity/{id}/                  - Delete capacity
  GET    /api/capacity/available/             - Available capacity
  GET    /api/capacity/full/                  - Full tournaments
  POST   /api/capacity/{id}/increment/        - Increment team count
  POST   /api/capacity/{id}/decrement/        - Decrement team count

FINANCE:
  GET    /api/finance/                        - List all finance records
  POST   /api/finance/                        - Create finance record
  GET    /api/finance/{id}/                   - Finance detail
  PUT    /api/finance/{id}/                   - Update finance
  PATCH  /api/finance/{id}/                   - Partial update
  DELETE /api/finance/{id}/                   - Delete finance
  GET    /api/finance/free/                   - Free tournaments
  GET    /api/finance/paid/                   - Paid tournaments
  POST   /api/finance/{id}/record_payment/    - Record payment
  POST   /api/finance/{id}/record_payout/     - Record payout
  GET    /api/finance/{id}/summary/           - Financial summary

MEDIA:
  GET    /api/media/                          - List all media records
  POST   /api/media/                          - Create media record
  GET    /api/media/{id}/                     - Media detail
  PUT    /api/media/{id}/                     - Update media
  PATCH  /api/media/{id}/                     - Partial update
  DELETE /api/media/{id}/                     - Delete media
  GET    /api/media/with_logos/               - Media with logos
  GET    /api/media/with_banners/             - Media with banners
  GET    /api/media/with_streams/             - Media with streams

RULES:
  GET    /api/rules/                          - List all rules
  POST   /api/rules/                          - Create rules
  GET    /api/rules/{id}/                     - Rules detail
  PUT    /api/rules/{id}/                     - Update rules
  PATCH  /api/rules/{id}/                     - Partial update
  DELETE /api/rules/{id}/                     - Delete rules
  GET    /api/rules/with_age_restriction/     - Age restricted
  GET    /api/rules/with_region_restriction/  - Region restricted
  GET    /api/rules/{id}/check_eligibility/   - Check eligibility

ARCHIVE:
  GET    /api/archive/                        - List all archives
  POST   /api/archive/                        - Create archive
  GET    /api/archive/{id}/                   - Archive detail
  PUT    /api/archive/{id}/                   - Update archive
  PATCH  /api/archive/{id}/                   - Partial update
  DELETE /api/archive/{id}/                   - Delete archive
  GET    /api/archive/archived/               - Archived tournaments
  GET    /api/archive/active/                 - Active tournaments
  GET    /api/archive/clones/                 - Cloned tournaments
  POST   /api/archive/{id}/archive_tournament/  - Archive tournament
  POST   /api/archive/{id}/restore_tournament/  - Restore tournament

FILTERS:
  All list endpoints support filtering via query parameters:
  - ?tournament=<id>       Filter by tournament
  - ?status=<status>       Filter by status
  - ?search=<query>        Full-text search
  - ?ordering=<field>      Sort results
  
PAGINATION:
  All list endpoints support pagination:
  - ?page=<number>         Page number
  - ?page_size=<number>    Items per page
"""
