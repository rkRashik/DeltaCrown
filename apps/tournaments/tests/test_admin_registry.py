# apps/tournaments/tests/test_admin_registry.py
import importlib
from django.contrib import admin
from apps.tournaments.models import Tournament, Registration

def test_tournament_admin_registered():
    importlib.import_module("apps.tournaments.admin")
    assert Tournament in admin.site._registry

def test_registration_admin_registered():
    importlib.import_module("apps.tournaments.admin")
    assert Registration in admin.site._registry
