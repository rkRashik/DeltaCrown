import importlib

def test_views_package_imports_forwarders():
    importlib.import_module("apps.tournaments.views")
    importlib.import_module("apps.tournaments.views.public")
    importlib.import_module("apps.tournaments.views.dashboard")
