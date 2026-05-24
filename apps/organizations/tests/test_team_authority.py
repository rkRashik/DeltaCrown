import uuid

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership, Team
from apps.organizations.services import team_authority
from apps.organizations.tests.factories import (
    GameFactory,
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.tournaments.api.permissions import IsMatchParticipant
from apps.tournaments.models import Match, Registration, Tournament
from apps.tournaments.services.checkin_service import CheckinService
from apps.tournaments.services.registration_eligibility import RegistrationEligibilityService


class TeamAuthorityTestCase(TestCase):
    def setUp(self):
        self.owner = UserFactory(username="ta_owner")
        self.team = TeamFactory.create_independent(created_by=self.owner, name="Authority Team")

    def add_member(self, user, role=MembershipRole.PLAYER, status=MembershipStatus.ACTIVE, captain=False):
        return TeamMembershipFactory(
            team=self.team,
            user=user,
            role=role,
            status=status,
            is_tournament_captain=captain,
        )

    def test_anonymous_and_non_member_cannot_access_or_mutate(self):
        outsider = UserFactory(username="ta_outsider")
        self.assertFalse(team_authority.can_access_team_hq(AnonymousUser(), self.team))
        self.assertFalse(team_authority.can_manage_team_profile(outsider, self.team))
        self.assertFalse(team_authority.can_manage_roster(outsider, self.team))

    def test_non_member_cannot_access_team_hq(self):
        outsider = UserFactory(username="ta_hq_outsider")
        self.assertFalse(team_authority.can_access_team_hq(outsider, self.team))

    def test_active_owner_can_manage_profile_roster_competitive(self):
        self.add_member(self.owner, MembershipRole.OWNER)
        self.assertTrue(team_authority.can_manage_team_profile(self.owner, self.team))
        self.assertTrue(team_authority.can_manage_roster(self.owner, self.team))
        self.assertTrue(team_authority.can_act_as_team_captain(self.owner, self.team))

    def test_active_manager_can_manage_profile_roster_competitive(self):
        manager = UserFactory(username="ta_manager")
        self.add_member(manager, MembershipRole.MANAGER)
        self.assertTrue(team_authority.can_manage_team_profile(manager, self.team))
        self.assertTrue(team_authority.can_manage_roster(manager, self.team))
        self.assertTrue(team_authority.can_act_as_team_captain(manager, self.team))

    def test_coach_training_analytics_not_admin(self):
        coach = UserFactory(username="ta_coach")
        self.add_member(coach, MembershipRole.COACH)
        self.assertTrue(team_authority.can_manage_training(coach, self.team))
        self.assertTrue(team_authority.can_view_analytics(coach, self.team))
        self.assertFalse(team_authority.can_manage_team_profile(coach, self.team))
        self.assertFalse(team_authority.can_manage_roster(coach, self.team))
        self.assertFalse(team_authority.can_manage_discord(coach, self.team))

    def test_plain_player_cannot_mutate(self):
        player = UserFactory(username="ta_player")
        self.add_member(player, MembershipRole.PLAYER)
        self.assertFalse(team_authority.can_manage_team_profile(player, self.team))
        self.assertFalse(team_authority.can_manage_roster(player, self.team))
        self.assertFalse(team_authority.can_act_as_team_captain(player, self.team))

    def test_tournament_captain_gets_competitive_not_profile(self):
        captain = UserFactory(username="ta_captain")
        self.add_member(captain, MembershipRole.PLAYER, captain=True)
        self.assertTrue(team_authority.can_act_as_team_captain(captain, self.team))
        self.assertTrue(team_authority.can_submit_team_result(captain, self.team))
        self.assertFalse(team_authority.can_manage_team_profile(captain, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(captain, self.team))

    def test_inactive_owner_cannot_mutate(self):
        inactive_owner = UserFactory(username="ta_inactive_owner")
        self.add_member(inactive_owner, MembershipRole.OWNER, status=MembershipStatus.INACTIVE)
        self.assertFalse(team_authority.can_manage_team_profile(inactive_owner, self.team))
        self.assertFalse(team_authority.can_act_as_team_captain(inactive_owner, self.team))

    def test_org_ceo_and_manager_can_manage_org_team(self):
        ceo = UserFactory(username="ta_org_ceo")
        manager = UserFactory(username="ta_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Org Authority Team")
        self.assertTrue(team_authority.can_manage_team_profile(ceo, team))
        self.assertTrue(team_authority.can_manage_team_profile(manager, team))

    def test_sensitive_team_data_admin_only(self):
        self.add_member(self.owner, MembershipRole.OWNER)
        manager = UserFactory(username="ta_sensitive_manager")
        coach = UserFactory(username="ta_sensitive_coach")
        player = UserFactory(username="ta_sensitive_player")
        captain = UserFactory(username="ta_sensitive_captain")
        inactive_owner = UserFactory(username="ta_sensitive_inactive_owner")
        outsider = UserFactory(username="ta_sensitive_outsider")
        superuser = UserFactory(username="ta_sensitive_super", is_superuser=True)
        self.add_member(manager, MembershipRole.MANAGER)
        self.add_member(coach, MembershipRole.COACH)
        self.add_member(player, MembershipRole.PLAYER)
        self.add_member(captain, MembershipRole.PLAYER, captain=True)
        self.add_member(inactive_owner, MembershipRole.OWNER, status=MembershipStatus.INACTIVE)

        org_ceo = UserFactory(username="ta_sensitive_org_ceo")
        org_manager = UserFactory(username="ta_sensitive_org_manager")
        org = OrganizationFactory(ceo=org_ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        org_team = TeamFactory(organization=org, created_by=None, name="Sensitive Org Team")

        self.assertTrue(team_authority.can_view_sensitive_team_data(self.owner, self.team))
        self.assertTrue(team_authority.can_view_sensitive_team_data(manager, self.team))
        self.assertTrue(team_authority.can_view_sensitive_team_data(org_ceo, org_team))
        self.assertTrue(team_authority.can_view_sensitive_team_data(org_manager, org_team))
        self.assertTrue(team_authority.can_view_sensitive_team_data(superuser, self.team))

        self.assertFalse(team_authority.can_view_sensitive_team_data(coach, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(player, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(captain, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(outsider, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(inactive_owner, self.team))

    def test_can_access_hq_does_not_equal_sensitive_access(self):
        coach = UserFactory(username="ta_hq_coach")
        player = UserFactory(username="ta_hq_player")
        self.add_member(coach, MembershipRole.COACH)
        self.add_member(player, MembershipRole.PLAYER)
        self.assertTrue(team_authority.can_access_team_hq(coach, self.team))
        self.assertTrue(team_authority.can_access_team_hq(player, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(coach, self.team))
        self.assertFalse(team_authority.can_view_sensitive_team_data(player, self.team))

    def test_org_analyst_and_scout_cannot_manage_org_team(self):
        analyst = UserFactory(username="ta_org_analyst")
        scout = UserFactory(username="ta_org_scout")
        org = OrganizationFactory()
        OrganizationMembership.objects.create(organization=org, user=analyst, role="ANALYST")
        OrganizationMembership.objects.create(organization=org, user=scout, role="SCOUT")
        team = TeamFactory(organization=org, created_by=None, name="Org Non Admin Team")
        self.assertFalse(team_authority.can_manage_team_profile(analyst, team))
        self.assertFalse(team_authority.can_manage_team_profile(scout, team))

    def test_creator_role_is_owner_never_creator(self):
        actor = team_authority.get_team_actor(self.owner, self.team)
        self.assertEqual(actor.role, "OWNER")
        self.assertTrue(actor.is_creator)

        TeamMembershipFactory(team=self.team, user=self.owner, role=MembershipRole.PLAYER)
        actor = team_authority.get_team_actor(self.owner, self.team)
        self.assertNotEqual(actor.role, "CREATOR")
        self.assertTrue(actor.is_team_admin)

    def test_disbanded_team_blocks_normal_mutations(self):
        self.add_member(self.owner, MembershipRole.OWNER)
        self.team.status = TeamStatus.DISBANDED
        self.team.save(update_fields=["status"])
        self.assertFalse(team_authority.can_manage_team_profile(self.owner, self.team))
        self.assertFalse(team_authority.can_act_as_team_captain(self.owner, self.team))

    def test_treasury_is_stricter_than_manager(self):
        manager = UserFactory(username="ta_treasury_manager")
        self.add_member(manager, MembershipRole.MANAGER)
        self.assertTrue(team_authority.can_manage_team_profile(manager, self.team))
        self.assertFalse(team_authority.can_manage_treasury(manager, self.team))
        self.add_member(self.owner, MembershipRole.OWNER)
        self.assertTrue(team_authority.can_manage_treasury(self.owner, self.team))

    def test_competitive_settings_are_admin_only_not_tournament_captain(self):
        captain = UserFactory(username="ta_comp_settings_captain")
        self.add_member(captain, MembershipRole.PLAYER, captain=True)
        self.assertTrue(team_authority.can_act_as_team_captain(captain, self.team))
        self.assertFalse(team_authority.can_manage_competitive_settings(captain, self.team))

    def test_can_create_team_in_org_for_ceo_and_manager_only(self):
        ceo = UserFactory(username="ta_create_org_ceo")
        manager = UserFactory(username="ta_create_org_manager")
        scout = UserFactory(username="ta_create_org_scout")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=manager, role="MANAGER")
        OrganizationMembership.objects.create(organization=org, user=scout, role="SCOUT")
        self.assertTrue(team_authority.can_create_team_in_org(ceo, org))
        self.assertTrue(team_authority.can_create_team_in_org(manager, org))
        self.assertFalse(team_authority.can_create_team_in_org(scout, org))

    def test_can_archive_org_team_for_org_ceo_or_superuser_not_manager(self):
        ceo = UserFactory(username="ta_archive_ceo")
        manager = UserFactory(username="ta_archive_manager")
        superuser = UserFactory(username="ta_archive_superuser", is_superuser=True)
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Archive Org Team")
        self.assertTrue(team_authority.can_archive_org_team(ceo, team))
        self.assertTrue(team_authority.can_archive_org_team(superuser, team))
        self.assertFalse(team_authority.can_archive_org_team(manager, team))


class TournamentAuthorityRegressionTests(TestCase):
    def make_tournament(self, game, **kwargs):
        now = timezone.now()
        defaults = {
            "name": "Authority Cup",
            "slug": f"authority-cup-{uuid.uuid4().hex[:10]}",
            "organizer": UserFactory(username=f"ta_organizer_{UserFactory._meta.model.objects.count()}"),
            "game": game,
            "participation_type": Tournament.TEAM,
            "status": Tournament.REGISTRATION_OPEN,
            "registration_start": now - timezone.timedelta(days=1),
            "registration_end": now + timezone.timedelta(days=1),
            "tournament_start": now + timezone.timedelta(minutes=10),
        }
        defaults.update(kwargs)
        return Tournament.objects.create(**defaults)

    def make_team_registration(self, tournament, team):
        return Registration.objects.create(
            tournament=tournament,
            team_id=team.id,
            status=Registration.CONFIRMED,
        )

    def test_checkin_allows_tournament_captain_and_manager_but_blocks_plain_player(self):
        game = GameFactory()
        team = TeamFactory.create_independent(created_by=UserFactory(username="ta_ci_owner"), game_id=game.id)
        tournament = self.make_tournament(game)
        registration = self.make_team_registration(tournament, team)
        captain = UserFactory(username="ta_ci_captain")
        manager = UserFactory(username="ta_ci_manager")
        player = UserFactory(username="ta_ci_player")
        TeamMembershipFactory(team=team, user=captain, role=MembershipRole.PLAYER, is_tournament_captain=True)
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)

        self.assertTrue(CheckinService._is_registration_owner(captain, registration))
        self.assertTrue(CheckinService._is_registration_owner(manager, registration))
        self.assertFalse(CheckinService._is_registration_owner(player, registration))
        self.assertTrue(CheckinService.can_check_in(tournament, captain))
        self.assertTrue(CheckinService.can_check_in(tournament, manager))
        self.assertFalse(CheckinService.can_check_in(tournament, player))

    def test_registration_eligibility_allows_tournament_captain(self):
        game = GameFactory()
        owner = UserFactory(username="ta_reg_owner")
        captain = UserFactory(username="ta_reg_captain")
        team = TeamFactory.create_independent(created_by=owner, game_id=game.id)
        TeamMembershipFactory(team=team, user=captain, role=MembershipRole.PLAYER, is_tournament_captain=True)
        tournament = self.make_tournament(game)

        result = RegistrationEligibilityService._check_team_eligibility(tournament, captain)
        self.assertTrue(result.is_eligible, result.reason)

    def test_match_participant_allows_team_authority_user_and_blocks_random(self):
        game = GameFactory()
        captain = UserFactory(username="ta_match_captain")
        random_user = UserFactory(username="ta_match_random")
        team = TeamFactory.create_independent(created_by=UserFactory(username="ta_match_owner"), game_id=game.id)
        TeamMembershipFactory(team=team, user=captain, role=MembershipRole.PLAYER, is_tournament_captain=True)
        tournament = self.make_tournament(game)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=team.id,
            participant1_name=team.name,
        )
        permission = IsMatchParticipant()

        class Request:
            pass

        request = Request()
        request.user = captain
        self.assertTrue(permission.has_object_permission(request, None, match))

        request.user = random_user
        self.assertFalse(permission.has_object_permission(request, None, match))

    def test_match_participant_does_not_pass_on_user_id_equal_team_id_without_authority(self):
        game = GameFactory()
        user = UserFactory(username="ta_id_collision")
        team = Team.objects.create(
            id=user.id,
            name="ID Collision Team",
            slug="id-collision-team",
            created_by=UserFactory(username="ta_id_collision_owner"),
            game_id=game.id,
            region="NA",
            status=TeamStatus.ACTIVE,
        )
        tournament = self.make_tournament(game)
        match = Match.objects.create(
            tournament=tournament,
            round_number=1,
            match_number=1,
            participant1_id=team.id,
            participant1_name=team.name,
        )
        permission = IsMatchParticipant()

        class Request:
            pass

        request = Request()
        request.user = user
        self.assertFalse(permission.has_object_permission(request, None, match))
