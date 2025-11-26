# apps/user_profile/urls.py
from django.urls import path
from .views import (
    MyProfileUpdateView, profile_view, my_tournaments_view,
    kyc_upload_view, kyc_status_view, privacy_settings_view, settings_view
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
    # Owner pages
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),
    
    # KYC Verification
    path("me/kyc/upload/", kyc_upload_view, name="kyc_upload"),
    path("me/kyc/status/", kyc_status_view, name="kyc_status"),
    
    # Privacy Settings
    path("me/privacy/", privacy_settings_view, name="privacy_settings"),
    
    # Modular Settings Page
    path("me/settings/", settings_view, name="settings"),

    # Public profile (invariant)
    path("u/<str:username>/", public_profile, name="public_profile"),
    
    # API endpoints - specific paths BEFORE catch-all patterns
    path("api/profile/get-game-id/", get_game_id, name="get_game_id"),
    path("api/profile/update-game-id/", update_game_id, name="update_game_id"),
    
    # Modern Game ID API endpoints
    path("api/profile/check-game-id/<str:game_code>/", check_game_id_api, name="check_game_id_api"),
    path("api/profile/save-game-id/<str:game_code>/", save_game_id_api, name="save_game_id_api"),
    path("api/profile/game-ids/", get_all_game_ids_api, name="get_all_game_ids_api"),
    path("api/profile/delete-game-id/<str:game_code>/", delete_game_id_api, name="delete_game_id_api"),
    
    path("api/profile/<str:profile_id>/", profile_api, name="profile_api"),

    # Modern profile page (primary)
    path("profile/", profile_view, name="profile"),
    
    # Legacy private profile page (kept for compatibility)
    path("<str:username>/", profile_view, name="profile_legacy"),
]
