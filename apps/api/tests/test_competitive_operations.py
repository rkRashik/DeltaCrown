from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.competition.models import Bounty, BountyClaim, Challenge
from apps.contracts.models import ContractEnrollment, ContractTemplate
from apps.organizations.choices import MembershipRole
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.tournaments.models import DisputeRecord, Match, MatchResultSubmission, Tournament


ENDPOINT = "/api/v1/competitive/my-operations/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def game():
    return GameFactory(short_code="OPS", slug="ops-game")


def authenticate(client, user):
    client.force_authenticate(user=user)
    return client


def create_linked_tournament_match(*, game, organizer, team, opponent, state=Match.PENDING_RESULT):
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Linked Competitive Match",
        slug=f"linked-competitive-{team.id}-{opponent.id}-{int(now.timestamp())}",
        game=game,
        organizer=organizer,
        format=Tournament.SINGLE_ELIMINATION,
        participation_type="TEAM",
        max_participants=2,
        min_participants=2,
        registration_start=now,
        registration_end=now,
        tournament_start=now,
        is_featured=False,
        is_official=False,
    )
    return Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=team.id,
        participant1_name=team.name,
        participant2_id=opponent.id,
        participant2_name=opponent.name,
        state=state,
        scheduled_time=now,
    )


@pytest.mark.django_db
def test_my_operations_requires_auth(api_client):
    response = api_client.get(ENDPOINT)

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_my_operations_includes_user_mission_enrollment(api_client, game):
    user = UserFactory()
    template = ContractTemplate.objects.create(
        title="Daily Survival Run",
        game=game,
        entry_fee_dc=25,
        reward_dc=100,
        duration_hours=24,
    )
    enrollment = ContractEnrollment.objects.create(
        user=user,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=24),
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    items = response.json()["results"]
    mission = next(item for item in items if item["id"] == str(enrollment.id))
    assert mission["type"] == "mission"
    assert mission["title"] == "Daily Survival Run"
    assert mission["next_action_label"] == "Track Mission"
    assert mission["is_action_required"] is True


@pytest.mark.django_db
def test_my_operations_includes_authority_team_showdown_and_bounty(api_client, game):
    user = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.MANAGER)
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Protocol Night",
        entry_fee_dc=200,
    )
    bounty = Bounty.objects.create(
        issuer_team=team,
        game=game,
        title="Beat Protocol",
        reward_amount_dc=500,
        challenger_entry_fee_dc=100,
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    items = response.json()["results"]
    assert any(item["id"] == str(showdown.id) and item["type"] == "showdown" for item in items)
    assert any(item["id"] == f"issued:{bounty.id}" and item["type"] == "bounty" for item in items)


@pytest.mark.django_db
def test_my_operations_hides_private_team_operations_from_unrelated_users(api_client, game):
    manager = UserFactory()
    outsider = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Private Team Operation",
        entry_fee_dc=200,
    )
    bounty = Bounty.objects.create(
        issuer_team=team,
        game=game,
        title="Private Bounty",
        reward_amount_dc=300,
        challenger_entry_fee_dc=50,
    )
    BountyClaim.objects.create(bounty=bounty, claiming_team=opponent, claimed_by=manager)

    response = authenticate(api_client, outsider).get(ENDPOINT)

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["results"]}
    assert str(showdown.id) not in ids
    assert f"issued:{bounty.id}" not in ids
    assert all(not item_id.startswith("claim:") for item_id in ids)


@pytest.mark.django_db
def test_my_operations_uses_safe_bounty_claim_lifecycle_labels(api_client, game):
    user = UserFactory()
    claimant = TeamFactory(game_id=game.id)
    issuer = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=claimant, user=user, role=MembershipRole.MANAGER)

    pending_bounty = Bounty.objects.create(
        issuer_team=issuer,
        game=game,
        title="Pending Review Bounty",
        reward_amount_dc=250,
    )
    rejected_bounty = Bounty.objects.create(
        issuer_team=issuer,
        game=game,
        title="Rejected Claim Bounty",
        reward_amount_dc=250,
    )
    verified_bounty = Bounty.objects.create(
        issuer_team=issuer,
        game=game,
        title="Verified Claim Bounty",
        reward_amount_dc=250,
    )
    pending = BountyClaim.objects.create(
        bounty=pending_bounty,
        claiming_team=claimant,
        claimed_by=user,
        status="PENDING",
    )
    rejected = BountyClaim.objects.create(
        bounty=rejected_bounty,
        claiming_team=claimant,
        claimed_by=user,
        status="REJECTED",
    )
    verified = BountyClaim.objects.create(
        bounty=verified_bounty,
        claiming_team=claimant,
        claimed_by=user,
        status="VERIFIED",
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()["results"]}
    assert by_id[f"claim:{pending.id}"]["next_action_label"] == "Waiting for Review"
    assert by_id[f"claim:{pending.id}"]["is_action_required"] is False
    assert by_id[f"claim:{rejected.id}"]["next_action_label"] == "Claim Rejected"
    assert by_id[f"claim:{verified.id}"]["next_action_label"] == "View Result"


