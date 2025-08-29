from django.urls import path
from . import views
from . import views_public as public

app_name = "tournaments"

urlpatterns = [
    path("", public.tournament_list, name="list"),
    path("<slug:slug>/", public.tournament_detail, name="detail"),
    path("<slug:slug>/register/", views.register_view, name="register"),
    path("<slug:slug>/register/success/", views.register_success, name="register_success"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),
    path("<slug:slug>/", views.tournament_detail, name="tournament_detail"),



]
