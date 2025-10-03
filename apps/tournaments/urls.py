# apps/tournaments/urls.py
from django.urls import path

from .views.public import hub, list_by_game, detail
from .views.hub_enhanced import hub_enhanced
from .views.detail_enhanced import detail_enhanced

# Modern Registration System (CANONICAL)
from .views.registration_modern import (
    modern_register_view,
    registration_context_api,
    validate_registration_api,
    submit_registration_api,
    request_approval_api,
    pending_requests_api,
    approve_request_api,
    reject_request_api,
)

# State Management API
from .views.state_api import tournament_state_api

# Deprecated views (for backward compatibility - redirect to modern)
from .views._deprecated import (
    register,
    unified_register,
    enhanced_register,
    valorant_register,
    efootball_register,
)

app_name = "tournaments"

# Optional "My Matches" — safely import all extras if present.
try:  # pragma: no cover
    from .views.my_matches import (
        my_matches,
        save_default_filter,
        toggle_pin,
        my_matches_bulk,
        my_matches_csv,
        my_matches_ics_link,
        my_matches_ics_regen,
        my_matches_ics,
    )
    HAS_MY_MATCHES = True
except Exception:  # pragma: no cover
    HAS_MY_MATCHES = False

urlpatterns = [
    # ==========================================
    # CORE TOURNAMENT PAGES
    # ==========================================
    
    # Hub / landing (Enhanced with real-time stats & filtering)
    path("", hub_enhanced, name="hub"),

    # Browse by game (e.g. /tournaments/game/valorant/)
    path("game/<slug:game>/", list_by_game, name="game"),

    # Detail (Enhanced with optimized queries & data loading)
    path("t/<slug:slug>/", detail_enhanced, name="detail"),
    
    # ==========================================
    # MODERN REGISTRATION SYSTEM (PRIMARY)
    # ==========================================
    
    # Main registration view (use this!)
    path("register-modern/<slug:slug>/", modern_register_view, name="modern_register"),
    
    # ==========================================
    # REGISTRATION API ENDPOINTS
    # ==========================================
    
    # Real-time State API (for live updates)
    path("api/<slug:slug>/state/", tournament_state_api, name="state_api"),
    
    # Registration Context & Validation
    path("api/<slug:slug>/register/context/", registration_context_api, name="registration_context_api"),
    path("api/<slug:slug>/register/validate/", validate_registration_api, name="validate_registration_api"),
    path("api/<slug:slug>/register/submit/", submit_registration_api, name="submit_registration_api"),
    path("api/<slug:slug>/request-approval/", request_approval_api, name="request_approval_api"),
    
    # Approval Request APIs
    path("api/registration-requests/pending/", pending_requests_api, name="pending_requests_api"),
    path("api/registration-requests/<int:request_id>/approve/", approve_request_api, name="approve_request_api"),
    path("api/registration-requests/<int:request_id>/reject/", reject_request_api, name="reject_request_api"),
    
    # ==========================================
    # DEPRECATED REGISTRATION VIEWS
    # ⚠️ These redirect to modern_register_view
    # ⚠️ Will be removed in version 2.0
    # ==========================================
    
    # Legacy registration (DEPRECATED - redirects to modern)
    path("register/<slug:slug>/", register, name="register"),
    
    # Unified registration (DEPRECATED - redirects to modern)
    path("register-new/<slug:slug>/", unified_register, name="unified_register"),
    
    # Enhanced registration (DEPRECATED - redirects to modern)
    path("register-enhanced/<slug:slug>/", enhanced_register, name="enhanced_register"),
    
    # Game-specific registration (DEPRECATED - redirects to modern)
    path("valorant/<slug:slug>/", valorant_register, name="valorant_register"),
    path("efootball/<slug:slug>/", efootball_register, name="efootball_register"),
]

# Optional: My Matches surface and helpers
if HAS_MY_MATCHES:
    urlpatterns += [
        # Dashboard-like list
        path("my/matches/", my_matches, name="my_matches"),
        # Save default filter
        path("my/matches/save-default/", save_default_filter, name="my_matches_save_default"),
        # Pin/unpin tournaments
        path("my/matches/pin/<int:tournament_id>/", toggle_pin, name="my_matches_toggle_pin"),
        # Bulk attendance actions
        path("my/matches/bulk/", my_matches_bulk, name="my_matches_bulk"),
        # Export CSV
        path("my/matches.csv", my_matches_csv, name="my_matches_csv"),
        # ICS help + management
        path("my/matches/ics/", my_matches_ics_link, name="my_matches_ics_link"),
        path("my/matches/ics/regen/", my_matches_ics_regen, name="my_matches_ics_regen"),
        # ICS feed (tokenized)
        path("my/matches/ics/<str:token>.ics", my_matches_ics, name="my_matches_ics"),
    ]
