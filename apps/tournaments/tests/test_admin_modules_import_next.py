# apps/tournaments/tests/test_admin_modules_import_next.py
import importlib

def test_admin_modules_import_next():
    importlib.import_module("apps.tournaments.admin")  # base + re-exports
    importlib.import_module("apps.tournaments.admin.matches")
    importlib.import_module("apps.tournaments.admin.hooks")
