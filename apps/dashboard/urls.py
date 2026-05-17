from django.urls import path
from .views import (
    competitive_bounty_claim_detail_view,
    competitive_bounty_detail_view,
    competitive_dropzone_lobby_detail_view,
    competitive_dropzone_entry_detail_view,
    competitive_hub_view,
    competitive_dispute_center_view,
    competitive_mission_detail_view,
    competitive_proof_file_view,
    competitive_match_proof_file_view,
    competitive_dispute_evidence_file_view,
    competitive_match_media_file_view,
    competitive_review_workspace_view,
    competitive_showdown_detail_view,
    dashboard_index,
    my_matches_view,
)

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", dashboard_index, name="index"),
    # Compatibility route
    path("my/matches/", my_matches_view, name="my_matches"),
    # Preferred route
    path("dashboard/matches/", my_matches_view, name="matches"),
    # Competitive Hub and lightweight operation detail pages.
    path("dashboard/competitive/", competitive_hub_view, name="competitive_hub"),
    path("dashboard/competitive/review/", competitive_review_workspace_view, name="competitive_review_workspace"),
    path("dashboard/competitive/disputes/", competitive_dispute_center_view, name="competitive_dispute_center"),
    path("dashboard/competitive/proofs/<uuid:proof_id>/file/", competitive_proof_file_view, name="competitive_proof_file"),
    path("dashboard/competitive/match-proofs/<int:submission_id>/file/", competitive_match_proof_file_view, name="competitive_match_proof_file"),
    path("dashboard/competitive/dispute-evidence/<int:evidence_id>/file/", competitive_dispute_evidence_file_view, name="competitive_dispute_evidence_file"),
    path("dashboard/competitive/match-media/<uuid:media_id>/file/", competitive_match_media_file_view, name="competitive_match_media_file"),
    path(
        "dashboard/competitive/showdowns/<uuid:challenge_id>/",
        competitive_showdown_detail_view,
        name="competitive_showdown_detail",
    ),
    path(
        "dashboard/competitive/missions/<uuid:enrollment_id>/",
        competitive_mission_detail_view,
        name="competitive_mission_detail",
    ),
    path(
        "dashboard/competitive/bounties/<uuid:bounty_id>/",
        competitive_bounty_detail_view,
        name="competitive_bounty_detail",
    ),
    path(
        "dashboard/competitive/bounty-claims/<uuid:claim_id>/",
        competitive_bounty_claim_detail_view,
        name="competitive_bounty_claim_detail",
    ),
    path(
        "dashboard/competitive/dropzone/lobbies/<uuid:lobby_id>/",
        competitive_dropzone_lobby_detail_view,
        name="competitive_dropzone_lobby_detail",
    ),
    path(
        "dashboard/competitive/dropzone/entries/<uuid:entry_id>/",
        competitive_dropzone_entry_detail_view,
        name="competitive_dropzone_entry_detail",
    ),
]
