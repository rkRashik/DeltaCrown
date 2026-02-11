"""
Challenge & Bounty API URL Configuration

Phase 10: RESTful routes for the Challenge & Bounty competitive system.
"""
from django.urls import path
from apps.api.views.challenge_views import (
    ChallengeListCreateView,
    ChallengeDetailView,
    ChallengeAcceptView,
    ChallengeDeclineView,
    ChallengeCancelView,
    ChallengeScheduleView,
    ChallengeResultView,
    ChallengeDisputeView,
    TeamChallengesView,
    TeamChallengeStatsView,
    BountyListCreateView,
    BountyClaimView,
    TeamBountiesView,
)

app_name = 'challenge_api'

urlpatterns = [
    # ── Challenges ───────────────────────────────────────────────────────
    # List / Create
    path(
        'challenges/',
        ChallengeListCreateView.as_view(),
        name='challenge-list-create',
    ),

    # Detail (by UUID or reference code)
    path(
        'challenges/<str:challenge_ref>/',
        ChallengeDetailView.as_view(),
        name='challenge-detail',
    ),

    # Lifecycle actions
    path(
        'challenges/<uuid:challenge_id>/accept/',
        ChallengeAcceptView.as_view(),
        name='challenge-accept',
    ),
    path(
        'challenges/<uuid:challenge_id>/decline/',
        ChallengeDeclineView.as_view(),
        name='challenge-decline',
    ),
    path(
        'challenges/<uuid:challenge_id>/cancel/',
        ChallengeCancelView.as_view(),
        name='challenge-cancel',
    ),
    path(
        'challenges/<uuid:challenge_id>/schedule/',
        ChallengeScheduleView.as_view(),
        name='challenge-schedule',
    ),
    path(
        'challenges/<uuid:challenge_id>/result/',
        ChallengeResultView.as_view(),
        name='challenge-result',
    ),
    path(
        'challenges/<uuid:challenge_id>/dispute/',
        ChallengeDisputeView.as_view(),
        name='challenge-dispute',
    ),

    # Team-scoped
    path(
        'teams/<str:team_slug>/challenges/',
        TeamChallengesView.as_view(),
        name='team-challenges',
    ),
    path(
        'teams/<str:team_slug>/challenges/stats/',
        TeamChallengeStatsView.as_view(),
        name='team-challenge-stats',
    ),

    # ── Bounties ─────────────────────────────────────────────────────────
    path(
        'bounties/',
        BountyListCreateView.as_view(),
        name='bounty-list-create',
    ),
    path(
        'bounties/<uuid:bounty_id>/claim/',
        BountyClaimView.as_view(),
        name='bounty-claim',
    ),
    path(
        'teams/<str:team_slug>/bounties/',
        TeamBountiesView.as_view(),
        name='team-bounties',
    ),
]
