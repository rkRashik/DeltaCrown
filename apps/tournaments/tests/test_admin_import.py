import importlib
from django.contrib import admin
from apps.tournaments.models import Tournament

def test_admin_autodiscover_imports_tournaments_admin():
    importlib.import_module("apps.tournaments.admin")
    assert Tournament in admin.site._registry
