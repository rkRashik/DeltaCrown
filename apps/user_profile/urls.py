# apps/user_profile/urls.py
from django.urls import path
from .views import (
    MyProfileUpdateView, profile_view, my_tournaments_view,
    kyc_upload_view, kyc_status_view, privacy_settings_view, settings_view,
    # Phase 4: Modal Action Views
    update_bio, add_social_link, add_game_profile, edit_game_profile, delete_game_profile,
    # Phase 4: Follow System
    follow_user, unfollow_user, followers_list, following_list,
    # Phase 4: Full Page Views
    achievements_view, match_history_view, certificates_view
)
from .views_public import public_profile, profile_api
from .api_views import get_game_id, update_game_id
from .api.game_id_api import (
    check_game_id_api,
    save_game_id_api,
    get_all_game_ids_api,
    delete_game_id_api
)

app_name = "user_profile"

urlpatterns = [
    # ============================================
    # OWNER PAGES (me/...)
    # ============================================
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),
    
    # KYC Verification
    path("me/kyc/upload/", kyc_upload_view, name="kyc_upload"),
    path("me/kyc/status/", kyc_status_view, name="kyc_status"),
    
    # Privacy Settings
    path("me/privacy/", privacy_settings_view, name="privacy_settings"),
    
    # Modular Settings Page
    path("me/settings/", settings_view, name="settings"),

    # ============================================
    # PHASE 4: MODAL ACTION ENDPOINTS (POST handlers)
    # ============================================
    path("actions/update-bio/", update_bio, name="update_bio"),
    path("actions/add-social-link/", add_social_link, name="add_social_link"),
    path("actions/add-game-profile/", add_game_profile, name="add_game_profile"),
    path("actions/edit-game-profile/<int:profile_id>/", edit_game_profile, name="edit_game_profile"),
    path("actions/delete-game-profile/<int:profile_id>/", delete_game_profile, name="delete_game_profile"),
    
    # Follow System
    path("actions/follow/<str:username>/", follow_user, name="follow_user"),
    path("actions/unfollow/<str:username>/", unfollow_user, name="unfollow_user"),
    path("@<str:username>/followers/", followers_list, name="followers_list"),
    path("@<str:username>/following/", following_list, name="following_list"),

    # ============================================
    # API ENDPOINTS (api/...)
    # Specific paths BEFORE catch-all patterns
    # ============================================
    path("api/profile/get-game-id/", get_game_id, name="get_game_id"),
    path("api/profile/update-game-id/", update_game_id, name="update_game_id"),
    
    # Modern Game ID API endpoints
    path("api/profile/check-game-id/<str:game_code>/", check_game_id_api, name="check_game_id_api"),
    path("api/profile/save-game-id/<str:game_code>/", save_game_id_api, name="save_game_id_api"),
    path("api/profile/game-ids/", get_all_game_ids_api, name="get_all_game_ids_api"),
    path("api/profile/delete-game-id/<str:game_code>/", delete_game_id_api, name="delete_game_id_api"),
    
    path("api/profile/<str:profile_id>/", profile_api, name="profile_api"),

    # ============================================
    # PHASE 4: PUBLIC PROFILE PAGES (@username/...)
    # IMPORTANT: These must come AFTER specific paths to avoid conflicts
    # ============================================
    
    # Full-page component views
    path("@<str:username>/achievements/", achievements_view, name="achievements"),
    path("@<str:username>/match-history/", match_history_view, name="match_history"),
    path("@<str:username>/certificates/", certificates_view, name="certificates"),
    
    # Main profile page (@ prefix for modern social media convention)
    path("@<str:username>/", profile_view, name="profile"),
    
    # ============================================
    # LEGACY COMPATIBILITY ROUTES
    # ============================================
    
    # Legacy public profile (u/ prefix)
    path("u/<str:username>/", public_profile, name="public_profile"),
    
    # Legacy profile page without prefix (lowest priority)
    path("<str:username>/", profile_view, name="profile_legacy"),
]
