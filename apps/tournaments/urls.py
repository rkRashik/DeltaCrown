"""
Tournament URL configuration.

Note: Frontend views moved to legacy_backup/ (November 2, 2025)
This file maintains URL namespace for admin panel and future API endpoints.

Current active routes:
- Admin panel: /admin/tournaments/ (Django admin)
- API endpoints: /api/tournaments/ (Module 3.1)

Legacy frontend routes (disabled):
- /tournaments/hub/ - Tournament listing (moved to legacy)
- /tournaments/<slug>/ - Tournament detail (moved to legacy)
- /tournaments/<slug>/register/ - Registration form (moved to legacy)
"""

from django.urls import path
from django.views.generic import RedirectView

app_name = 'tournaments'

urlpatterns = [
    # Redirect legacy frontend URLs to home page with info message
    # Users should use admin panel or API for tournament management
    path('', RedirectView.as_view(url='/', permanent=False), name='hub'),
    path('<slug:slug>/', RedirectView.as_view(url='/', permanent=False), name='detail'),
    path('<slug:slug>/register/', RedirectView.as_view(url='/', permanent=False), name='register'),
    
    # Keep these URL names for reverse() calls even though they redirect
    # This prevents NoReverseMatch errors in templates and admin
    path('<slug:slug>/unified-register/', RedirectView.as_view(url='/', permanent=False), name='unified_register'),
    path('<slug:slug>/enhanced-register/', RedirectView.as_view(url='/', permanent=False), name='enhanced_register'),
    path('<slug:slug>/valorant-register/', RedirectView.as_view(url='/', permanent=False), name='valorant_register'),
    path('<slug:slug>/efootball-register/', RedirectView.as_view(url='/', permanent=False), name='efootball_register'),
    path('<slug:slug>/modern-register/', RedirectView.as_view(url='/', permanent=False), name='modern_register'),
    
    # API state endpoint (if needed by admin panel)
    path('api/<slug:slug>/state/', RedirectView.as_view(url='/api/tournaments/', permanent=False), name='state_api'),
    
    # Archive routes
    path('archives/', RedirectView.as_view(url='/', permanent=False), name='archive_list'),
    path('archives/<slug:slug>/', RedirectView.as_view(url='/', permanent=False), name='archive_detail'),
]

# Note: Actual tournament management is done through:
# 1. Django Admin: /admin/tournaments/
# 2. REST API: /api/tournaments/ (Module 3.1)
# 3. Future frontend will be rebuilt from scratch
