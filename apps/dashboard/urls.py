from django.urls import path
from .views import my_matches_view, dashboard_index

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", dashboard_index, name="index"),
    # Compatibility route
    path("my/matches/", my_matches_view, name="my_matches"),
    # Preferred route
    path("dashboard/matches/", my_matches_view, name="matches"),
]
