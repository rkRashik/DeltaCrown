from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.user_profile.models import UserProfile
from apps.tournaments.models import Tournament, Registration, Match
from apps.game_valorant.models import ValorantConfig
from apps.teams.models import Team
from apps.corelib.brackets import generate_bracket, admin_set_winner

class BracketBasicsTests(TestCase):
    def setUp(self):
        # 3 teams (odd count → one BYE), 2 confirmed, 1 pending
        self.u1 = User.objects.create_user(username="c1")
        self.u2 = User.objects.create_user(username="c2")
        self.u3 = User.objects.create_user(username="c3")
        p1 = getattr(self.u1, "profile", None) or UserProfile.objects.create(user=self.u1, display_name="C1")
        p2 = getattr(self.u2, "profile", None) or UserProfile.objects.create(user=self.u2, display_name="C2")
        p3 = getattr(self.u3, "profile", None) or UserProfile.objects.create(user=self.u3, display_name="C3")
        self.tA = Team.objects.create(name="Alpha", tag="ALP", captain=p1)
        self.tB = Team.objects.create(name="Bravo", tag="BRV", captain=p2)
        self.tC = Team.objects.create(name="Charlie", tag="CHL", captain=p3)

        now = timezone.now()
        self.t = Tournament.objects.create(
            name="LAN Valo", slug="lan-valo",
            reg_open_at=now - timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
            slot_size=8, entry_fee_bdt=0, prize_pool_bdt=0,
        )
        ValorantConfig.objects.create(tournament=self.t, best_of="BO3", rounds_per_match=13)

        # Only ALP & BRV are confirmed → bracket capacity = 2 (power-of-two of 2)
        Registration.objects.create(tournament=self.t, team=self.tA, status="CONFIRMED", payment_status="verified")
        Registration.objects.create(tournament=self.t, team=self.tB, status="CONFIRMED", payment_status="verified")
        Registration.objects.create(tournament=self.t, team=self.tC, status="PENDING", payment_status="pending")

    def test_generate_and_propagate(self):
        generate_bracket(self.t)
        # Rounds: with 2 confirmed, capacity=2 => 1 round (final)
        m = Match.objects.get(tournament=self.t, round_no=1, position=1)
        # Set winner A and ensure no crash
        admin_set_winner(m, who="a")
        m.refresh_from_db()
        self.assertTrue(m.winner_team_id in [self.tA.id, self.tB.id])
        self.assertEqual(m.state, "VERIFIED")
