# apps/user_profile/urls.py
from django.urls import path
from .views import MyProfileUpdateView, profile_view, my_tournaments_view
from .views_public import public_profile, profile_api
from .api_views import get_game_id, update_game_id

app_name = "user_profile"

urlpatterns = [
    # Owner pages
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),

    # Public profile (invariant)
    path("u/<str:username>/", public_profile, name="public_profile"),
    
    # API endpoints - specific paths BEFORE catch-all patterns
    path("api/profile/get-game-id/", get_game_id, name="get_game_id"),
    path("api/profile/update-game-id/", update_game_id, name="update_game_id"),
    path("api/profile/<str:profile_id>/", profile_api, name="profile_api"),

    # Modern profile page (primary)
    path("profile/", profile_view, name="profile"),
    
    # Legacy private profile page (kept for compatibility)
    path("<str:username>/", profile_view, name="profile_legacy"),
]
