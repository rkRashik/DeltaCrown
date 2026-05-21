"""Tests for mobile match endpoints."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.tournaments.models import Match, MatchResultSubmission, Tournament


User = get_user_model()


def create_game(**overrides):
    defaults = {
        "name": "Mobile Match Game",
        "display_name": "Mobile Match Game",
        "slug": "mobile-match-game",
        "short_code": "MMG",
        "category": "FPS",
        "game_type": "TEAM_VS_TEAM",
        "platforms": ["PC"],
        "is_active": True,
        "is_passport_supported": True,
    }
    defaults.update(overrides)
    return Game.objects.create(**defaults)


def create_tournament(organizer, game, **overrides):
    now = timezone.now()
    defaults = {
        "name": "Mobile Match Cup",
        "slug": "mobile-match-cup",
        "organizer": organizer,
        "game": game,
        "format": Tournament.SINGLE_ELIM,
        "participation_type": Tournament.SOLO,
        "platform": Tournament.PC,
        "mode": Tournament.ONLINE,
        "max_participants": 16,
        "min_participants": 2,
        "registration_start": now - timedelta(days=3),
        "registration_end": now - timedelta(days=1),
        "tournament_start": now + timedelta(hours=1),
        "status": Tournament.LIVE,
        "prize_pool": Decimal("0.00"),
        "has_entry_fee": False,
    }
    defaults.update(overrides)
    return Tournament.objects.create(**defaults)


def create_match(tournament, user, opponent, **overrides):
    defaults = {
        "tournament": tournament,
        "round_number": 1,
        "match_number": 1,
        "participant1_id": user.id,
        "participant1_name": user.username,
        "participant2_id": opponent.id,
        "participant2_name": opponent.username,
        "state": Match.LIVE,
        "scheduled_time": timezone.now() - timedelta(minutes=5),
        "lobby_info": {"map": "Haven", "lobby_code": "ABC123", "admin_notes": "hidden"},
    }
    defaults.update(overrides)
    return Match.objects.create(**defaults)


def create_team(owner, game, **overrides):
    defaults = {
        "name": "Match Team",
        "slug": "match-team",
        "tag": "MTM",
        "game_id": game.id,
        "region": "Global",
        "created_by": owner,
        "status": TeamStatus.ACTIVE,
        "visibility": "PUBLIC",
    }
    defaults.update(overrides)
    team = Team.objects.create(**defaults)
    TeamMembership.objects.create(
        team=team,
        user=owner,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
        is_tournament_captain=True,
    )
    return team


class MobileMatchEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("matchuser", "matchuser@example.com", "testpass123!")
        self.opponent = User.objects.create_user("opponent", "opponent@example.com", "testpass123!")
        self.unrelated = User.objects.create_user("unrelated", "unrelated@example.com", "testpass123!")
        self.organizer = User.objects.create_user("matchorg", "matchorg@example.com", "testpass123!")
        self.game = create_game()
        self.tournament = create_tournament(self.organizer, self.game)
        self.match = create_match(self.tournament, self.user, self.opponent)
        self.client.force_authenticate(self.user)

    def test_me_matches_requires_auth(self):
        response = APIClient().get(reverse("mobile_api_v1:matches:my_matches"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])

    def test_me_matches_returns_only_current_users_matches(self):
        create_match(
            self.tournament,
            self.opponent,
            self.unrelated,
            match_number=2,
            participant1_name=self.opponent.username,
            participant2_name=self.unrelated.username,
        )

        response = self.client.get(reverse("mobile_api_v1:matches:my_matches"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        ids = [item["id"] for item in body["data"]["matches"]]
        self.assertEqual(ids, [self.match.id])

    def test_match_detail_rejects_unrelated_user(self):
        self.client.force_authenticate(self.unrelated)

        response = self.client.get(reverse("mobile_api_v1:matches:match_detail", args=[self.match.id]))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])

    def test_match_detail_returns_mobile_safe_fields_for_participant(self):
        response = self.client.get(reverse("mobile_api_v1:matches:match_detail", args=[self.match.id]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["id"], self.match.id)
        self.assertEqual(data["user_side"]["id"], self.user.id)
        self.assertEqual(data["opponent_side"]["id"], self.opponent.id)
        self.assertNotIn("organizer_id", data["tournament"])
        self.assertNotIn("lobby_info", data)

    def test_lobby_rejects_unrelated_user(self):
        self.client.force_authenticate(self.unrelated)

        response = self.client.get(reverse("mobile_api_v1:matches:match_lobby", args=[self.match.id]))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])

    def test_lobby_returns_mobile_envelope_for_participant(self):
        response = self.client.get(reverse("mobile_api_v1:matches:match_lobby", args=[self.match.id]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["lobby_info"]["lobby_code"], "ABC123")
        self.assertNotIn("admin_notes", body["data"]["lobby_info"])

    def test_check_in_rejects_unrelated_user(self):
        self.match.state = Match.CHECK_IN
        self.match.check_in_deadline = timezone.now() + timedelta(minutes=10)
        self.match.save(update_fields=["state", "check_in_deadline"])
        self.client.force_authenticate(self.unrelated)

        response = self.client.post(reverse("mobile_api_v1:matches:match_check_in", args=[self.match.id]), {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.match.refresh_from_db()
        self.assertFalse(self.match.participant1_checked_in)

    def test_check_in_respects_existing_status_timing_rules(self):
        self.match.state = Match.SCHEDULED
        self.match.check_in_deadline = timezone.now() + timedelta(minutes=10)
        self.match.save(update_fields=["state", "check_in_deadline"])

        response = self.client.post(reverse("mobile_api_v1:matches:match_check_in", args=[self.match.id]), {}, format="json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "invalid_state")

    def test_submit_result_rejects_unrelated_user(self):
        self.client.force_authenticate(self.unrelated)

        response = self.client.post(
            reverse("mobile_api_v1:matches:match_submit_result", args=[self.match.id]),
            {"result_payload": {"score_for": 2, "score_against": 1}},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MatchResultSubmission.objects.filter(match=self.match).exists())

    def test_submit_result_creates_pending_result_state_when_allowed(self):
        response = self.client.post(
            reverse("mobile_api_v1:matches:match_submit_result", args=[self.match.id]),
            {
                "result_payload": {"score_for": 2, "score_against": 1},
                "score": {"for": 2, "against": 1},
                "notes": "GG",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        submission = MatchResultSubmission.objects.get(match=self.match)
        self.assertEqual(submission.status, MatchResultSubmission.STATUS_PENDING)
        self.assertEqual(submission.submitted_by_user, self.user)
        self.match.refresh_from_db()
        self.assertEqual(self.match.state, Match.PENDING_RESULT)

    def test_upload_proof_handles_proof_url_safely(self):
        response = self.client.post(
            reverse("mobile_api_v1:matches:match_upload_proof", args=[self.match.id]),
            {"proof_url": "https://example.com/proof.png"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["submission"]["proof_url"], "https://example.com/proof.png")
        self.assertIn("multipart", body["data"]["note"])

    def test_status_endpoint_returns_lightweight_status(self):
        response = self.client.get(reverse("mobile_api_v1:matches:match_status", args=[self.match.id]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["match_id"], self.match.id)
        self.assertEqual(body["data"]["match_status"], Match.LIVE)
        self.assertIn("next_action", body["data"])

    def test_team_member_can_access_team_match(self):
        team = create_team(self.user, self.game)
        team_match = create_match(
            self.tournament,
            self.user,
            self.opponent,
            participant1_id=team.id,
            participant1_name=team.name,
            match_number=3,
        )

        response = self.client.get(reverse("mobile_api_v1:matches:match_detail", args=[team_match.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_no_organizer_admin_internal_fields_leak(self):
        response = self.client.get(reverse("mobile_api_v1:matches:match_lobby", args=[self.match.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertNotIn("organizer_id", payload["match"]["tournament"])
        self.assertNotIn("config", payload)
        self.assertNotIn("admin_notes", payload["lobby_info"])
