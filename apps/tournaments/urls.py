from django.urls import path
from .views import dashboard as views
from .views import public as public


app_name = "tournaments"

urlpatterns = [
    path("", public.tournament_list, name="list"),

    # Matches
    path("match/<int:match_id>/", views.match_review_view, name="match_review"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("match/<int:match_id>/confirm/", views.match_confirm_view, name="match_confirm"),
    path("match/<int:match_id>/dispute/", views.match_dispute_view, name="match_dispute"),
    path("match/<int:match_id>/comment/", views.match_comment_view, name="match_comment"),
    path("staff/match/<int:match_id>/resolve/", views.match_dispute_resolve_view, name="match_dispute_resolve"),

    # My matches
    path("my-matches/", public.my_matches_view, name="my_matches"),

    # Bracket
    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),

    # Registration (before detail)
    path("<slug:slug>/register/success/", public.register_success, name="register_success"),
    path("<slug:slug>/register/", public.register_view, name="register"),

    # Detail (catch-all)
    path("<slug:slug>/", public.tournament_detail, name="detail"),
]
