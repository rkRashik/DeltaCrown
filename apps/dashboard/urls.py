from django.urls import path
from .views import my_matches_view

app_name = "dashboard"

urlpatterns = [
    path("my/matches/", my_matches_view, name="my_matches"),
]