@pytest.mark.django_db
def test_my_operations_routes_linked_showdown_result_to_match_room(api_client, game):
    user = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.MANAGER)
    match = create_linked_tournament_match(
        game=game,
        organizer=user,
        team=team,
        opponent=opponent,
        state=Match.PENDING_RESULT,
    )
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Linked Showdown",
        entry_fee_dc=200,
        status="ACCEPTED",
        match=match,
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    item = next(item for item in response.json()["results"] if item["id"] == str(showdown.id))
    assert item["match_room_url"] == f"/tournaments/{match.tournament.slug}/matches/{match.id}/room/"
    assert item["next_action_label"] == "Submit Result in Match Room"
    assert item["next_action_url"] == item["match_room_url"]
    assert item["submit_result_url"] is None
    assert item["linked_result_state"] == "result_needed"


@pytest.mark.django_db
def test_my_operations_derives_showdown_proof_review_state(api_client, game):
    user = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.MANAGER)
    match = create_linked_tournament_match(
        game=game,
        organizer=user,
        team=team,
        opponent=opponent,
        state=Match.PENDING_RESULT,
    )
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Proof Review Showdown",
        entry_fee_dc=200,
        status="ACCEPTED",
        match=match,
    )
    MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=team.id,
        raw_result_payload={"side": 1, "score_for": 13, "score_against": 9},
        proof_screenshot_url="https://example.com/proof.png",
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    item = next(item for item in response.json()["results"] if item["id"] == str(showdown.id))
    assert item["next_action_label"] == "Proof Under Review"
    assert item["linked_result_state"] == "viewer_submitted"
    assert item["linked_result_submission_count"] == 1


@pytest.mark.django_db
def test_my_operations_derives_showdown_dispute_state(api_client, game):
    user = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.MANAGER)
    match = create_linked_tournament_match(
        game=game,
        organizer=user,
        team=team,
        opponent=opponent,
        state=Match.DISPUTED,
    )
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Disputed Showdown",
        entry_fee_dc=200,
        status="ACCEPTED",
        match=match,
    )
    submission = MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=team.id,
        raw_result_payload={"side": 1, "score_for": 13, "score_against": 9},
    )
    DisputeRecord.objects.create(
        submission=submission,
        opened_by_user=user,
        opened_by_team_id=team.id,
        reason_code=DisputeRecord.REASON_SCORE_MISMATCH,
        description="Scoreline needs organizer review.",
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    item = next(item for item in response.json()["results"] if item["id"] == str(showdown.id))
    assert item["next_action_label"] == "Under Review"
    assert item["linked_result_state"] == "under_review"
    assert item["linked_open_dispute_count"] == 1


@pytest.mark.django_db
def test_my_operations_includes_bounty_claim_match_room_url(api_client, game):
    user = UserFactory()
    claimant = TeamFactory(game_id=game.id)
    issuer = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=claimant, user=user, role=MembershipRole.MANAGER)
    match = create_linked_tournament_match(
        game=game,
        organizer=user,
        team=issuer,
        opponent=claimant,
        state=Match.SCHEDULED,
    )
    bounty = Bounty.objects.create(
        issuer_team=issuer,
        game=game,
        title="Linked Bounty",
        reward_amount_dc=250,
        challenger_entry_fee_dc=50,
    )
    claim = BountyClaim.objects.create(
        bounty=bounty,
        claiming_team=claimant,
        claimed_by=user,
        status="PENDING",
        match=match,
    )

    response = authenticate(api_client, user).get(ENDPOINT)

    assert response.status_code == 200
    item = next(item for item in response.json()["results"] if item["id"] == f"claim:{claim.id}")
    assert item["match_room_url"] == f"/tournaments/{match.tournament.slug}/matches/{match.id}/room/"
    assert item["next_action_label"] == "Enter Match Room"
    assert item["linked_result_state"] == "room_ready"
