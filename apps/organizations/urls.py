"""
URL Configuration for organizations app.

Includes both UI views and API endpoints.

NOTE: Uses modular views from apps.organizations.views/ package
(hub.py, team.py, org.py) not the old monolithic views.py file.
"""

from django.urls import path, include
from django.views.generic import RedirectView

# Import from modular views package
from apps.organizations.views import (
    vnext_hub,
    team_create,
    team_detail,
    team_manage,
    team_invites,
    organization_detail,
    org_create,
    org_control_plane,
    org_hub,
    org_directory,
)
from apps.organizations.views.hub import vnext_hub_filter

app_name = 'organizations'

urlpatterns = [
    # API endpoints are now registered at root level in deltacrown/urls.py
    # This comment left for reference - actual API routes moved to main urls.py
    
    # UI views - vNext Hub (landing page)
    path('teams/vnext/', vnext_hub, name='vnext_hub'),
    path('teams/vnext/filter/', vnext_hub_filter, name='vnext_hub_filter'),
    
    # UI views - Team invites dashboard
    path('teams/invites/', team_invites, name='team_invites'),
    
    # UI views - Team creation
    path('teams/create/', team_create, name='team_create'),
    
    # UI views - Team detail (P4-T1 - Public display)
    path('teams/<str:team_slug>/', team_detail, name='team_detail'),
    
    # UI views - Team management (P3-T6 - Roster operations, requires auth)
    path('teams/<str:team_slug>/manage/', team_manage, name='team_manage'),
    
    # UI views - Organization creation (P3-T7)
    # MUST come BEFORE <org_slug> catch-all to avoid capturing 'create' as slug
    path('orgs/create/', org_create, name='org_create'),
    
    # UI views - Organization Directory (global rankings)
    # MUST come BEFORE <org_slug> catch-all
    path('orgs/', org_directory, name='org_directory'),
    
    # UI views - Organization Hub (P3-T8)
    # MUST come BEFORE <org_slug> catch-all detail page
    path('orgs/<str:org_slug>/hub/', org_hub, name='org_hub'),
    
    # UI views - Organization Control Plane
    # MUST come BEFORE <org_slug> catch-all detail page
    path('orgs/<str:org_slug>/control-plane/', org_control_plane, name='org_control_plane'),
    
    # UI views - Organization-scoped team detail (CANONICAL)
    # MUST come BEFORE <org_slug> catch-all to avoid capturing team routes
    path('orgs/<str:org_slug>/teams/<str:team_slug>/', team_detail, name='org_team_detail'),
    path('orgs/<str:org_slug>/teams/<str:team_slug>/manage/', team_manage, name='org_team_manage'),
    
    # UI views - Organization detail (catch-all, must be LAST)
    path('orgs/<str:org_slug>/', organization_detail, name='organization_detail'),
]
