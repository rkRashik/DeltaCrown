# apps/corelib/tests/test_admin_imports.py
import importlib
from django.contrib import admin


def test_notifications_admin_import_and_registry():
    importlib.import_module("apps.notifications.admin")
    from apps.notifications.models import Notification
    assert Notification in admin.site._registry


def test_teams_admin_import_and_registry():
    importlib.import_module("apps.teams.admin")
    from apps.teams.models import Team
    assert Team in admin.site._registry


def test_tournaments_admin_import_and_registry():
    importlib.import_module("apps.tournaments.admin")
    from apps.tournaments.models import Tournament
    assert Tournament in admin.site._registry
