# apps/corelib/tests/test_views_packages.py
import importlib


def test_tournaments_views_packages_importable():
    pkg = importlib.import_module("apps.tournaments.views")
    public = importlib.import_module("apps.tournaments.views.public")
    dashboard = importlib.import_module("apps.tournaments.views.dashboard")
    # at least one callable visible at package level
    assert hasattr(pkg, "tournament_list") or hasattr(public, "tournament_list")


def test_teams_views_packages_importable_and_alias():
    pkg = importlib.import_module("apps.teams.views")
    public = importlib.import_module("apps.teams.views.public")
    manage = importlib.import_module("apps.teams.views.manage")
    # our compat alias guarantees team_index is exposed somewhere
    assert hasattr(pkg, "team_index") or hasattr(public, "team_index")
    # manage should also expose it (alias set in __init__)
    assert hasattr(manage, "team_index")
