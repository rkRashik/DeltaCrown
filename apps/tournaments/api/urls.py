# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-routing

"""
Tournament API - URL Configuration

REST API routes for tournament registration and management.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Routing)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (URL Conventions)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tournaments.api import views
from apps.tournaments.api.tournament_views import TournamentViewSet  # Module 2.1
from apps.tournaments.api.game_config_views import GameConfigViewSet  # Module 2.2
from apps.tournaments.api.custom_field_views import CustomFieldViewSet  # Module 2.2
from apps.tournaments.api.template_views import TournamentTemplateViewSet  # Module 2.3
from apps.tournaments.api.discovery_views import TournamentDiscoveryViewSet  # Module 2.4
from apps.tournaments.api.registrations import RegistrationViewSet  # Milestone B
from apps.tournaments.api.payments import PaymentVerificationViewSet  # Milestone C
from apps.tournaments.api.matches import MatchViewSet  # Milestone D (replaces match_views)
from apps.tournaments.api.bracket_views import BracketViewSet
from apps.tournaments.api.result_views import ResultViewSet  # Module 4.4
from apps.tournaments.api.leaderboard_views import LeaderboardViewSet  # Milestone E
from apps.tournaments.api import payout_views  # Module 5.2
from apps.tournaments.api import certificate_views  # Module 5.3
from apps.tournaments.api import analytics_views  # Module 5.4
from apps.tournaments.api import organizer_views  # Module 2.5

# Phase E: Read-only leaderboard endpoints
from apps.tournaments.api.leaderboard_views import (
    tournament_leaderboard,
    player_leaderboard_history,
    scoped_leaderboard,
)

# Router for DRF viewsets
router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='tournament')  # Module 2.1
router.register(r'tournament-discovery', TournamentDiscoveryViewSet, basename='tournament-discovery')  # Module 2.4
router.register(r'games', GameConfigViewSet, basename='game-config')  # Module 2.2
router.register(r'tournament-templates', TournamentTemplateViewSet, basename='tournament-template')  # Module 2.3
router.register(r'registrations', RegistrationViewSet, basename='registration')  # Use Milestone B version
router.register(r'payments', PaymentVerificationViewSet, basename='payment')  # Milestone C
router.register(r'brackets', BracketViewSet, basename='bracket')
router.register(r'matches', MatchViewSet, basename='match')  # Module 4.3
router.register(r'results', ResultViewSet, basename='result')  # Module 4.4
router.register(r'leaderboards', LeaderboardViewSet, basename='leaderboard')  # Milestone E

# Module 2.2: Nested router for custom fields under tournaments
# TODO: Install drf-nested-routers package to enable nested custom fields endpoint
# from rest_framework_nested import routers as nested_routers
# tournaments_router = nested_routers.NestedDefaultRouter(router, r'tournaments', lookup='tournament')
# tournaments_router.register(r'custom-fields', CustomFieldViewSet, basename='tournament-custom-fields')

app_name = 'tournaments_api'

urlpatterns = [
    path('', include(router.urls)),
    # path('', include(tournaments_router.urls)),  # Module 2.2: Custom fields (requires drf-nested-routers)
    path('checkin/', include('apps.tournaments.api.checkin.urls', namespace='checkin')),
    
    # Phase E: Read-Only Leaderboard Endpoints (PII-Free)
    path('leaderboards/tournament/<int:tournament_id>/', tournament_leaderboard, name='tournament-leaderboard'),
    path('leaderboards/player/<int:player_id>/history/', player_leaderboard_history, name='player-history'),
    path('leaderboards/<str:scope>/', scoped_leaderboard, name='scoped-leaderboard'),
    
    # Module 5.2: Prize Payouts & Refunds
    path('<int:tournament_id>/payouts/', payout_views.process_payouts, name='process-payouts'),
    path('<int:tournament_id>/refunds/', payout_views.process_refunds, name='process-refunds'),
    path('<int:tournament_id>/payouts/verify/', payout_views.verify_reconciliation, name='verify-reconciliation'),
    
    # Module 5.3: Certificates & Achievement Proofs
    path('certificates/<int:pk>/', certificate_views.download_certificate, name='download-certificate'),
    path('certificates/verify/<uuid:code>/', certificate_views.verify_certificate, name='verify-certificate'),
    
    # Module 5.4: Analytics & Reports
    path('analytics/organizer/<int:tournament_id>/', analytics_views.organizer_analytics, name='analytics-organizer'),
    path('analytics/participant/<int:user_id>/', analytics_views.participant_analytics, name='analytics-participant'),
    path('analytics/export/<int:tournament_id>/', analytics_views.export_tournament_csv, name='analytics-export-csv'),
    
    # Module 2.5: Organizer Dashboard (Backend Only)
    path('organizer/dashboard/stats/', organizer_views.organizer_stats, name='organizer-dashboard-stats'),
    path('organizer/tournaments/<int:tournament_id>/health/', organizer_views.tournament_health, name='organizer-tournament-health'),
    path('organizer/tournaments/<int:tournament_id>/participants/', organizer_views.participant_breakdown, name='organizer-tournament-participants'),
]
