from datetime import timedelta
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.competition.models import Bounty, BountyClaim, Challenge
from apps.contracts.models import ContractEnrollment, ContractProofSubmission, ContractTemplate
from apps.organizations.choices import MembershipRole
from apps.organizations.tests.factories import GameFactory, TeamFactory, TeamMembershipFactory, UserFactory
from apps.royale.models import RoyaleEntry, RoyaleLobby
from apps.tournaments.models import DisputeEvidence, DisputeNote, DisputeRecord, Match, MatchMedia, MatchResultSubmission, Tournament


def create_tournament_match(*, game, organizer, team, opponent, state=Match.PENDING_RESULT):
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Competitive Detail Match",
        slug=f"competitive-detail-{uuid.uuid4().hex[:10]}",
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
def test_showdown_detail_visible_to_related_team_member(client):
    game = GameFactory(short_code="SDA")
    user = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.PLAYER)
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Detail Showdown",
        status="ACCEPTED",
    )

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/showdowns/{showdown.id}/")

    assert response.status_code == 200
    assert b"Detail Showdown" in response.content
    assert b"Showdown" in response.content


@pytest.mark.django_db
def test_showdown_detail_blocks_unrelated_user(client):
    game = GameFactory(short_code="SDB")
    owner = UserFactory()
    outsider = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=owner, role=MembershipRole.MANAGER)
    showdown = Challenge.objects.create(
        challenger_team=team,
        challenged_team=opponent,
        game=game,
        title="Private Detail Showdown",
    )

    client.force_login(outsider)
    response = client.get(f"/dashboard/competitive/showdowns/{showdown.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_bounty_claim_detail_reuses_match_room_proof_state(client):
    game = GameFactory(short_code="BDA")
    user = UserFactory()
    issuer = TeamFactory(game_id=game.id)
    claimant = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=claimant, user=user, role=MembershipRole.PLAYER)
    match = create_tournament_match(game=game, organizer=user, team=issuer, opponent=claimant)
    bounty = Bounty.objects.create(
        issuer_team=issuer,
        game=game,
        title="Proof Review Bounty",
        reward_amount_dc=500,
    )
    claim = BountyClaim.objects.create(
        bounty=bounty,
        claiming_team=claimant,
        claimed_by=user,
        match=match,
    )
    MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=claimant.id,
        raw_result_payload={"winner_team_id": claimant.id},
        proof_screenshot_url="https://example.com/proof.png",
    )

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/bounty-claims/{claim.id}/")

    assert response.status_code == 200
    assert b"Proof Review Bounty" in response.content
    assert b"Proof Under Review" in response.content
    assert b"https://example.com/proof.png" in response.content


@pytest.mark.django_db
def test_dropzone_detail_hides_room_credentials_before_reveal(client):
    game = GameFactory(short_code="DZA")
    user = UserFactory()
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Future Dropzone",
        slug=f"future-dropzone-{uuid.uuid4().hex[:10]}",
        game=game,
        organizer=user,
        format=Tournament.BATTLE_ROYALE,
        participation_type="SOLO",
        max_participants=100,
        min_participants=2,
        registration_start=now,
        registration_end=now,
        tournament_start=now + timedelta(hours=3),
        is_featured=False,
        is_official=False,
    )
    lobby = RoyaleLobby.objects.create(
        tournament=tournament,
        game=game,
        title="Friday Drop",
        slot_capacity=100,
        entry_fee_dc=50,
        scheduled_at=now + timedelta(hours=3),
        room_id="SECRET-ROOM",
        room_password="SECRET-PASS",
        prize_distribution={"mode": "PERCENT", "splits": {"1": 50, "2": 25}},
    )
    entry = RoyaleEntry.objects.create(lobby=lobby, user=user)

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/dropzone/entries/{entry.id}/")

    assert response.status_code == 200
    assert b"Friday Drop" in response.content
    assert b"Room credentials unlock" in response.content
    assert b"SECRET-ROOM" not in response.content
    assert b"SECRET-PASS" not in response.content


