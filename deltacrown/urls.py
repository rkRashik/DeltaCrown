# deltacrown/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views as project_views


urlpatterns = [
    # Home (new): render templates/home.html via deltacrown.views.home
    path("", project_views.home, name="home"),

    # Admin
    path("admin/", admin.site.urls),

    # Auth (login/logout/password views)
    path("accounts/", include("django.contrib.auth.urls")),

    # CKEditor-5
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # Tournaments (primary mount with namespace)
    path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
    # Optional short alias with a different namespace to avoid urls.W005
    path("t/", include(("apps.tournaments.urls", "tournaments"), namespace="t")),

    # Teams
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),

    # User profiles
    path("profiles/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),

    # Notifications
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
