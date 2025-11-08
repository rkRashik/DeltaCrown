"""
URL routing for Check-in API

Endpoints:
- POST /api/tournaments/checkin/<registration_id>/check-in/ - Check in
- POST /api/tournaments/checkin/<registration_id>/undo/ - Undo check-in
- POST /api/tournaments/checkin/bulk/ - Bulk check-in
- GET /api/tournaments/checkin/<registration_id>/status/ - Get status

Author: DeltaCrown Development Team
Date: November 8, 2025
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CheckinViewSet

# Create router
router = DefaultRouter()
router.register(r'', CheckinViewSet, basename='checkin')

app_name = 'checkin'

urlpatterns = [
    path('', include(router.urls)),
]
