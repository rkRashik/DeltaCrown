from django.urls import path

# Owner/private views you already had
from .views import MyProfileUpdateView, profile_view, my_tournaments_view

# Public view lives in a separate module so imports are unambiguous
from .views_public import public_profile

app_name = "user_profile"

urlpatterns = [
    # Owner pages
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),

    # ✅ Public profile (this is what reverse('user_profile:public_profile', ...) targets)
    path("u/<str:username>/", public_profile, name="public_profile"),

    # Existing private/owner-facing profile
    path("<str:username>/", profile_view, name="profile"),
]
