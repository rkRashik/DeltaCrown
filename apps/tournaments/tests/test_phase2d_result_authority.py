import inspect
import uuid
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership, Team
from apps.organizations.tests.factories import (
    GameFactory,
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.tournaments.api import matches as matches_api
from apps.tournaments.api.matches import IsParticipant
from apps.tournaments.api.result_views import ResultViewSet
from apps.tournaments.models import Match, Registration, Tournament
from apps.tournaments.services.match_authority import resolve_participant_side, user_can_act_for_match
from apps.tournaments.views.result_submission import SubmitResultView, report_dispute


class Phase2DMatchAuthorityTests(TestCase):
    def make_tournament(self, game, participation_type=Tournament.TEAM):
        now = timezone.now()
        return Tournament.objects.create(
            name=f"Phase 2D Cup {uuid.uuid4().hex[:8]}",
            slug=f"phase-2d-cup-{uuid.uuid4().hex[:10]}",
            organizer=UserFactory(),
            game=game,
            participation_type=participation_type,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=2),
            registration_end=now - timezone.timedelta(days=1),
            tournament_start=now + timezone.timedelta(days=1),
        )

    def make_match(self, team, *, participant_id=None):
        game = GameFactory()
        if team.game_id != game.id:
            team.game_id = game.id
            team.save(update_fields=["game_id"])
        tournament = self.make_tournament(game)
        return Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=participant_id or team.id,
            participant1_name=team.name,
            state=Match.PENDING_RESULT,
        )

    def make_independent_team(self, *, with_creator_membership=True):
        creator = UserFactory()
        team = TeamFactory.create_independent(created_by=creator)
        if with_creator_membership:
            TeamMembershipFactory(team=team, user=creator, role=MembershipRole.OWNER)
        return team, creator

    def test_user_can_act_for_match_allows_team_owner(self):
        team, owner = self.make_independent_team()
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(owner, match))

    def test_user_can_act_for_match_allows_team_manager(self):
        team, _owner = self.make_independent_team()
        manager = UserFactory(username="p2d_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(manager, match))

    def test_user_can_act_for_match_allows_tournament_captain_player(self):
        team, _owner = self.make_independent_team()
        captain = UserFactory(username="p2d_captain")
        TeamMembershipFactory(
            team=team,
            user=captain,
            role=MembershipRole.PLAYER,
            is_tournament_captain=True,
        )
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(captain, match))

    def test_user_can_act_for_match_blocks_coach(self):
        team, _owner = self.make_independent_team()
        coach = UserFactory(username="p2d_coach")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)
        match = self.make_match(team)
        self.assertFalse(user_can_act_for_match(coach, match))

    def test_user_can_act_for_match_blocks_plain_player(self):
        team, _owner = self.make_independent_team()
        player = UserFactory(username="p2d_player")
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)
        match = self.make_match(team)
        self.assertFalse(user_can_act_for_match(player, match))

    def test_user_can_act_for_match_blocks_non_member(self):
        team, _owner = self.make_independent_team()
        outsider = UserFactory(username="p2d_outsider")
        match = self.make_match(team)
        self.assertFalse(user_can_act_for_match(outsider, match))

    def test_user_can_act_for_match_blocks_inactive_owner(self):
        team, _owner = self.make_independent_team()
        inactive_owner = UserFactory(username="p2d_inactive_owner")
        TeamMembershipFactory(
            team=team,
            user=inactive_owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.INACTIVE,
        )
        match = self.make_match(team)
        self.assertFalse(user_can_act_for_match(inactive_owner, match))

    def test_user_can_act_for_match_allows_org_ceo_and_manager(self):
        ceo = UserFactory(username="p2d_org_ceo")
        org_manager = UserFactory(username="p2d_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None)
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(ceo, match))
        self.assertTrue(user_can_act_for_match(org_manager, match))

    def test_user_can_act_for_match_allows_creator_without_membership(self):
        team, creator = self.make_independent_team(with_creator_membership=False)
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(creator, match))

    def test_user_can_act_for_match_allows_superuser(self):
        team, _owner = self.make_independent_team()
        superuser = UserFactory(username="p2d_superuser", is_superuser=True)
        match = self.make_match(team)
        self.assertTrue(user_can_act_for_match(superuser, match))

    def test_user_can_act_for_match_preserves_solo_participant_behavior(self):
        game = GameFactory()
        solo_user = UserFactory(username="p2d_solo")
        tournament = self.make_tournament(game, participation_type=Tournament.SOLO)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=solo_user.id,
            participant1_name=solo_user.username,
        )
        self.assertTrue(user_can_act_for_match(solo_user, match))
        self.assertEqual(resolve_participant_side(solo_user, match), 1)

    def test_team_tournament_does_not_pass_when_user_id_equals_unrelated_team_id(self):
        game = GameFactory()
        user = UserFactory(username="p2d_id_collision")
        team = Team.objects.create(
            id=user.id,
            name="Phase 2D Collision Team",
            slug="phase-2d-collision-team",
            created_by=UserFactory(username="p2d_collision_owner"),
            game_id=game.id,
            region="NA",
            status=TeamStatus.ACTIVE,
        )
        tournament = self.make_tournament(game, participation_type=Tournament.TEAM)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=team.id,
            participant1_name=team.name,
        )
        self.assertFalse(user_can_act_for_match(user, match))
        self.assertIsNone(resolve_participant_side(user, match))

    def test_user_can_act_for_match_resolves_registration_participant_id(self):
        team, _owner = self.make_independent_team()
        manager = UserFactory(username="p2d_reg_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        game = GameFactory()
        team.game_id = game.id
        team.save(update_fields=["game_id"])
        tournament = self.make_tournament(game)
        registration = Registration.objects.create(
            id=900001,
            tournament=tournament,
            team_id=team.id,
            status=Registration.CONFIRMED,
        )
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=registration.id,
            participant1_name=team.name,
        )
        self.assertTrue(user_can_act_for_match(manager, match))

    def test_resolve_participant_side_team_owner_participant1_returns_one(self):
        team, owner = self.make_independent_team()
        match = self.make_match(team)
        self.assertEqual(resolve_participant_side(owner, match), 1)

    def test_resolve_participant_side_team_owner_participant2_returns_two(self):
        team, owner = self.make_independent_team()
        opponent, _opponent_owner = self.make_independent_team()
        game = GameFactory()
        for candidate in (team, opponent):
            candidate.game_id = game.id
            candidate.save(update_fields=["game_id"])
        tournament = self.make_tournament(game)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=2,
            participant1_id=opponent.id,
            participant1_name=opponent.name,
            participant2_id=team.id,
            participant2_name=team.name,
        )
        self.assertEqual(resolve_participant_side(owner, match), 2)

    def test_resolve_participant_side_tournament_captain_returns_correct_side(self):
        team, _owner = self.make_independent_team()
        opponent, _opponent_owner = self.make_independent_team()
        captain = UserFactory(username="p2d_side_captain")
        TeamMembershipFactory(
            team=team,
            user=captain,
            role=MembershipRole.PLAYER,
            is_tournament_captain=True,
        )
        game = GameFactory()
        for candidate in (team, opponent):
            candidate.game_id = game.id
            candidate.save(update_fields=["game_id"])
        tournament = self.make_tournament(game)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=3,
            participant1_id=opponent.id,
            participant1_name=opponent.name,
            participant2_id=team.id,
            participant2_name=team.name,
        )
        self.assertEqual(resolve_participant_side(captain, match), 2)

    def test_resolve_participant_side_non_participant_returns_none(self):
        team, _owner = self.make_independent_team()
        outsider = UserFactory(username="p2d_side_outsider")
        match = self.make_match(team)
        self.assertIsNone(resolve_participant_side(outsider, match))

    def test_submit_result_view_participant_helper_uses_match_authority(self):
        team, _owner = self.make_independent_team()
        manager = UserFactory(username="p2d_submit_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        match = self.make_match(team)
        self.assertTrue(SubmitResultView()._is_participant(manager, match))

    def test_is_participant_permission_uses_match_authority(self):
        team, _owner = self.make_independent_team()
        manager = UserFactory(username="p2d_api_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        match = self.make_match(team)
        request = SimpleNamespace(user=manager)
        self.assertTrue(IsParticipant().has_object_permission(request, None, match))

    def test_patched_sources_no_direct_participant_gate_regression(self):
        result_source = inspect.getsource(ResultViewSet.confirm_result)
        dispute_source = inspect.getsource(report_dispute)
        participant_source = inspect.getsource(matches_api.IsParticipant.has_object_permission)
        submit_source = inspect.getsource(matches_api.MatchViewSet.submit_result)
        self.assertIn("user_can_act_for_match(request.user, match)", result_source)
        self.assertIn("user_can_act_for_match(request.user, match)", dispute_source)
        self.assertIn("user_can_act_for_match(request.user, obj)", participant_source)
        self.assertIn("resolve_participant_side(request.user, match)", submit_source)
        self.assertNotIn("request.user.id in [match.participant1_id, match.participant2_id]", result_source)
        self.assertNotIn("match.participant1_id == request.user.id", submit_source)
        self.assertNotIn("match.participant2_id == request.user.id", submit_source)
