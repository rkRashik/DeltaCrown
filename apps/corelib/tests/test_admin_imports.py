# apps/corelib/tests/test_admin_imports.py
import importlib
from django.contrib import admin


def test_notifications_admin_import_and_registry():
    importlib.import_module("apps.notifications.admin")
    from apps.notifications.models import Notification  # noqa
    # Ensure admin has the model registered
    assert any(m.__name__ == "Notification" for m in admin.site._registry.keys())


def test_teams_admin_import_and_registry():
    importlib.import_module("apps.teams.admin")
    from apps.teams.models import Team  # noqa
    assert any(m.__name__ == "Team" for m in admin.site._registry.keys())


def test_user_profile_admin_import_and_registry():
    importlib.import_module("apps.user_profile.admin")
    from apps.user_profile.models import UserProfile  # noqa
    assert any(m.__name__ == "UserProfile" for m in admin.site._registry.keys())


def test_tournaments_admin_import_and_registry():
    importlib.import_module("apps.tournaments.admin")
    from apps.tournaments.models import Tournament  # noqa
    assert any(m.__name__ == "Tournament" for m in admin.site._registry.keys())