@pytest.mark.django_db
def test_dropzone_detail_blocks_other_users(client):
    game = GameFactory(short_code="DZB")
    user = UserFactory()
    outsider = UserFactory()
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Private Dropzone",
        slug=f"private-dropzone-{uuid.uuid4().hex[:10]}",
        game=game,
        organizer=user,
        format=Tournament.BATTLE_ROYALE,
        participation_type="SOLO",
        max_participants=100,
        min_participants=2,
        registration_start=now,
        registration_end=now,
        tournament_start=now + timedelta(hours=1),
        is_featured=False,
        is_official=False,
    )
    lobby = RoyaleLobby.objects.create(
        tournament=tournament,
        game=game,
        title="Private Drop",
        slot_capacity=100,
        scheduled_at=now + timedelta(hours=1),
    )
    entry = RoyaleEntry.objects.create(lobby=lobby, user=user)

    client.force_login(outsider)
    response = client.get(f"/dashboard/competitive/dropzone/entries/{entry.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_mission_detail_visible_to_owner(client):
    game = GameFactory(short_code="MDA")
    user = UserFactory()
    template = ContractTemplate.objects.create(
        title="Clutch Mission",
        description="Win a focused match objective.",
        game=game,
        entry_fee_dc=10,
        reward_dc=40,
        goal_type="CUSTOM",
        goal_spec={"objective": "win"},
    )
    enrollment = ContractEnrollment.objects.create(
        user=user,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
        progress={"wins": 0},
    )

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/missions/{enrollment.id}/")

    assert response.status_code == 200
    assert b"Clutch Mission" in response.content
    assert b"Mission Progress" in response.content
    assert b"wins" in response.content.lower()


@pytest.mark.django_db
def test_mission_detail_blocks_unrelated_user(client):
    game = GameFactory(short_code="MDB")
    owner = UserFactory()
    outsider = UserFactory()
    template = ContractTemplate.objects.create(
        title="Private Mission",
        game=game,
        entry_fee_dc=10,
        reward_dc=40,
    )
    enrollment = ContractEnrollment.objects.create(
        user=owner,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
    )

    client.force_login(outsider)
    response = client.get(f"/dashboard/competitive/missions/{enrollment.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_dropzone_lobby_hides_room_credentials_before_reveal_and_links_entry(client):
    game = GameFactory(short_code="DLC")
    user = UserFactory()
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Lobby Detail Dropzone",
        slug=f"lobby-detail-dropzone-{uuid.uuid4().hex[:10]}",
        game=game,
        organizer=user,
        format=Tournament.BATTLE_ROYALE,
        participation_type="SOLO",
        max_participants=100,
        min_participants=2,
        registration_start=now,
        registration_end=now,
        tournament_start=now + timedelta(hours=3),
        is_featured=False,
        is_official=False,
    )
    lobby = RoyaleLobby.objects.create(
        tournament=tournament,
        game=game,
        title="Lobby Detail",
        slot_capacity=100,
        entry_fee_dc=25,
        scheduled_at=now + timedelta(hours=3),
        room_id="HIDDEN-ROOM",
        room_password="HIDDEN-PASS",
        prize_distribution={"mode": "PERCENT", "splits": {"1": 60}},
    )
    entry = RoyaleEntry.objects.create(lobby=lobby, user=user)

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/dropzone/lobbies/{lobby.id}/")

    assert response.status_code == 200
    assert b"Lobby Detail" in response.content
    assert f"/dashboard/competitive/dropzone/entries/{entry.id}/".encode() in response.content
    assert b"Room credentials unlock" in response.content
    assert b"HIDDEN-ROOM" not in response.content
    assert b"HIDDEN-PASS" not in response.content


@pytest.mark.django_db
def test_dropzone_lobby_results_table_appears_when_scores_exist(client):
    game = GameFactory(short_code="DLR")
    user = UserFactory()
    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Scored Dropzone",
        slug=f"scored-dropzone-{uuid.uuid4().hex[:10]}",
        game=game,
        organizer=user,
        format=Tournament.BATTLE_ROYALE,
        participation_type="SOLO",
        max_participants=100,
        min_participants=2,
        registration_start=now,
        registration_end=now,
        tournament_start=now - timedelta(hours=1),
        is_featured=False,
        is_official=False,
    )
    lobby = RoyaleLobby.objects.create(
        tournament=tournament,
        game=game,
        title="Scored Lobby",
        slot_capacity=100,
        scheduled_at=now - timedelta(hours=1),
        status="SCORING",
    )
    RoyaleEntry.objects.create(lobby=lobby, user=user, status="SCORED", placement=1, kills=8)

    client.force_login(user)
    response = client.get(f"/dashboard/competitive/dropzone/lobbies/{lobby.id}/")

    assert response.status_code == 200
    assert b"Placement" in response.content
    assert b"8" in response.content


