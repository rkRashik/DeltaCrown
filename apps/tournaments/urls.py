# apps/tournaments/urls.py
from django.urls import path
from . import views                      # report/bracket utilities live here
from . import views_public as public     # public pages (list/detail/register/success)

app_name = "tournaments"

urlpatterns = [
    # Public list/detail
    path("", public.tournament_list, name="list"),
    path("<slug:slug>/", public.tournament_detail, name="detail"),

    # Registration flow (public)
    path("<slug:slug>/register/", public.register_view, name="register"),
    path("<slug:slug>/register/success/", public.register_success, name="register_success"),

    # Brackets / match reporting + review
    path("match/<int:match_id>/", views.match_review_view, name="match_review"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("match/<int:match_id>/confirm/", views.match_confirm_view, name="match_confirm"),
    path("match/<int:match_id>/dispute/", views.match_dispute_view, name="match_dispute"),

    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),
]
