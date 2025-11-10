# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-routing

"""
Tournament API - URL Configuration

REST API routes for tournament registration and management.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Routing)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (URL Conventions)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tournaments.api import views
from apps.tournaments.api.bracket_views import BracketViewSet
from apps.tournaments.api.match_views import MatchViewSet
from apps.tournaments.api.result_views import ResultViewSet  # Module 4.4
from apps.tournaments.api import payout_views  # Module 5.2
from apps.tournaments.api import certificate_views  # Module 5.3

# Router for DRF viewsets
router = DefaultRouter()
router.register(r'registrations', views.RegistrationViewSet, basename='registration')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'brackets', BracketViewSet, basename='bracket')
router.register(r'matches', MatchViewSet, basename='match')  # Module 4.3
router.register(r'results', ResultViewSet, basename='result')  # Module 4.4

app_name = 'tournaments_api'

urlpatterns = [
    path('', include(router.urls)),
    path('checkin/', include('apps.tournaments.api.checkin.urls', namespace='checkin')),
    
    # Module 5.2: Prize Payouts & Refunds
    path('<int:tournament_id>/payouts/', payout_views.process_payouts, name='process-payouts'),
    path('<int:tournament_id>/refunds/', payout_views.process_refunds, name='process-refunds'),
    path('<int:tournament_id>/payouts/verify/', payout_views.verify_reconciliation, name='verify-reconciliation'),
    
    # Module 5.3: Certificates & Achievement Proofs
    path('certificates/<int:pk>/', certificate_views.download_certificate, name='download-certificate'),
    path('certificates/verify/<uuid:code>/', certificate_views.verify_certificate, name='verify-certificate'),
]
