from django.urls import path
from .views import MyProfileUpdateView, profile_view, my_tournaments_view

app_name = "user_profile"

urlpatterns = [
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),
    path("<str:username>/", profile_view, name="profile"),
]
