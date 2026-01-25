"""
API URLs for vNext Organization and Team creation + Management.

Endpoints:
    POST /api/vnext/organizations/create/ - Create organization
    POST /api/vnext/teams/create/ - Create team (independent or org-owned)
    
    # Organization Management (P3-T5)
    GET /api/vnext/orgs/<org_slug>/ - Get organization details
    POST /api/vnext/orgs/<org_slug>/members/add/ - Add member
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/role/ - Update member role
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/remove/ - Remove member
    POST /api/vnext/orgs/<org_slug>/settings/ - Update organization settings
    
    # Team Membership Management (P3-T6)
    GET /api/vnext/teams/<team_slug>/detail/ - Get team details with roster
    POST /api/vnext/teams/<team_slug>/members/add/ - Add team member
    POST /api/vnext/teams/<team_slug>/members/<member_id>/role/ - Update member role
    POST /api/vnext/teams/<team_slug>/members/<member_id>/remove/ - Remove team member
    POST /api/vnext/teams/<team_slug>/settings/ - Update team settings
    
    # Hub Live Widgets (Phase B)
    GET /api/system/ticker/ - Live ticker feed (matches, transfers, news)
    GET /api/players/lft/ - Scout radar (players looking for team)
    GET /api/scrims/active/ - Active scrim requests
    GET /api/teams/search/ - Team search autocomplete
"""

from django.urls import path
from apps.organizations.api import views, hub_endpoints

app_name = 'organizations_api'

urlpatterns = [
    # Organization creation
    path('organizations/create/', views.create_organization, name='create_organization'),
    
    # Team creation
    path('teams/create/', views.create_team, name='create_team'),
    
    # Organization management (P3-T5)
    path('orgs/<str:org_slug>/', views.get_organization_detail, name='org_detail'),
    path('orgs/<str:org_slug>/members/add/', views.add_organization_member, name='add_member'),
    path('orgs/<str:org_slug>/members/<int:member_id>/role/', views.update_member_role, name='update_role'),
    path('orgs/<str:org_slug>/members/<int:member_id>/remove/', views.remove_organization_member, name='remove_member'),
    path('orgs/<str:org_slug>/settings/', views.update_organization_settings, name='update_settings'),
    
    # Team membership management (P3-T6)
    path('teams/<str:team_slug>/detail/', views.get_team_detail, name='team_detail'),
    path('teams/<str:team_slug>/members/add/', views.add_team_member, name='team_add_member'),
    path('teams/<str:team_slug>/members/<int:member_id>/role/', views.update_member_role, name='team_update_role'),
    path('teams/<str:team_slug>/members/<int:member_id>/remove/', views.remove_team_member, name='team_remove_member'),
    path('teams/<str:team_slug>/settings/', views.update_team_settings, name='team_update_settings'),
    
    # Phase C: Hub live widget endpoints
    path('system/ticker/', hub_endpoints.ticker_feed, name='ticker_feed'),
    path('system/players/lft/', hub_endpoints.scout_radar, name='scout_radar'),
    path('system/scrims/active/', hub_endpoints.active_scrims, name='active_scrims'),
    path('system/teams/search/', hub_endpoints.team_search, name='team_search'),
]
