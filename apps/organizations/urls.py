"""
URL Configuration for organizations app.

Includes both UI views and API endpoints.
"""

from django.urls import path, include
from django.views.generic import RedirectView
from . import views

app_name = 'organizations'

urlpatterns = [
    # API endpoints
    path('api/vnext/', include('apps.organizations.api.urls')),
    
    # UI views - vNext Hub (landing page)
    path('teams/vnext/', views.vnext_hub, name='vnext_hub'),
    
    # UI views - Team creation
    path('teams/create/', views.team_create, name='team_create'),
    
    # UI views - Team detail (P3-T6)
    path('teams/<str:team_slug>/', views.team_detail, name='team_detail'),
]
