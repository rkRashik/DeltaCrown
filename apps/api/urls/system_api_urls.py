"""
System-level API endpoints.

Includes hub widget feeds and cross-app utilities.
"""

from django.urls import path
from apps.organizations.api import hub_endpoints

app_name = 'system_api'

urlpatterns = [
    # Hub live widgets
    path('ticker/', hub_endpoints.ticker_feed, name='ticker_feed'),
    path('players/lft/', hub_endpoints.scout_radar, name='scout_radar'),
    path('scrims/active/', hub_endpoints.active_scrims, name='active_scrims'),
    path('teams/search/', hub_endpoints.team_search, name='team_search'),
]
