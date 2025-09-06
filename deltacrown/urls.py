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

    # App mounts (explicit)
    path("notifications/", include("apps.notifications.urls")),
    path("", include("apps.economy.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # Public explore pages
    path("explore/tournaments/", views.tournaments_list, name="explore_tournaments"),
    path("explore/tournaments/<int:pk>/", views.tournament_detail, name="explore_tournament_detail"),

    # Captain console (teams profile routes)
    path("profile/teams/", include("apps.teams.urls_profile")),

    # Dashboard suite
    path("", include("apps.dashboard.urls")),

    # ✅ User profile app — include ONCE with namespace “user_profile”
    #    This makes reverse("user_profile:public_profile", ...) work.
    path("user/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),
]

def _optional_include(prefix: str, module: str):
    """
    Import {module}.urls if it exists and mount it at /{prefix}/.
    Don’t use this for user_profile (we include it explicitly above with namespace).
    """
    try:
        import_module(f"{module}.urls")
    except ModuleNotFoundError:
        return
    urlpatterns.append(path(f"{prefix}/", include(f"{module}.urls")))

# Optional includes for the rest (avoid duplicating user_profile here)
for _prefix, _module in [
    ("tournaments", "apps.tournaments"),
    ("teams", "apps.teams"),
    ("payment", "apps.payment"),
    ("forums", "apps.forums"),
    ("ecommerce", "apps.ecommerce"),
    ("analytics", "apps.analytics"),
]:
    _optional_include(_prefix, _module)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
