# apps/tournaments/tests/test_admin_modules_import.py
import importlib

def test_admin_modules_import():
    importlib.import_module("apps.tournaments.admin")  # triggers base + re-exports
    importlib.import_module("apps.tournaments.admin.tournaments")
    importlib.import_module("apps.tournaments.admin.registrations")
    importlib.import_module("apps.tournaments.admin.exports")
    importlib.import_module("apps.tournaments.admin.components")
