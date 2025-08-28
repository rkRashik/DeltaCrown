from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.tournaments import views as tviews


urlpatterns = [
    path('admin/', admin.site.urls),
    # CKEditor-5
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    path("tournaments/", include("apps.tournaments.urls")),

    # optional short alias for brackets (Part 6)
    path("brackets/<slug:slug>/", tviews.bracket_view, name="bracket_view"),

    # home -> list
    path("", tviews.tournament_list, name="home"),

    path("teams/", include("apps.teams.urls", namespace="teams")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
