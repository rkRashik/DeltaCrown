# apps/corelib/tests/test_views_packages.py
import importlib


def test_tournaments_views_packages_importable():
    pkg = importlib.import_module("apps.tournaments.views")
    public = importlib.import_module("apps.tournaments.views.public")
    dashboard = importlib.import_module("apps.tournaments.views.dashboard")
    # at least one common public callable should be visible
    assert hasattr(pkg, "tournament_list") or hasattr(public, "tournament_list")
    assert dashboard  # imported successfully


def test_teams_views_packages_importable_and_alias():
    pkg = importlib.import_module("apps.teams.views")
    public = importlib.import_module("apps.teams.views.public")
    manage = importlib.import_module("apps.teams.views.manage")
    # compat alias is provided at package level
    assert hasattr(pkg, "team_index") or hasattr(public, "team_index")
    # manage module should also expose index alias
    assert hasattr(manage, "team_index")
