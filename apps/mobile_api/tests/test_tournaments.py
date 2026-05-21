"""Tests for mobile tournament endpoints."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.tournaments.models import Registration, Tournament
from apps.user_profile.models import GameProfile, UserProfile


User = get_user_model()


def create_game(**overrides):
    defaults = {
        "name": "Mobile Tournament Game",
        "display_name": "Mobile Tournament Game",
        "slug": "mobile-tournament-game",
        "short_code": "MTG",
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
        "name": "Mobile Cup",
        "slug": "mobile-cup",
        "organizer": organizer,
        "game": game,
        "format": Tournament.SINGLE_ELIM,
        "participation_type": Tournament.SOLO,
        "platform": Tournament.PC,
        "mode": Tournament.ONLINE,
        "max_participants": 16,
        "min_participants": 2,
        "registration_start": now - timedelta(days=1),
        "registration_end": now + timedelta(days=2),
        "tournament_start": now + timedelta(days=5),
        "status": Tournament.REGISTRATION_OPEN,
        "prize_pool": Decimal("1000.00"),
        "prize_currency": "BDT",
        "has_entry_fee": False,
    }
    defaults.update(overrides)
    return Tournament.objects.create(**defaults)


def create_passport(user, game):
    return GameProfile.objects.create(
        user=user,
        game=game,
        game_display_name=game.display_name,
        ign=f"{user.username}IGN",
        in_game_name=f"{user.username}IGN",
        identity_key=f"{user.username.lower()}ign",
    )


class MobileTournamentEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="touruser",
            email="touruser@example.com",
            password="testpass123!",
        )
        self.other_user = User.objects.create_user(
            username="othertouruser",
            email="othertour@example.com",
            password="testpass123!",
        )
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123!",
        )
        self.game = create_game()
        self.tournament = create_tournament(self.organizer, self.game)
        self.client.force_authenticate(self.user)

    def test_tournament_list_requires_auth(self):
        response = APIClient().get(reverse("mobile_api_v1:tournaments:tournaments"))

        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "not_authenticated")

    def test_tournament_list_returns_mobile_envelope_and_cards(self):
        response = self.client.get(reverse("mobile_api_v1:tournaments:tournaments"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        card = body["data"]["tournaments"][0]
        self.assertEqual(card["id"], self.tournament.id)
        self.assertEqual(card["slug"], "mobile-cup")
        self.assertEqual(card["game"]["id"], self.game.id)
        self.assertIn("capacity", card)
        self.assertIn("entry_fee", card)
        self.assertIn("prize", card)
        self.assertNotIn("organizer_id", card)
        self.assertNotIn("config", card)

    def test_tournament_detail_returns_eligibility_block(self):
        create_passport(self.user, self.game)
        response = self.client.get(
            reverse("mobile_api_v1:tournaments:tournament_detail", args=[self.tournament.slug])
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        eligibility = body["data"]["eligibility"]
        self.assertTrue(eligibility["can_join"])
        self.assertEqual(eligibility["status"], "joinable")
        self.assertEqual(eligibility["next_action"], "join")
        self.assertNotIn("organizer_id", body["data"])
        self.assertNotIn("config", body["data"])

    def test_tournament_detail_unknown_id_or_slug_returns_mobile_404_envelope(self):
        response = self.client.get(reverse("mobile_api_v1:tournaments:tournament_detail", args=["missing-cup"]))

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "not_found")

    def test_join_rejects_closed_tournament(self):
        create_passport(self.user, self.game)
        self.tournament.status = Tournament.REGISTRATION_CLOSED
        self.tournament._skip_status_validation = True
        self.tournament.save(update_fields=["status"])

        response = self.client.post(
            reverse("mobile_api_v1:tournaments:tournament_join", args=[self.tournament.slug]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["joined"])
        self.assertEqual(body["data"]["eligibility"]["status"], "closed")

    def test_join_rejects_duplicate_registration_safely(self):
        create_passport(self.user, self.game)
        existing = Registration.objects.create(
            tournament=self.tournament,
            user=self.user,
            status=Registration.PENDING,
        )

        response = self.client.post(
            reverse("mobile_api_v1:tournaments:tournament_join", args=[self.tournament.slug]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["joined"])
        self.assertEqual(body["data"]["registration"]["id"], existing.id)
        self.assertEqual(body["data"]["eligibility"]["status"], "already_joined")

    def test_join_returns_game_passport_requirement(self):
        response = self.client.post(
            reverse("mobile_api_v1:tournaments:tournament_join", args=[self.tournament.slug]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["joined"])
        self.assertEqual(body["data"]["eligibility"]["status"], "game_passport_required")
        self.assertEqual(body["data"]["eligibility"]["next_action"], "add_game_passport")

    def test_join_returns_profile_requirement_when_profile_missing(self):
        UserProfile.objects.filter(user=self.user).delete()

        response = self.client.post(
            reverse("mobile_api_v1:tournaments:tournament_join", args=[self.tournament.slug]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["eligibility"]["status"], "profile_required")
        self.assertEqual(body["data"]["eligibility"]["next_action"], "complete_profile")

    def test_me_tournaments_returns_only_current_users_registrations(self):
        own = Registration.objects.create(
            tournament=self.tournament,
            user=self.user,
            status=Registration.CONFIRMED,
        )
        Registration.objects.create(
            tournament=self.tournament,
            user=self.other_user,
            status=Registration.CONFIRMED,
        )

        response = self.client.get(reverse("mobile_api_v1:tournaments:my_tournaments"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        registrations = body["data"]["registrations"]
        self.assertEqual(len(registrations), 1)
        self.assertEqual(registrations[0]["registration"]["id"], own.id)
        self.assertEqual(registrations[0]["tournament"]["id"], self.tournament.id)

    def test_join_success_creates_registration_for_joinable_solo_tournament(self):
        create_passport(self.user, self.game)

        response = self.client.post(
            reverse("mobile_api_v1:tournaments:tournament_join", args=[self.tournament.slug]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["data"]["joined"])
        self.assertEqual(body["data"]["registration"]["status"], Registration.PENDING)
        self.assertTrue(Registration.objects.filter(tournament=self.tournament, user=self.user).exists())
