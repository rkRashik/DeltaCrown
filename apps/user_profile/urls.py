from django.urls import path
from .views import MyProfileUpdateView, profile_view, my_tournaments_view
from . import views

app_name = "user_profile"

urlpatterns = [
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("<str:username>/", views.profile_view, name="profile"),
    path("<str:username>/", profile_view, name="profile"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),
]
