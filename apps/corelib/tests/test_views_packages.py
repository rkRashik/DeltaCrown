# apps/corelib/tests/test_views_packages.py
import importlib


def test_tournaments_views_packages_importable():
    pkg = importlib.import_module("apps.tournaments.views")
    public = importlib.import_module("apps.tournaments.views.public")
    dashboard = importlib.import_module("apps.tournaments.views.dashboard")
    # At least one common public callable is visible (name may vary per project)
    assert hasattr(pkg, "tournament_list") or hasattr(public, "tournament_list")
    assert dashboard  # imported successfully


def test_teams_views_packages_importable():
    pkg = importlib.import_module("apps.teams.views")
    public = importlib.import_module("apps.teams.views.public")
    manage = importlib.import_module("apps.teams.views.manage")
    # Ensure the public module exposes a team list/index callable
    assert (
        hasattr(pkg, "team_list")
        or hasattr(public, "team_list")
        or hasattr(public, "team_index")
    )
    # Manage module should provide action endpoints
    assert hasattr(manage, "leave_team_view") or hasattr(manage, "transfer_captain_view")
