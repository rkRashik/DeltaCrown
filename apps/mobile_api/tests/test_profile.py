"""Tests for mobile profile and game passport endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GameProfile, UserProfile


User = get_user_model()


def create_game(**overrides):
    defaults = {
        "name": "Valorant",
        "display_name": "VALORANT",
        "slug": "valorant",
        "short_code": "VAL",
        "category": "FPS",
        "game_type": "TEAM_VS_TEAM",
        "platforms": ["PC"],
        "is_active": True,
        "is_passport_supported": True,
    }
    defaults.update(overrides)
    return Game.objects.create(**defaults)


class MobileProfileEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="testpass123!",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("mobile_api_v1:profile:profile")

    def test_profile_get_authenticated(self):
        profile = self.user.profile
        profile.display_name = "Mobile Player"
        profile.real_full_name = "Mobile Player Real"
        profile.city = "Dhaka"
        profile.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["display_name"], "Mobile Player")
        self.assertEqual(data["real_full_name"], "Mobile Player Real")
        self.assertEqual(data["city"], "Dhaka")
        self.assertIn("avatar_url", data)
        self.assertIn("completion_percentage", data)
        self.assertIn("profile_completed", data)

    def test_profile_get_missing_profile_returns_safe_defaults(self):
        UserProfile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIsNone(data["display_name"])
        self.assertIsNone(data["public_id"])
        self.assertEqual(data["completion_percentage"], 0)
        self.assertFalse(data["profile_completed"])

    def test_profile_patch_updates_allowed_field(self):
        response = self.client.patch(self.url, {"display_name": "Updated Mobile"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, "Updated Mobile")

    def test_profile_patch_rejects_unsafe_admin_only_field(self):
        response = self.client.patch(self.url, {"kyc_status": "verified"}, format="json")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertIn("kyc_status", body["error"]["details"]["fields"])


class MobileGamesEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="gamesuser",
            email="games@example.com",
            password="testpass123!",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("mobile_api_v1:profile:games")

    def test_games_list_returns_active_games(self):
        active = create_game()
        create_game(
            name="Inactive Game",
            display_name="Inactive Game",
            slug="inactive-game",
            short_code="INACT",
            is_active=False,
        )
        GamePlayerIdentityConfig.objects.create(
            game=active,
            field_name="ign",
            display_name="In-Game Name",
            is_required=True,
            min_length=3,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        games = body["data"]["games"]
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], active.id)
        self.assertEqual(games[0]["slug"], "valorant")
        self.assertEqual(games[0]["identity_fields"][0]["field_name"], "ign")


class MobileGamePassportEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="passportuser",
            email="passport@example.com",
            password="testpass123!",
        )
        self.other_user = User.objects.create_user(
            username="otherpassport",
            email="otherpassport@example.com",
            password="testpass123!",
        )
        self.client.force_authenticate(self.user)
        self.game = create_game()
        GamePlayerIdentityConfig.objects.create(
            game=self.game,
            field_name="ign",
            display_name="In-Game Name",
            is_required=True,
            min_length=3,
        )
        self.list_url = reverse("mobile_api_v1:profile:game_passports")

    def test_game_passports_list_returns_only_current_user_passports(self):
        own = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            game_display_name=self.game.display_name,
            ign="OwnPlayer",
            in_game_name="OwnPlayer",
            identity_key="ownplayer",
        )
        GameProfile.objects.create(
            user=self.other_user,
            game=self.game,
            game_display_name=self.game.display_name,
            ign="OtherPlayer",
            in_game_name="OtherPlayer",
            identity_key="otherplayer",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        passports = body["data"]["game_passports"]
        self.assertEqual(len(passports), 1)
        self.assertEqual(passports[0]["id"], own.id)
        self.assertEqual(passports[0]["ign"], "OwnPlayer")

    def test_create_game_passport_success(self):
        response = self.client.post(
            self.list_url,
            {
                "game_id": self.game.id,
                "ign": "NewPlayer",
                "region": "NA",
                "visibility": "PUBLIC",
                "is_lft": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["ign"], "NewPlayer")
        self.assertTrue(body["data"]["is_lft"])
        self.assertTrue(GameProfile.objects.filter(user=self.user, game=self.game).exists())

    def test_create_game_passport_validation_error(self):
        response = self.client.post(
            self.list_url,
            {"game_id": self.game.id, "ign": "ab"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertIn("ign", body["error"]["details"])

    def test_update_cannot_modify_another_users_passport(self):
        other_passport = GameProfile.objects.create(
            user=self.other_user,
            game=self.game,
            game_display_name=self.game.display_name,
            ign="OtherPlayer",
            in_game_name="OtherPlayer",
            identity_key="otherplayer",
        )
        url = reverse("mobile_api_v1:profile:game_passport_detail", args=[other_passport.id])

        response = self.client.patch(url, {"ign": "StolenName"}, format="json")

        self.assertEqual(response.status_code, 404)
        other_passport.refresh_from_db()
        self.assertEqual(other_passport.ign, "OtherPlayer")

    def test_delete_cannot_delete_another_users_passport(self):
        other_passport = GameProfile.objects.create(
            user=self.other_user,
            game=self.game,
            game_display_name=self.game.display_name,
            ign="OtherPlayer",
            in_game_name="OtherPlayer",
            identity_key="otherplayer",
        )
        url = reverse("mobile_api_v1:profile:game_passport_detail", args=[other_passport.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(GameProfile.objects.filter(id=other_passport.id).exists())

    def test_delete_own_passport_requires_existing_otp_flow(self):
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            game_display_name=self.game.display_name,
            ign="OwnPlayer",
            in_game_name="OwnPlayer",
            identity_key="ownplayer",
        )
        url = reverse("mobile_api_v1:profile:game_passport_detail", args=[passport.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "otp_required")
        self.assertTrue(GameProfile.objects.filter(id=passport.id).exists())
