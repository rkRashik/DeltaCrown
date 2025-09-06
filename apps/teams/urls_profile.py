from django.urls import path
from .views.manage_console import manage_team_by_game

app_name = "teams_profile"

urlpatterns = [
    path("<str:game>/manage/", manage_team_by_game, name="manage_team_by_game"),
]
