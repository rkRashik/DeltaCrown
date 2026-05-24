import inspect

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from apps.competition.models import GameRankingConfig, MatchReport
from apps.competition.services.match_report_service import MatchReportService
from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import OrganizationMembership
from apps.organizations.tests.factories import (
    GameFactory,
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.tournaments.views.result_submission import SubmitResultView


class Phase2DCMatchReportAuthorityTests(TestCase):
    def setUp(self):
        self.game = GameFactory()
        self.game_id = "P2DC"
        GameRankingConfig.objects.create(
            game_id=self.game_id,
            game_name="Phase 2D-C Test Game",
        )
        self.opponent = TeamFactory.create_independent(
            created_by=UserFactory(username="p2dc_opponent_owner"),
            game_id=self.game.id,
        )

    def make_independent_team(self, *, created_by=None, with_creator_membership=False):
        creator = created_by or UserFactory()
        team = TeamFactory.create_independent(created_by=creator, game_id=self.game.id)
        if with_creator_membership:
            TeamMembershipFactory(team=team, user=creator, role=MembershipRole.OWNER)
        return team, creator

    def add_member(
        self,
        team,
        user,
        *,
        role=MembershipRole.PLAYER,
        status=MembershipStatus.ACTIVE,
        captain=False,
    ):
        return TeamMembershipFactory(
            team=team,
            user=user,
            role=role,
            status=status,
            is_tournament_captain=captain,
        )

    def submit_report(self, user, team):
        return MatchReportService.submit_match_report(
            submitted_by=user,
            team1=team,
            team2=self.opponent,
            game_id=self.game_id,
            result="WIN",
            played_at=timezone.now() - timezone.timedelta(hours=1),
        )

    def assert_can_submit(self, user, team):
        before = MatchReport.objects.count()
        report = self.submit_report(user, team)
        self.assertEqual(MatchReport.objects.count(), before + 1)
        self.assertEqual(report.submitted_by, user)
        self.assertEqual(report.team1, team)

    def assert_cannot_submit(self, user, team):
        before = MatchReport.objects.count()
        with self.assertRaises(PermissionDenied):
            self.submit_report(user, team)
        self.assertEqual(MatchReport.objects.count(), before)

    def test_owner_and_manager_can_submit_match_report(self):
        team, _creator = self.make_independent_team()
        owner = UserFactory(username="p2dc_owner")
        manager = UserFactory(username="p2dc_manager")
        self.add_member(team, owner, role=MembershipRole.OWNER)
        self.add_member(team, manager, role=MembershipRole.MANAGER)

        self.assert_can_submit(owner, team)
        self.assert_can_submit(manager, team)

    def test_org_ceo_and_manager_can_submit_for_org_owned_team(self):
        ceo = UserFactory(username="p2dc_org_ceo")
        org_manager = UserFactory(username="p2dc_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, game_id=self.game.id)

        self.assert_can_submit(ceo, team)
        self.assert_can_submit(org_manager, team)

    def test_creator_without_membership_and_superuser_can_submit(self):
        creator = UserFactory(username="p2dc_creator")
        team, _creator = self.make_independent_team(created_by=creator)
        superuser = UserFactory(username="p2dc_superuser", is_superuser=True)

        self.assert_can_submit(creator, team)
        self.assert_can_submit(superuser, team)

    def test_coach_player_tournament_captain_inactive_owner_and_non_member_are_blocked(self):
        team, _creator = self.make_independent_team()
        coach = UserFactory(username="p2dc_coach")
        player = UserFactory(username="p2dc_player")
        captain = UserFactory(username="p2dc_captain")
        inactive_owner = UserFactory(username="p2dc_inactive_owner")
        outsider = UserFactory(username="p2dc_outsider")
        self.add_member(team, coach, role=MembershipRole.COACH)
        self.add_member(team, player, role=MembershipRole.PLAYER)
        self.add_member(team, captain, role=MembershipRole.PLAYER, captain=True)
        self.add_member(
            team,
            inactive_owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.INACTIVE,
        )

        self.assert_cannot_submit(coach, team)
        self.assert_cannot_submit(player, team)
        self.assert_cannot_submit(captain, team)
        self.assert_cannot_submit(inactive_owner, team)
        self.assert_cannot_submit(outsider, team)

    def test_submit_result_get_context_uses_resolved_participant_side(self):
        source = inspect.getsource(SubmitResultView.get)

        self.assertIn("resolve_participant_side(request.user, match)", source)
        self.assertIn("'is_participant1': side == 1", source)
        self.assertIn("'is_participant2': side == 2", source)
        self.assertNotIn("match.participant1_id == request.user.id", source)
        self.assertNotIn("match.participant2_id == request.user.id", source)
