# apps/corelib/tests/test_urls_imports.py
import importlib


def _has_patterns(module_path):
    mod = importlib.import_module(module_path)
    return hasattr(mod, "urlpatterns") and len(getattr(mod, "urlpatterns")) > 0


def test_urls_import_teams():
    assert _has_patterns("apps.teams.urls")


def test_urls_import_tournaments():
    assert _has_patterns("apps.tournaments.urls")