@pytest.mark.django_db
def test_competitive_review_workspace_staff_only(client):
    user = UserFactory()
    client.force_login(user)

    response = client.get("/dashboard/competitive/review/")

    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_competitive_review_workspace_lists_pending_mission_proof(client):
    game = GameFactory(short_code="RVW")
    player = UserFactory()
    staff = UserFactory(is_staff=True)
    template = ContractTemplate.objects.create(
        title="Review Queue Mission",
        game=game,
        entry_fee_dc=0,
        reward_dc=40,
    )
    enrollment = ContractEnrollment.objects.create(
        user=player,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
    )
    ContractProofSubmission.objects.create(
        enrollment=enrollment,
        submitted_by=player,
        proof_url="https://example.com/review-proof.png",
        notes="Review this proof.",
    )

    client.force_login(staff)
    response = client.get("/dashboard/competitive/review/")

    assert response.status_code == 200
    assert b"Review Workspace" in response.content
    assert b"Review Queue Mission" in response.content
    assert b"Review Proof" in response.content


@pytest.mark.django_db
def test_mission_proof_file_owner_and_staff_can_view_but_unrelated_user_blocked(client):
    game = GameFactory(short_code="PFV")
    owner = UserFactory()
    staff = UserFactory(is_staff=True)
    outsider = UserFactory()
    template = ContractTemplate.objects.create(
        title="Private Proof Mission",
        game=game,
        entry_fee_dc=0,
        reward_dc=40,
    )
    enrollment = ContractEnrollment.objects.create(
        user=owner,
        template=template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
    )
    proof = ContractProofSubmission.objects.create(
        enrollment=enrollment,
        submitted_by=owner,
        proof_file=SimpleUploadedFile(
            "scoreboard.png",
            b"\x89PNG\r\n\x1a\n" + b"0" * 128,
            content_type="image/png",
        ),
    )
    url = f"/dashboard/competitive/proofs/{proof.id}/file/"

    client.force_login(owner)
    assert client.get(url).status_code == 200

    client.force_login(staff)
    assert client.get(url).status_code == 200

    client.force_login(outsider)
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_dispute_center_participant_sees_only_related_mission_proofs(client):
    game = GameFactory(short_code="DCP")
    owner = UserFactory()
    outsider = UserFactory()
    own_template = ContractTemplate.objects.create(title="Own Proof", game=game)
    other_template = ContractTemplate.objects.create(title="Other Proof", game=game)
    own_enrollment = ContractEnrollment.objects.create(
        user=owner,
        template=own_template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
    )
    other_enrollment = ContractEnrollment.objects.create(
        user=outsider,
        template=other_template,
        status="ACTIVE",
        deadline_at=timezone.now() + timedelta(hours=6),
    )
    ContractProofSubmission.objects.create(
        enrollment=own_enrollment,
        submitted_by=owner,
        proof_url="https://example.com/own.png",
    )
    ContractProofSubmission.objects.create(
        enrollment=other_enrollment,
        submitted_by=outsider,
        proof_url="https://example.com/other.png",
    )

    client.force_login(owner)
    response = client.get("/dashboard/competitive/disputes/")

    assert response.status_code == 200
    assert b"Own Proof" in response.content
    assert b"Other Proof" not in response.content


