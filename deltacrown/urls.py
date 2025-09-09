# deltacrown/urls.py
from importlib import import_module

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from .views import healthz

urlpatterns = [
    # Root + health
    path("", include("apps.siteui.urls")),
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),



    # Core apps (explicit)
    path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),

    # User profile — include ONCE with namespace & prefix invariant
    path("user/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),

    # Optional extras mounted if present
    path("notifications/", include("apps.notifications.urls")) if import_module else None,
    path("", include("apps.dashboard.urls")),
    path("", include("apps.economy.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

# Drop any Nones inserted by the conditional line above
urlpatterns = [u for u in urlpatterns if u is not None]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
