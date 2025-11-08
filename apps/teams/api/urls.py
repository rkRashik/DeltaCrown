# apps/teams/api/urls.py
"""
Team API URL Configuration (Module 3.3)

REST API routing for team management endpoints.

Traceability:
- Documents/ExecutionPlan/MODULE_3.3_IMPLEMENTATION_PLAN.md#proposed-endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TeamViewSet, TeamInviteViewSet

# Create router
router = DefaultRouter()
router.register(r'', TeamViewSet, basename='team')
router.register(r'invites', TeamInviteViewSet, basename='team-invite')

app_name = 'teams_api'

urlpatterns = [
    path('', include(router.urls)),
]
