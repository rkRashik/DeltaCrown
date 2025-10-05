# apps/tournaments/urls.py
from django.urls import path

from .views.public import hub, list_by_game, detail
from .views.hub_enhanced import hub_enhanced
from .views.detail_v8 import tournament_detail_v8
from .views.dashboard_v2 import tournament_dashboard_v2

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

# Dashboard API
from .views.api_dashboard import bracket_api, matches_api, news_api, statistics_api

# Tournament Features API (Bracket, Prize, Stats)
from .api.features import (
    get_tournament_bracket,
    get_match_details,
    add_match_to_calendar,
    get_tournament_stats,
    get_participant_directory,
    get_team_stats,
    get_head_to_head,
    get_stream_data,
    get_chat_history,
    submit_match_prediction,
    get_match_predictions,
    get_player_stats,
    get_activities,
    get_highlights,
    track_share,
    download_schedule,
    download_bracket,
)

# Enhanced API Views (New - Modern frontend integration)
from .api_views import (
    tournament_teams,
    tournament_matches,
    tournament_leaderboard,
    tournament_registration_status,
    featured_tournaments,
    tournament_live_stats,
)

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

    # Detail (V8 - Complete rebuild with premium design and real data)
    path("t/<slug:slug>/", tournament_detail_v8, name="detail"),
    
    # Dashboard (Participant view)
    path("t/<slug:slug>/dashboard/", tournament_dashboard_v2, name="dashboard"),
    
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
    # DASHBOARD API ENDPOINTS
    # ==========================================
    
    # Dashboard APIs (for participant dashboard)
    path("api/t/<slug:slug>/bracket/", bracket_api, name="bracket_api"),
    path("api/t/<slug:slug>/matches/", matches_api, name="matches_api"),
    path("api/t/<slug:slug>/news/", news_api, name="news_api"),
    path("api/t/<slug:slug>/statistics/", statistics_api, name="statistics_api"),
    
    # ==========================================
    # ADVANCED FEATURES API (NEW)
    # ==========================================
    
    # Bracket Viewer API
    path("api/tournaments/<slug:slug>/bracket/", get_tournament_bracket, name="features_bracket_api"),
    
    # Match Details API
    path("api/tournaments/match/<int:match_id>/", get_match_details, name="match_details_api"),
    
    # Calendar Integration API
    path("api/tournaments/match/<int:match_id>/calendar/", add_match_to_calendar, name="match_calendar_api"),
    
    # Tournament Stats API
    path("api/tournaments/<slug:slug>/stats/", get_tournament_stats, name="tournament_stats_api"),
    
    # Participant Directory API
    path("api/tournaments/<slug:slug>/participants/", get_participant_directory, name="participants_api"),
    
    # Team Stats API (for comparison)
    path("api/tournaments/team/<int:team_id>/stats/", get_team_stats, name="team_stats_api"),
    
    # Head-to-Head API (team comparison)
    path("api/tournaments/h2h/<int:team1_id>/<int:team2_id>/", get_head_to_head, name="head_to_head_api"),
    
    # Live Stream Data API
    path("api/tournaments/<slug:slug>/stream/", get_stream_data, name="stream_data_api"),
    
    # Chat History API
    path("api/tournaments/<slug:slug>/chat/history/", get_chat_history, name="chat_history_api"),
    
    # Match Prediction APIs
    path("api/tournaments/match/<int:match_id>/predict/", submit_match_prediction, name="submit_prediction_api"),
    path("api/tournaments/match/<int:match_id>/predictions/", get_match_predictions, name="match_predictions_api"),
    
    # Premium Features APIs
    path("api/tournaments/<slug:slug>/player-stats/", get_player_stats, name="player_stats_api"),
    path("api/tournaments/<slug:slug>/activities/", get_activities, name="activities_api"),
    path("api/tournaments/<slug:slug>/highlights/", get_highlights, name="highlights_api"),
    path("api/tournaments/<slug:slug>/track-share/", track_share, name="track_share_api"),
    path("api/tournaments/<slug:slug>/download/schedule/", download_schedule, name="download_schedule_api"),
    path("api/tournaments/<slug:slug>/download/bracket/", download_bracket, name="download_bracket_api"),
    
    # ==========================================
    # ENHANCED DETAIL PAGE APIs (NEW)
    # ==========================================
    
    # Teams API (get registered teams with players)
    path("api/t/<slug:slug>/teams/", tournament_teams, name="teams_api"),
    
    # Matches API (get match schedule and results) - Enhanced
    path("api/<slug:slug>/matches/", tournament_matches, name="matches_detail_api"),
    
    # Leaderboard API (get current standings)
    path("api/t/<slug:slug>/leaderboard/", tournament_leaderboard, name="leaderboard_api"),
    
    # Registration Status API (get user's registration status)
    path("api/t/<slug:slug>/registration-status/", tournament_registration_status, name="registration_status_api"),
    
    # Live Stats API (real-time updates for counters)
    path("api/tournaments/<slug:slug>/live-stats/", tournament_live_stats, name="live_stats_api"),
    
    # Featured Tournaments API (for hub page)
    path("api/featured/", featured_tournaments, name="featured_api"),
    
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
