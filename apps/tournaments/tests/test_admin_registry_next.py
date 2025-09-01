# apps/tournaments/tests/test_admin_registry_next.py
import importlib
from django.contrib import admin
from apps.tournaments.models import Tournament, Registration, Match

def test_registry_after_split():
    importlib.import_module("apps.tournaments.admin")
    assert Tournament in admin.site._registry
    assert Registration in admin.site._registry
    assert Match in admin.site._registry
