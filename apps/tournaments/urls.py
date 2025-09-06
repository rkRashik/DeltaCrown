from django.urls import path
from .views import dashboard as views
from .views import public as public
from .views import my_matches as vm

app_name = "tournaments"

urlpatterns = [
    path("", public.tournament_list, name="list"),

    path("match/<int:match_id>/", views.match_review_view, name="match_review"),
    path("match/<int:match_id>/report/", views.report_match_view, name="match_report"),
    path("match/<int:match_id>/confirm/", views.match_confirm_view, name="match_confirm"),
    path("match/<int:match_id>/dispute/", views.match_dispute_view, name="match_dispute"),
    path("match/<int:match_id>/comment/", views.match_comment_view, name="match_comment"),
    path("staff/match/<int:match_id>/resolve/", views.match_dispute_resolve_view, name="match_dispute_resolve"),

    path("my-matches/", vm.my_matches, name="my_matches"),
    path("my-matches/save-default/", vm.save_default_filter, name="my_matches_save_default"),
    path("my-matches/pin/<int:tournament_id>/", vm.toggle_pin, name="my_matches_toggle_pin"),
    path("my-matches/export.csv", vm.my_matches_csv, name="my_matches_csv"),
    path("my-matches/ics/", vm.my_matches_ics_link, name="my_matches_ics_link"),
    path("my-matches/ics/<str:token>.ics", vm.my_matches_ics, name="my_matches_ics"),

    path("brackets/<slug:slug>/", views.bracket_view, name="bracket_view"),
    path("<slug:slug>/register/success/", public.register_success, name="register_success"),
    path("<slug:slug>/register/", public.register_view, name="register"),
    path("<slug:slug>/", public.tournament_detail, name="detail"),
]
