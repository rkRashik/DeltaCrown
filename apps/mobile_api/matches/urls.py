"""URL patterns for mobile match endpoints."""
from django.urls import path

from .views import (
    MobileMatchCheckInView,
    MobileMatchDetailView,
    MobileMatchLobbyView,
    MobileMatchStatusView,
    MobileMatchSubmitResultView,
    MobileMatchUploadProofView,
    MobileMyMatchesView,
)


urlpatterns = [
    path("me/matches/", MobileMyMatchesView.as_view(), name="my_matches"),
    path("matches/<int:match_id>/", MobileMatchDetailView.as_view(), name="match_detail"),
    path("matches/<int:match_id>/lobby/", MobileMatchLobbyView.as_view(), name="match_lobby"),
    path("matches/<int:match_id>/check-in/", MobileMatchCheckInView.as_view(), name="match_check_in"),
    path("matches/<int:match_id>/submit-result/", MobileMatchSubmitResultView.as_view(), name="match_submit_result"),
    path("matches/<int:match_id>/upload-proof/", MobileMatchUploadProofView.as_view(), name="match_upload_proof"),
    path("matches/<int:match_id>/status/", MobileMatchStatusView.as_view(), name="match_status"),
]
