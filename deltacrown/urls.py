# deltacrown/urls.py
from importlib import import_module

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from .views import healthz
from django.views.generic import TemplateView
from apps.players import views as player_views
from apps.search import views as search_views
from apps.siteui import views as site_views
from apps.support import views as support_views
from django.views.generic import RedirectView


urlpatterns = [
    # Root + health
    path("", include("apps.siteui.urls")),
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("account/", include(("apps.accounts.urls", "account"), namespace="account")),

    # Crawlers / SEO
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),


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
    path("players/<str:username>/", player_views.player_detail, name="player_detail"),
    path("search/", search_views.search, name="search"),
    path("privacy/", site_views.privacy, name="privacy"),
    path("terms/", site_views.terms, name="terms"),
    path("help/", support_views.faq_view, name="faq"),
    path("contact/", support_views.contact_view, name="contact"),
]

# Optional allauth routing
try:
    import allauth  # type: ignore
    urlpatterns += [path("accounts/", include("allauth.urls"))]
except Exception:
    # Graceful fallbacks for login/signup/logout URLs if allauth is not installed
    urlpatterns += [
        path("accounts/login/", RedirectView.as_view(url="/account/login/", permanent=False)),
        path("accounts/signup/", RedirectView.as_view(url="/account/signup/", permanent=False)),
        path("accounts/logout/", RedirectView.as_view(url="/account/logout/", permanent=False)),
    ]

# Drop any Nones inserted by the conditional line above
urlpatterns = [u for u in urlpatterns if u is not None]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
