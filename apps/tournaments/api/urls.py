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

# Router for DRF viewsets
router = DefaultRouter()
router.register(r'registrations', views.RegistrationViewSet, basename='registration')
router.register(r'payments', views.PaymentViewSet, basename='payment')

app_name = 'tournaments_api'

urlpatterns = [
    path('', include(router.urls)),
    path('checkin/', include('apps.tournaments.api.checkin.urls', namespace='checkin')),
]
