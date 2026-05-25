import uuid

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.organizations.services.team_detail_context import get_team_detail_context
from apps.organizations.tests.factories import GameFactory, TeamFactory, UserFactory
from apps.tournaments.models import Match, Registration, Tournament


class TeamDetailRegistrationMatchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.game = GameFactory()
        self.owner = UserFactory(username=f"tdrm_owner_{uuid.uuid4().hex[:8]}")
        self.opponent_owner = UserFactory(username=f"tdrm_opp_owner_{uuid.uuid4().hex[:8]}")
        self.team = TeamFactory.create_independent(
            created_by=self.owner,
            game_id=self.game.id,
            name=f"Registration Match Team {uuid.uuid4().hex[:8]}",
        )
        self.opponent = TeamFactory.create_independent(
            created_by=self.opponent_owner,
            game_id=self.game.id,
            name=f"Registration Opponent {uuid.uuid4().hex[:8]}",
        )
        self.tournament = self._make_tournament()

    def _make_tournament(self):
        now = timezone.now()
        return Tournament.objects.create(
            name=f"Registration Match Cup {uuid.uuid4().hex[:8]}",
            slug=f"registration-match-cup-{uuid.uuid4().hex[:12]}",
            organizer=UserFactory(username=f"tdrm_organizer_{uuid.uuid4().hex[:8]}"),
            game=self.game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=2),
            registration_end=now + timezone.timedelta(days=1),
            tournament_start=now + timezone.timedelta(days=2),
        )

    def _register(self, team):
        return Registration.objects.create(
            tournament=self.tournament,
            team_id=team.id,
            status=Registration.CONFIRMED,
        )

    def test_upcoming_matches_include_registration_participant_ids(self):
        team_reg = self._register(self.team)
        opponent_reg = self._register(self.opponent)
        Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            participant1_id=team_reg.id,
            participant1_name="Old Team Name",
            participant2_id=opponent_reg.id,
            participant2_name="Old Opponent Name",
            state=Match.SCHEDULED,
            scheduled_time=timezone.now() + timezone.timedelta(hours=2),
        )

        context = get_team_detail_context(team_slug=self.team.slug)

        self.assertEqual(len(context["upcoming_matches"]), 1)
        self.assertEqual(context["upcoming_matches"][0]["opponent_name"], self.opponent.name)

    def test_match_history_includes_completed_registration_participant_ids(self):
        team_reg = self._register(self.team)
        opponent_reg = self._register(self.opponent)
        Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=2,
            participant1_id=team_reg.id,
            participant1_name="Old Team Name",
            participant2_id=opponent_reg.id,
            participant2_name="Old Opponent Name",
            state=Match.COMPLETED,
            participant1_score=2,
            participant2_score=1,
            winner_id=team_reg.id,
            loser_id=opponent_reg.id,
        )

        context = get_team_detail_context(team_slug=self.team.slug)

        self.assertEqual(len(context["match_history"]), 1)
        match = context["match_history"][0]
        self.assertEqual(match["opponent_name"], self.opponent.name)
        self.assertEqual(match["result"], "win")
        self.assertEqual(match["score"], "2-1")

    def test_direct_team_id_matches_still_appear(self):
        Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=3,
            participant1_id=self.team.id,
            participant1_name=self.team.name,
            participant2_id=self.opponent.id,
            participant2_name=self.opponent.name,
            state=Match.COMPLETED,
            participant1_score=3,
            participant2_score=0,
            winner_id=self.team.id,
            loser_id=self.opponent.id,
        )

        context = get_team_detail_context(team_slug=self.team.slug)

        self.assertEqual(len(context["match_history"]), 1)
        self.assertEqual(context["match_history"][0]["opponent_name"], self.opponent.name)
        self.assertEqual(context["match_history"][0]["score"], "3-0")

    def test_empty_registration_team_does_not_crash(self):
        context = get_team_detail_context(team_slug=self.team.slug)

        self.assertIsInstance(context["upcoming_matches"], list)
        self.assertIsInstance(context["match_history"], list)
        self.assertIsInstance(context["operations_log"], list)
