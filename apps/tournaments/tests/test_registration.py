# apps/tournaments/tests/test_registration.py
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, Registration
from apps.game_valorant.models import ValorantConfig
from apps.game_efootball.models import EfootballConfig
from apps.teams.models import Team

User = get_user_model()

class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _ensure_profile(self, user):
        # If signals didn’t run for any reason, create a profile on the fly.
        if not hasattr(user, "profile"):
            from apps.user_profile.models import UserProfile
            UserProfile.objects.create(user=user, display_name=user.username)
        return user.profile

    def test_team_paid_registration_flow(self):
        # Login captain
        u = User.objects.create_user(username="capt", password="x")
        self.client.login(username="capt", password="x")
        profile = self._ensure_profile(u)

        # Paid Valorant tournament with window open
        now = timezone.now()
        t = Tournament.objects.create(
            name="Cup Valo",
            slug="cup-valo",
            reg_open_at=now - timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
            slot_size=8,
            prize_pool_bdt=0,
            entry_fee_bdt=100,
        )
        ValorantConfig.objects.create(tournament=t, best_of="BO3", rounds_per_match=13)

        # Captain's team
        team = Team.objects.create(name="Alpha", tag="ALP", captain=profile)

        url = reverse("tournaments:register", args=[t.slug])

        # POST without payment -> form re-renders (status 200)
        resp = self.client.post(url, data={"team": team.id})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            Registration.objects.filter(tournament=t, team=team).exists()
        )

        # POST with payment -> registration row created (pending)
        resp = self.client.post(
            url,
            data={"team": team.id, "payment_method": "bkash", "payment_reference": "TXN123"},
        )
        self.assertIn(resp.status_code, (302, 303))  # redirect to success
        self.assertTrue(
            Registration.objects.filter(
                tournament=t, team=team, payment_status="pending"
            ).exists()
        )

    def test_solo_free_registration_flow(self):
        # Login player
        u = User.objects.create_user(username="p1", password="x")
        self.client.login(username="p1", password="x")
        self._ensure_profile(u)

        # Free eFootball tournament
        now = timezone.now()
        t = Tournament.objects.create(
            name="Open eFootball",
            slug="open-efootball",
            reg_open_at=now - timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
            slot_size=4,
            entry_fee_bdt=0,
        )
        EfootballConfig.objects.create(tournament=t, format_type="BO1", match_duration_min=10)

        url = reverse("tournaments:register", args=[t.slug])

        # Free path -> no payment fields required
        resp = self.client.post(url, data={})
        self.assertIn(resp.status_code, (302, 303))  # redirected to success
        self.assertTrue(
            Registration.objects.filter(tournament=t, user=u.profile).exists()
        )
