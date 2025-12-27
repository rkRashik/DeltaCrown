"""
Games app URL configuration
"""
from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('api/games/', views.games_list, name='games_list'),
    path('api/games/<int:game_id>/schema/', views.game_identity_schema, name='game_identity_schema'),
]
