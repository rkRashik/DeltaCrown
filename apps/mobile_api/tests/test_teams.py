"""Tests for mobile team endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.user_profile.models import GameProfile


User = get_user_model()


def create_game(**overrides):
    defaults = {
        "name": "Mobile Team Game",
        "display_name": "Mobile Team Game",
        "slug": "mobile-team-game",
        "short_code": "MTG",
        "category": "FPS",
        "game_type": "TEAM_VS_TEAM",
        "platforms": ["PC"],
        "is_active": True,
        "is_passport_supported": True,
    }
    defaults.update(overrides)
    return Game.objects.create(**defaults)


def create_passport(user, game):
    return GameProfile.objects.create(
        user=user,
        game=game,
        game_display_name=game.display_name,
        ign=f"{user.username}IGN",
        in_game_name=f"{user.username}IGN",
        identity_key=f"{user.username.lower()}ign",
    )


def create_team(owner, game, **overrides):
    defaults = {
        "name": "Mobile Squad",
        "slug": "mobile-squad",
        "tag": "MSQ",
        "game_id": game.id,
        "region": "Global",
        "created_by": owner,
        "status": TeamStatus.ACTIVE,
        "visibility": "PUBLIC",
        "is_recruiting": True,
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


class MobileTeamEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="teamuser",
            email="teamuser@example.com",
            password="testpass123!",
        )
        self.other_user = User.objects.create_user(
            username="otherteamuser",
            email="otherteamuser@example.com",
            password="testpass123!",
        )
        self.captain = User.objects.create_user(
            username="captain",
            email="captain@example.com",
            password="testpass123!",
        )
        self.game = create_game()
        create_passport(self.user, self.game)
        create_passport(self.other_user, self.game)
        create_passport(self.captain, self.game)
        self.team = create_team(self.captain, self.game)
        self.client.force_authenticate(self.user)

    def test_team_status_requires_auth(self):
        response = APIClient().get(reverse("mobile_api_v1:teams:team_status"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])

    def test_team_status_returns_only_current_users_teams(self):
        own = create_team(self.user, self.game, name="Own Squad", slug="own-squad", tag="OWN")
        create_team(self.other_user, self.game, name="Other Squad", slug="other-squad", tag="OTH")

        response = self.client.get(reverse("mobile_api_v1:teams:team_status"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        teams = [
            item["team"]["id"]
            for group in body["data"]["games"]
            for item in group["teams"]
        ]
        self.assertIn(own.id, teams)
        self.assertNotIn(self.team.id, teams)

    def test_teams_list_requires_auth_and_returns_mobile_envelope(self):
        response = APIClient().get(reverse("mobile_api_v1:teams:teams"))
        self.assertEqual(response.status_code, 401)

        response = self.client.get(reverse("mobile_api_v1:teams:teams"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        card = body["data"]["teams"][0]
        self.assertIn("name", card)
        self.assertIn("game", card)
        self.assertIn("user_relation", card)

    def test_team_detail_returns_mobile_safe_fields(self):
        response = self.client.get(reverse("mobile_api_v1:teams:team_detail", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["team"]["id"], self.team.id)
        self.assertIn("members", data)
        self.assertIn("permissions", data)
        self.assertNotIn("organization_id", data["team"])
        self.assertNotIn("created_by", data["team"])

    def test_create_team_success_if_rules_allow(self):
        response = self.client.post(
            reverse("mobile_api_v1:teams:team_create"),
            {
                "name": "Fresh Mobile Team",
                "tag": "FMT",
                "game": self.game.slug,
                "description": "Ready for tournaments.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        team_id = body["data"]["team"]["id"]
        self.assertTrue(
            TeamMembership.objects.filter(
                team_id=team_id,
                user=self.user,
                role=MembershipRole.OWNER,
                status=MembershipStatus.ACTIVE,
            ).exists()
        )

    def test_create_team_validation_error_for_duplicate_invalid_data(self):
        create_team(self.user, self.game, name="Taken Team", slug="taken-team", tag="TAK")

        response = self.client.post(
            reverse("mobile_api_v1:teams:team_create"),
            {"name": "Taken Team", "tag": "NEW", "game": self.game.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "validation_error")

    def test_apply_to_team_success(self):
        response = self.client.post(
            reverse("mobile_api_v1:teams:team_apply", args=[self.team.slug]),
            {"message": "I can flex."},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "created")
        self.assertTrue(
            TeamJoinRequest.objects.filter(
                team=self.team,
                user=self.user,
                status=TeamJoinRequest.Status.PENDING,
            ).exists()
        )

    def test_duplicate_apply_returns_existing_pending_state_safely(self):
        existing = TeamJoinRequest.objects.create(team=self.team, user=self.user, status=TeamJoinRequest.Status.PENDING)

        response = self.client.post(reverse("mobile_api_v1:teams:team_apply", args=[self.team.slug]), {}, format="json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "pending")
        self.assertEqual(body["data"]["join_request"]["id"], existing.id)

    def test_non_captain_cannot_accept_or_decline_join_request(self):
        join_request = TeamJoinRequest.objects.create(team=self.team, user=self.other_user)

        accept_response = self.client.post(
            reverse("mobile_api_v1:teams:team_request_accept", args=[self.team.slug, join_request.id]),
            {},
            format="json",
        )
        decline_response = self.client.post(
            reverse("mobile_api_v1:teams:team_request_decline", args=[self.team.slug, join_request.id]),
            {},
            format="json",
        )

        self.assertEqual(accept_response.status_code, 403)
        self.assertEqual(decline_response.status_code, 403)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TeamJoinRequest.Status.PENDING)

    def test_captain_can_accept_join_request(self):
        join_request = TeamJoinRequest.objects.create(team=self.team, user=self.user)
        self.client.force_authenticate(self.captain)

        response = self.client.post(
            reverse("mobile_api_v1:teams:team_request_accept", args=[self.team.slug, join_request.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TeamJoinRequest.Status.ACCEPTED)
        self.assertTrue(
            TeamMembership.objects.filter(team=self.team, user=self.user, status=MembershipStatus.ACTIVE).exists()
        )

    def test_captain_can_decline_join_request(self):
        join_request = TeamJoinRequest.objects.create(team=self.team, user=self.user)
        self.client.force_authenticate(self.captain)

        response = self.client.post(
            reverse("mobile_api_v1:teams:team_request_decline", args=[self.team.slug, join_request.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TeamJoinRequest.Status.DECLINED)

    def test_no_internal_fields_leak_in_payloads(self):
        response = self.client.get(reverse("mobile_api_v1:teams:teams"))

        self.assertEqual(response.status_code, 200)
        card = response.json()["data"]["teams"][0]
        self.assertNotIn("organization_id", card)
        self.assertNotIn("created_by_id", card)
        self.assertNotIn("discord_webhook_url", card)
