# deltacrown/urls.py (Commit 1)
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
import importlib

# Optional: attach /healthz if present in project views
healthz_view = None
try:
    from . import views as project_views  # your project's views module
    healthz_view = getattr(project_views, "healthz", None)
except Exception:
    healthz_view = None

urlpatterns = [
    # Styleguide (Commit 1)
    path(
        "ui/styleguide/",
        TemplateView.as_view(template_name="ui/styleguide.html"),
        name="ui_styleguide",
    ),

    # Admin
    path("admin/", admin.site.urls),
]

# Optional routes — only included if the module exists
def include_if_exists(prefix: str, module_path: str, namespace: str | None = None):
    try:
        importlib.import_module(module_path)
    except ImportError:
        return
    if namespace:
        urlpatterns.append(path(prefix, include((module_path, namespace))))
    else:
        urlpatterns.append(path(prefix, include(module_path)))

# Common app includes (adjust to your project layout if needed)
include_if_exists("tournaments/", "tournaments.urls")
include_if_exists("teams/", "teams.urls")
include_if_exists("user/", "user_profile.urls")
include_if_exists("notifications/", "notifications.urls")
include_if_exists("store/", "ecommerce.urls")
include_if_exists("", "common.urls")  # homepage or misc public routes if you have them

# Health check (only if available)
if healthz_view:
    urlpatterns.append(path("healthz", healthz_view, name="healthz"))
