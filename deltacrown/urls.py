from importlib import import_module

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    # Root & health
    path("", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("notifications/", include("apps.notifications.urls")),

    # CKEditor 5 endpoints (upload, browse, etc.)
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # New: Explore routes (non-conflicting)
    path("explore/tournaments/", views.tournaments_list, name="explore_tournaments"),
    path("explore/tournaments/<int:pk>/", views.tournament_detail, name="explore_tournament_detail"),
]

def _optional_include(prefix: str, module: str):
    """
    If `<module>.urls` exists, include it under `<prefix>/`.
    Prevents ModuleNotFoundError when an app isn't present.
    """
    try:
        import_module(f"{module}.urls")
    except ModuleNotFoundError:
        return
    urlpatterns.append(path(f"{prefix}/", include(f"{module}.urls")))

# Try to include each app's urls only if present
for _prefix, _module in [
    ("tournaments", "apps.tournaments"),
    ("teams", "apps.teams"),
    ("user", "apps.user_profile"),
    ("payment", "apps.payment"),
    ("forums", "apps.forums"),
    ("ecommerce", "apps.ecommerce"),
    ("analytics", "apps.analytics"),
]:
    _optional_include(_prefix, _module)

# Dev static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