@pytest.mark.django_db
def test_match_room_proof_file_is_permission_checked(client):
    game = GameFactory(short_code="MPF")
    user = UserFactory()
    outsider = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.PLAYER)
    match = create_tournament_match(game=game, organizer=user, team=team, opponent=opponent)
    submission = MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=team.id,
        raw_result_payload={"winner_team_id": team.id},
        proof_screenshot=SimpleUploadedFile(
            "match-proof.png",
            b"\x89PNG\r\n\x1a\n" + b"1" * 128,
            content_type="image/png",
        ),
    )
    url = f"/dashboard/competitive/match-proofs/{submission.id}/file/"

    client.force_login(user)
    assert client.get(url).status_code == 200

    client.force_login(outsider)
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_dispute_center_participant_note_is_visible_and_internal_note_hidden(client):
    game = GameFactory(short_code="DNT")
    user = UserFactory()
    staff = UserFactory(is_staff=True)
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.PLAYER)
    match = create_tournament_match(game=game, organizer=user, team=team, opponent=opponent)
    submission = MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=team.id,
        raw_result_payload={"winner_team_id": team.id},
    )
    dispute = DisputeRecord.objects.create(
        submission=submission,
        opened_by_user=user,
        opened_by_team_id=team.id,
        reason_code=DisputeRecord.REASON_OTHER,
        description="Need review for proof mismatch.",
    )
    DisputeNote.objects.create(dispute=dispute, author=staff, body="Private operator note.", visibility="internal_staff")
    DisputeNote.objects.create(dispute=dispute, author=user, body="Participant clarification.", visibility="participant_safe")

    client.force_login(user)
    response = client.get("/dashboard/competitive/disputes/")

    assert response.status_code == 200
    assert b"Participant clarification" in response.content
    assert b"Private operator note" not in response.content


@pytest.mark.django_db
def test_dispute_evidence_and_match_media_file_routes_are_permission_checked(client):
    game = GameFactory(short_code="MEF")
    user = UserFactory()
    outsider = UserFactory()
    team = TeamFactory(game_id=game.id)
    opponent = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=team, user=user, role=MembershipRole.PLAYER)
    match = create_tournament_match(game=game, organizer=user, team=team, opponent=opponent)
    submission = MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=user,
        submitted_by_team_id=team.id,
        raw_result_payload={"winner_team_id": team.id},
    )
    dispute = DisputeRecord.objects.create(
        submission=submission,
        opened_by_user=user,
        opened_by_team_id=team.id,
        reason_code=DisputeRecord.REASON_OTHER,
        description="Evidence route test.",
    )
    evidence = DisputeEvidence.objects.create(
        dispute=dispute,
        uploaded_by=user,
        evidence_file=SimpleUploadedFile("evidence.png", b"\x89PNG\r\n\x1a\n" + b"2" * 128, content_type="image/png"),
    )
    media = MatchMedia.objects.create(
        match=match,
        uploaded_by_id=user.id,
        file=SimpleUploadedFile("media.png", b"\x89PNG\r\n\x1a\n" + b"3" * 128, content_type="image/png"),
        is_evidence=True,
    )

    client.force_login(user)
    assert client.get(f"/dashboard/competitive/dispute-evidence/{evidence.id}/file/").status_code == 200
    assert client.get(f"/dashboard/competitive/match-media/{media.id}/file/").status_code == 200

    client.force_login(outsider)
    assert client.get(f"/dashboard/competitive/dispute-evidence/{evidence.id}/file/").status_code == 404
    assert client.get(f"/dashboard/competitive/match-media/{media.id}/file/").status_code == 404
