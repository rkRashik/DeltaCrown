# apps/user_profile/urls.py
from django.urls import path
from .views import MyProfileUpdateView, profile_view, my_tournaments_view
from .views_public import public_profile, profile_api

app_name = "user_profile"

urlpatterns = [
    # Owner pages
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),

    # Public profile (invariant)
    path("u/<str:username>/", public_profile, name="public_profile"),
    
    # API endpoints
    path("api/profile/<str:profile_id>/", profile_api, name="profile_api"),

    # Legacy private profile page (kept for compatibility)
    path("<str:username>/", profile_view, name="profile"),
]
