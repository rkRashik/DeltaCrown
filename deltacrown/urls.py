# deltacrown/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap

from . import views as project_views
from apps.user_profile import views as user_profile_views
from .sitemaps import sitemaps

urlpatterns = [
    # Home
    path("", project_views.home, name="home"),

    # Dashboard (login required at view level)
    path("dashboard/", user_profile_views.dashboard, name="dashboard"),

    # Admin
    path("admin/", admin.site.urls),

    # Auth (built-in)
    path("accounts/", include("django.contrib.auth.urls")),

    # CKEditor-5 uploads
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # SEO endpoints
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots_txt",
    ),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="sitemap",
    ),

    # Apps
    path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
    path("t/", include(("apps.tournaments.urls", "tournaments"), namespace="t")),
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),
    path("profiles/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Error handlers (use fully-qualified dotted path or module attributes)
handler404 = "deltacrown.views.page_not_found_view"
handler500 = "deltacrown.views.server_error_view"
handler403 = "deltacrown.views.permission_denied_view"