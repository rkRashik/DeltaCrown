from django.urls import path
from . import views                      # report/brackets/detail (server-side)
from . import views_public as public     # public pages (list/detail/register/filters)

app_name = "tournaments"

urlpatterns = [
    # Public list
    path("", public.tournament_list, name="list"),

    # Matches: review/report/confirm/dispute/comment (specific first)
    path("match/<int:match_id>/", views.match_review_view, name="match_review"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("match/<int:match_id>/confirm/", views.match_confirm_view, name="match_confirm"),
    path("match/<int:match_id>/dispute/", views.match_dispute_view, name="match_dispute"),
    path("match/<int:match_id>/comment/", views.match_comment_view, name="match_comment"),

    # My matches (specific)
    path("my-matches/", public.my_matches_view, name="my_matches"),

    # Bracket (specific)
    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),

    # Registration (more specific than detail)
    path("<slug:slug>/register/success/", public.register_success, name="register_success"),
    path("<slug:slug>/register/", public.register_view, name="register"),

    # Tournament detail (catch-all LAST)
    path("<slug:slug>/", public.tournament_detail, name="detail"),
]
