from django.urls import path
from . import views

app_name = "tournaments"

urlpatterns = [
    path("<slug:slug>/register/", views.register_view, name="register"),
    path("<slug:slug>/register/success/", views.register_success, name="register_success"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),
    path("<slug:slug>/", views.tournament_detail, name="tournament_detail"),



]
