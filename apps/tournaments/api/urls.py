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
]
