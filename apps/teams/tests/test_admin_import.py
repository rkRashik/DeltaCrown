import importlib
from django.contrib import admin
from apps.teams.models import Team  # adjust if your primary model has a different name

def test_admin_autodiscover_imports_teams_admin():
    importlib.import_module("apps.teams.admin")
    assert Team in admin.site._registry
