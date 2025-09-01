import importlib
from django.contrib import admin
from apps.teams.models import Team

def test_teams_admin_autodiscover_registers_team():
    importlib.import_module("apps.teams.admin")
    assert Team in admin.site._registry
