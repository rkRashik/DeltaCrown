# deltacrown/urls.py
from importlib import import_module

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from .views import healthz, readiness, test_game_assets
from django.views.generic import TemplateView
from apps.players import views as player_views
from apps.search import views as search_views
from apps.siteui import views as site_views
from apps.support import views as support_views
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    # Root + health
    path("", include("apps.siteui.urls")),
    path("healthz/", healthz, name="healthz"),
    path("readiness/", readiness, name="readiness"),  # Module 2.4: Security Hardening
    
    # Prometheus metrics (Phase 3 Prep: Monitoring)
    path("metrics/", include("django_prometheus.urls")),
    
    path("test-game-assets/", test_game_assets, name="test_game_assets"),
    
    # Phase 9A-30: Custom Game Passport Admin (must come BEFORE Django admin catch-all)
    # Routes /admin/game-passports/* to custom interface instead of Django admin
    path("admin/game-passports/", include("apps.user_profile.urls_admin")),
    
    path("admin/", admin.site.urls),
    path("account/", include(("apps.accounts.urls", "account"), namespace="account")),

    # Favicon test page
    path("favicon-test/", TemplateView.as_view(template_name="favicon_test.html"), name="favicon_test"),

    # Favicon - Direct route for browser default lookup
    path("favicon.ico", RedirectView.as_view(url=settings.STATIC_URL + "img/favicon/favicon.ico", permanent=False)),

    # Crawlers / SEO
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),

    # -------------------------------------------------------------------------
    # JWT Authentication API (Phase 2: Real-Time Features & Security)
    # -------------------------------------------------------------------------
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # -------------------------------------------------------------------------
    # API Documentation (Phase 9, Epic 9.1: API Documentation Generator)
    # -------------------------------------------------------------------------
    # OpenAPI 3.0 schema endpoint (JSON)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI (interactive API documentation)
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # ReDoc UI (alternative API documentation)
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),


    # Core apps (explicit)
    # vNext Organizations & Teams (MUST come before legacy teams to override /teams/create/)
    path("", include("apps.organizations.urls")),
    
    # vNext Organizations API (explicitly registered namespace for {% url 'organizations_api:...' %})
    path("api/vnext/", include(("apps.organizations.api.urls", "organizations_api"), namespace="organizations_api")),
    
    # Tournament system - Admin only (frontend moved to legacy November 2, 2025)
    # URL namespace kept active for admin panel functionality
    path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),
    path("", include(("apps.games.urls", "games"), namespace="games")),
    
    # API endpoints
    # Module 3.1: Registration Flow & Validation API
    path("api/tournaments/", include("apps.tournaments.api.urls")),
    
    # Phase 7, Epic 7.3: Staff & Referee Role System API
    path("api/staffing/", include("apps.api.urls.tournament_staffing_urls")),
    
    # Phase 7, Epic 7.4: Match Operations Command Center API
    path("api/match-ops/", include("apps.api.urls.match_ops_urls")),
    
    # Phase 7, Epic 7.5: Audit Log System API
    path("api/audit-logs/", include("apps.api.urls.audit_log_urls")),
    
    # Phase 7, Epic 7.6: Help & Onboarding API
    path("api/organizer/help/", include("apps.api.urls.help_urls")),
    
    # Phase 8, Epic 8.2: User Stats Service API
    path("api/stats/v1/", include("apps.api.urls.user_stats_urls")),
    
    # Phase 8, Epic 8.3: Team Stats & Ranking API
    path("api/stats/v1/", include("apps.api.urls.team_stats_urls")),
    
    # Phase 8, Epic 8.4: Match History Engine API
    path("api/tournaments/v1/history/", include("apps.api.urls.match_history_urls")),
    
    # Phase 8, Epic 8.5: Advanced Analytics & Leaderboards API
    path("api/", include("apps.api.urls.analytics_urls")),
    
    # Phase B: System API (hub widgets, cross-app utilities)
    path("api/system/", include("apps.api.urls.system_api_urls")),
    
    # Module 3.3: Team Management API
    path("api/teams/", include("apps.teams.api.urls")),
    
    # Phase G: Spectator Live Views (public read-only tournament/match pages)
    path("spectator/", include(("apps.spectator.urls", "spectator"), namespace="spectator")),

    # NOTE: Mount user_profile AFTER other root-level apps to avoid catch-all conflicts (e.g. /dashboard/)
    # Backwards-compatibility legacy redirects kept below.

    # Optional extras mounted if present
    path("notifications/", include("apps.notifications.urls")) if import_module else None,
    path("", include("apps.dashboard.urls")),
    path("crownstore/", include(("apps.ecommerce.urls", "ecommerce"), namespace="ecommerce")),
    path("", include(("apps.economy.urls", "economy"), namespace="economy")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("players/<str:username>/", player_views.player_detail, name="player_detail"),
    path("search/", search_views.search, name="search"),
    path("privacy/", site_views.privacy, name="privacy"),
    path("terms/", site_views.terms, name="terms"),
    path("cookies/", site_views.cookies, name="cookies"),
    path("", include(("apps.support.urls", "support"), namespace="support")),
    # User profile system mounted last to prevent interference with other root paths
    path("", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),
    path("user/u/<str:username>/", RedirectView.as_view(pattern_name="user_profile:public_profile", permanent=True)),
    path("user/me/settings/", RedirectView.as_view(pattern_name="user_profile:settings", permanent=True)),
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
    # Serve static files from STATICFILES_DIRS during development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    # Also serve collected static files for network access
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
