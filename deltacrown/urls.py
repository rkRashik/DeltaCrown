# deltacrown/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth (so {% url 'login' %} works)
    path("accounts/", include("django.contrib.auth.urls")),

    # CKEditor-5
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # --- Tournaments ---
    # Primary mount with the "tournaments" namespace
    path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
    # Optional short alias; give it a DIFFERENT namespace to avoid urls.W005
    path("t/", include(("apps.tournaments.urls", "tournaments"), namespace="t")),

    # Home -> tournaments list
    path("", RedirectView.as_view(pattern_name="tournaments:list", permanent=False), name="home"),

    # Teams
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),

    # User profiles
    path("profiles/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),

    # Notifications
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
