from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.tournaments import views as tviews


urlpatterns = [
    path('admin/', admin.site.urls),
    # CKEditor-5
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    # to work this {% url 'login' %} works
    path("accounts/", include("django.contrib.auth.urls")),

    # Apps Tournaments
    path("tournaments/", include("apps.tournaments.urls")),
        # optional short alias for brackets
        path("brackets/<slug:slug>/", tviews.bracket_view, name="bracket_view"),
        # home -> list
        path("", tviews.tournament_list, name="home"),
        # for  /t/<slug> style
        path("t/", include("apps.tournaments.urls")),

    # Apps Teams
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),

    # Apps User Profile
    path("profiles/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),

    # App Notification
    path("notifications/", include("apps.notifications.urls")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
