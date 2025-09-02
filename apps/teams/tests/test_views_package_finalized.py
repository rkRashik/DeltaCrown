# apps/teams/tests/test_views_package_finalized.py
import importlib

def test_teams_views_package_imports_and_attrs():
    pkg = importlib.import_module("apps.teams.views")
    public = importlib.import_module("apps.teams.views.public")
    manage = importlib.import_module("apps.teams.views.manage")
    # At least one callable (adjust to your real names)
    assert hasattr(pkg, "team_index") or hasattr(public, "team_index")
    # manage should forward to public
    assert hasattr(manage, "team_index")
