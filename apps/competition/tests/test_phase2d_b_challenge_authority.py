from django.test import TestCase

from apps.competition.services.challenge_service import ChallengeService
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership
from apps.organizations.tests.factories import (
    GameFactory,
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


class Phase2DBChallengeAuthorityTests(TestCase):
    def setUp(self):
        self.game = GameFactory()

    def make_independent_team(self, *, created_by=None, status=TeamStatus.ACTIVE):
        creator = created_by or UserFactory()
        team = TeamFactory.create_independent(
            created_by=creator,
            game_id=self.game.id,
            status=status,
        )
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

    def make_org_team(self):
        ceo = UserFactory(username="p2db_org_ceo")
        org = OrganizationFactory(ceo=ceo)
        team = TeamFactory(
            organization=org,
            created_by=None,
            game_id=self.game.id,
            status=TeamStatus.ACTIVE,
        )
        return org, team, ceo

    def test_owner_and_manager_pass_has_team_authority(self):
        team, _creator = self.make_independent_team()
        owner = UserFactory(username="p2db_owner")
        manager = UserFactory(username="p2db_manager")
        self.add_member(team, owner, role=MembershipRole.OWNER)
        self.add_member(team, manager, role=MembershipRole.MANAGER)

        self.assertTrue(ChallengeService._has_team_authority(owner, team))
        self.assertTrue(ChallengeService._has_team_authority(manager, team))

    def test_org_ceo_and_manager_pass_has_team_authority_for_org_team(self):
        org, team, ceo = self.make_org_team()
        org_manager = UserFactory(username="p2db_org_manager")
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")

        self.assertTrue(ChallengeService._has_team_authority(ceo, team))
        self.assertTrue(ChallengeService._has_team_authority(org_manager, team))

    def test_creator_without_membership_and_superuser_pass_has_team_authority(self):
        creator = UserFactory(username="p2db_creator")
        team, _creator = self.make_independent_team(created_by=creator)
        superuser = UserFactory(username="p2db_superuser", is_superuser=True)

        self.assertTrue(ChallengeService._has_team_authority(creator, team))
        self.assertTrue(ChallengeService._has_team_authority(superuser, team))

    def test_coach_player_inactive_owner_and_non_member_are_blocked(self):
        team, _creator = self.make_independent_team()
        coach = UserFactory(username="p2db_coach")
        player = UserFactory(username="p2db_player")
        inactive_owner = UserFactory(username="p2db_inactive_owner")
        outsider = UserFactory(username="p2db_outsider")
        self.add_member(team, coach, role=MembershipRole.COACH)
        self.add_member(team, player, role=MembershipRole.PLAYER)
        self.add_member(
            team,
            inactive_owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.INACTIVE,
        )

        self.assertFalse(ChallengeService._has_team_authority(coach, team))
        self.assertFalse(ChallengeService._has_team_authority(player, team))
        self.assertFalse(ChallengeService._has_team_authority(inactive_owner, team))
        self.assertFalse(ChallengeService._has_team_authority(outsider, team))

    def test_tournament_captain_respects_allow_captain_policy(self):
        team, _creator = self.make_independent_team()
        captain = UserFactory(username="p2db_captain")
        self.add_member(team, captain, role=MembershipRole.PLAYER, captain=True)

        self.assertTrue(ChallengeService._has_team_authority(captain, team))
        self.assertFalse(ChallengeService._has_team_authority(captain, team, allow_captain=False))

    def test_disbanded_team_owner_is_blocked(self):
        owner = UserFactory(username="p2db_disbanded_owner")
        team, _creator = self.make_independent_team(created_by=owner, status=TeamStatus.DISBANDED)
        self.add_member(team, owner, role=MembershipRole.OWNER)

        self.assertFalse(ChallengeService._has_team_authority(owner, team))

    def test_owner_or_manager_helper_allows_admin_authority(self):
        team, creator = self.make_independent_team()
        owner = UserFactory(username="p2db_oom_owner")
        manager = UserFactory(username="p2db_oom_manager")
        superuser = UserFactory(username="p2db_oom_superuser", is_superuser=True)
        self.add_member(team, owner, role=MembershipRole.OWNER)
        self.add_member(team, manager, role=MembershipRole.MANAGER)

        org, org_team, ceo = self.make_org_team()
        org_manager = UserFactory(username="p2db_oom_org_manager")
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")

        self.assertTrue(ChallengeService._is_team_owner_or_manager(owner, team))
        self.assertTrue(ChallengeService._is_team_owner_or_manager(manager, team))
        self.assertTrue(ChallengeService._is_team_owner_or_manager(creator, team))
        self.assertTrue(ChallengeService._is_team_owner_or_manager(superuser, team))
        self.assertTrue(ChallengeService._is_team_owner_or_manager(ceo, org_team))
        self.assertTrue(ChallengeService._is_team_owner_or_manager(org_manager, org_team))

    def test_owner_or_manager_helper_blocks_non_admin_authority(self):
        team, _creator = self.make_independent_team()
        captain = UserFactory(username="p2db_oom_captain")
        coach = UserFactory(username="p2db_oom_coach")
        player = UserFactory(username="p2db_oom_player")
        inactive_owner = UserFactory(username="p2db_oom_inactive_owner")
        outsider = UserFactory(username="p2db_oom_outsider")
        self.add_member(team, captain, role=MembershipRole.PLAYER, captain=True)
        self.add_member(team, coach, role=MembershipRole.COACH)
        self.add_member(team, player, role=MembershipRole.PLAYER)
        self.add_member(
            team,
            inactive_owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.INACTIVE,
        )

        self.assertFalse(ChallengeService._is_team_owner_or_manager(captain, team))
        self.assertFalse(ChallengeService._is_team_owner_or_manager(coach, team))
        self.assertFalse(ChallengeService._is_team_owner_or_manager(player, team))
        self.assertFalse(ChallengeService._is_team_owner_or_manager(inactive_owner, team))
        self.assertFalse(ChallengeService._is_team_owner_or_manager(outsider, team))
