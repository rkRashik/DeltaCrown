import importlib

def test_views_package_imports_and_attrs():
    pkg = importlib.import_module("apps.tournaments.views")
    public = importlib.import_module("apps.tournaments.views.public")
    dashboard = importlib.import_module("apps.tournaments.views.dashboard")

    # At least one public and one dashboard callable should be visible at package level.
    # Adjust names here to your actual views if you want it stricter.
    assert hasattr(pkg, "tournament_list") or hasattr(public, "tournament_list")
    assert hasattr(pkg, "match_review_view") or hasattr(dashboard, "match_review_view")
def test_views_urls_still_import():
    # Make sure the URLConf still imports and includes patterns
    import importlib
    urls = importlib.import_module("apps.tournaments.urls")
    assert hasattr(urls, "urlpatterns") and len(urls.urlpatterns) > 0
