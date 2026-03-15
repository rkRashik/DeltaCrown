from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.games.models import Game
from apps.tournaments.models import Match, MatchResultSubmission, Tournament
from apps.user_profile.models import GameOAuthConnection, GameProfile
from apps.user_profile.tasks import _ingest_riot_snapshot, _sync_single_passport


@pytest.fixture
def riot_sync_context(db, django_user_model):
    user = django_user_model.objects.create_user(
        username="riot_player",
        email="riot_player@example.com",
        password="pass1234",
    )
    opponent = django_user_model.objects.create_user(
        username="riot_opponent",
        email="riot_opponent@example.com",
        password="pass1234",
    )

    game = Game.objects.create(
        name="Valorant",
        display_name="Valorant",
        slug="valorant",
        short_code="VAL",
        category="FPS",
        platforms=["PC"],
        is_passport_supported=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name="Riot Ingestion Cup",
        slug="riot-ingestion-cup",
        description="Test tournament",
        organizer=user,
        game=game,
        registration_start=now,
        registration_end=now,
        tournament_start=now,
    )

    match = Match.objects.create(
        tournament=tournament,
        bracket=None,
        round_number=1,
        match_number=1,
        participant1_id=user.id,
        participant1_name=user.username,
        participant2_id=opponent.id,
        participant2_name=opponent.username,
        state=Match.LIVE,
        scheduled_time=now,
    )

    passport = GameProfile.objects.create(
        user=user,
        game=game,
        game_display_name=game.display_name,
        ign="riot_player",
        in_game_name="riot_player#AP1",
        identity_key="riot_player#ap1",
        status=GameProfile.STATUS_ACTIVE,
        verification_status=GameProfile.VERIFICATION_VERIFIED,
        metadata={"riot_puuid": "puuid-1", "riot_region": "ap"},
    )

    GameOAuthConnection.objects.create(
        passport=passport,
        provider=GameOAuthConnection.Provider.RIOT,
        provider_account_id="puuid-1",
        game_shard="ap",
    )

    return {
        "user": user,
        "opponent": opponent,
        "match": match,
        "passport": passport,
    }


@pytest.mark.django_db
def test_ingest_riot_snapshot_creates_canonical_submission_and_calls_finalization(riot_sync_context):
    passport = riot_sync_context["passport"]
    match = riot_sync_context["match"]
    user = riot_sync_context["user"]

    snapshot = {
        "match_id": "riot-match-1",
        "kills": 17,
        "deaths": 9,
        "assists": 5,
        "character_id": "jett",
        "won": True,
        "duration_seconds": 1800,
        "game_start_millis": int(timezone.now().timestamp() * 1000),
    }

    mock_service = Mock()
    mock_service.finalize_submission_with_verification.side_effect = (
        lambda submission_id, resolved_by_user_id: SimpleNamespace(
            id=submission_id,
            match_id=match.id,
        )
    )

    with patch(
        "apps.tournament_ops.services.tournament_ops_service.get_tournament_ops_service",
        return_value=mock_service,
    ):
        result = _ingest_riot_snapshot(
            passport=passport,
            snapshot=snapshot,
            source_region="ap",
            system_actor_id=user.id,
        )

    assert result["status"] == "finalized"

    submission = MatchResultSubmission.objects.get(id=result["submission_id"])
    assert submission.match_id == match.id
    assert submission.source == "riot_api"
    assert submission.status == MatchResultSubmission.STATUS_AUTO_CONFIRMED
    assert submission.ingestion_fingerprint == f"riot:ap:{snapshot['match_id']}:{match.id}"

    payload = submission.raw_result_payload
    assert payload["winner_team_id"] == user.id
    assert payload["loser_team_id"] == riot_sync_context["opponent"].id

    mock_service.finalize_submission_with_verification.assert_called_once_with(
        submission_id=submission.id,
        resolved_by_user_id=user.id,
    )


@pytest.mark.django_db
def test_sync_single_passport_does_not_persist_projection_without_finalization(riot_sync_context, settings):
    passport = riot_sync_context["passport"]

    settings.RIOT_RESULT_INGESTION_ENABLED = True

    history_payload = {"match_ids": ["riot-match-1"]}
    details_payload = {
        "match_id": "riot-match-1",
        "match_info": {
            "game_length_millis": 1200000,
            "game_start_millis": int(timezone.now().timestamp() * 1000),
        },
        "scoreboard": [
            {
                "puuid": "puuid-1",
                "team_id": "Blue",
                "kills": 12,
                "deaths": 8,
                "assists": 4,
                "character_id": "jett",
            }
        ],
        "teams": [
            {"teamId": "Blue", "won": True},
            {"teamId": "Red", "won": False},
        ],
    }

    with patch(
        "apps.user_profile.tasks._call_riot_with_retry",
        side_effect=[history_payload, details_payload],
    ), patch(
        "apps.user_profile.tasks._ingest_riot_snapshot",
        return_value={"status": "unmatched"},
    ), patch("apps.user_profile.tasks._persist_sync_result") as mock_persist:
        result = _sync_single_passport(passport)

    assert result["status"] == "skipped"
    assert result["reason"] == "no_finalized_submissions"
    assert result["canonical_ingestion"]["unmatched"] == 1
    mock_persist.assert_not_called()
