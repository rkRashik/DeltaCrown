from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.organizations.choices import MembershipEventType, MembershipRole, MembershipStatus
from apps.organizations.models import OrganizationMembership, TeamMembership, TeamMembershipEvent
from apps.organizations.services import team_authority
from apps.organizations.services.exceptions import ConflictError, PermissionDeniedError
from apps.organizations.services.team_service import TeamService
from apps.organizations.services.training_service import TeamTrainingService
from apps.organizations.tests.factories import (
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


class Phase2CTrainingAuthorityTests(TestCase):
    def make_independent_team(self, *, with_owner_membership=True, name="Phase 2C Training Team"):
        owner = UserFactory()
        team = TeamFactory.create_independent(created_by=owner, name=name)
        if with_owner_membership:
            TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        return team, owner

    def test_coach_can_manage_training_authority(self):
        team, _owner = self.make_independent_team(name="Phase 2C Coach Training")
        coach = UserFactory(username="phase2c_training_coach")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        self.assertTrue(TeamTrainingService.has_team_ops_authority(coach, team))
        TeamTrainingService.verify_team_ops_authority(coach, team)

    def test_plain_player_cannot_manage_training(self):
        team, _owner = self.make_independent_team(name="Phase 2C Player Training")
        player = UserFactory(username="phase2c_training_player")
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)

        self.assertFalse(TeamTrainingService.has_team_ops_authority(player, team))
        with self.assertRaises(PermissionDenied):
            TeamTrainingService.verify_team_ops_authority(player, team)

    def test_org_manager_can_manage_training_for_org_owned_team(self):
        org_manager = UserFactory(username="phase2c_training_org_manager")
        org = OrganizationFactory()
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Phase 2C Org Training")

        self.assertTrue(TeamTrainingService.has_team_ops_authority(org_manager, team))
        TeamTrainingService.verify_team_ops_authority(org_manager, team)

    def test_coach_can_create_vod_review(self):
        team, _owner = self.make_independent_team(name="Phase 2C Coach VOD")
        coach = UserFactory(username="phase2c_vod_coach")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        review = TeamTrainingService.create_vod_review(
            team=team,
            actor=coach,
            title="Map two review",
            external_url="https://example.com/vod",
        )

        self.assertEqual(review.team, team)
        self.assertEqual(review.reviewer, coach)

    def test_creator_without_membership_training_authority_matches_team_authority(self):
        team, creator = self.make_independent_team(
            with_owner_membership=False,
            name="Phase 2C Creator Training",
        )

        self.assertEqual(
            TeamTrainingService.has_team_ops_authority(creator, team),
            team_authority.can_manage_training(creator, team),
        )
        self.assertTrue(TeamTrainingService.has_team_ops_authority(creator, team))


class Phase2CTeamServiceAuthorityTests(TestCase):
    def make_independent_team(self, *, with_owner_membership=True, name="Phase 2C Service Team"):
        owner = UserFactory()
        team = TeamFactory.create_independent(created_by=owner, name=name)
        if with_owner_membership:
            TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        return team, owner

    def test_creator_without_membership_can_add_member(self):
        team, creator = self.make_independent_team(
            with_owner_membership=False,
            name="Phase 2C Creator Add",
        )
        candidate = UserFactory(username="phase2c_creator_candidate")

        membership_id = TeamService.add_team_member(
            team_id=team.id,
            user_lookup=candidate.username,
            role=MembershipRole.PLAYER,
            added_by_user_id=creator.id,
        )

        membership = TeamMembership.objects.get(id=membership_id)
        self.assertEqual(membership.user, candidate)
        self.assertEqual(membership.status, MembershipStatus.ACTIVE)

    def test_superuser_can_add_member(self):
        team, _owner = self.make_independent_team(name="Phase 2C Super Add")
        superuser = UserFactory(username="phase2c_superuser", is_superuser=True)
        candidate = UserFactory(username="phase2c_super_candidate")

        membership_id = TeamService.add_team_member(
            team_id=team.id,
            user_lookup=candidate.username,
            role=MembershipRole.PLAYER,
            added_by_user_id=superuser.id,
        )

        self.assertTrue(TeamMembership.objects.filter(id=membership_id, user=candidate).exists())

    def test_add_team_member_blocks_same_game_active_team_conflict(self):
        team_a, owner = self.make_independent_team(name="Phase 2C Conflict Add A")
        team_b = TeamFactory.create_independent(
            created_by=UserFactory(),
            name="Phase 2C Conflict Add B",
            game_id=team_a.game_id,
        )
        candidate = UserFactory(username="phase2c_conflict_candidate")
        TeamMembershipFactory(team=team_b, user=candidate, role=MembershipRole.PLAYER)

        with self.assertRaises(ConflictError) as ctx:
            TeamService.add_team_member(
                team_id=team_a.id,
                user_lookup=candidate.username,
                role=MembershipRole.PLAYER,
                added_by_user_id=owner.id,
            )

        self.assertEqual(ctx.exception.error_code, "GAME_TEAM_CONFLICT")
        self.assertIn(team_b.name, ctx.exception.safe_message)
        self.assertFalse(TeamMembership.objects.filter(team=team_a, user=candidate).exists())

    def test_add_team_member_allows_different_game_active_membership(self):
        team_a, owner = self.make_independent_team(name="Phase 2C Different Game Add A")
        team_b = TeamFactory.create_independent(
            created_by=UserFactory(),
            name="Phase 2C Different Game Add B",
            game_id=team_a.game_id + 1000,
        )
        candidate = UserFactory(username="phase2c_different_game_candidate")
        TeamMembershipFactory(team=team_b, user=candidate, role=MembershipRole.PLAYER)

        membership_id = TeamService.add_team_member(
            team_id=team_a.id,
            user_lookup=candidate.username,
            role=MembershipRole.PLAYER,
            added_by_user_id=owner.id,
        )

        self.assertTrue(
            TeamMembership.objects.filter(
                id=membership_id,
                team=team_a,
                user=candidate,
                status=MembershipStatus.ACTIVE,
            ).exists()
        )

    def test_add_team_member_preserves_same_team_duplicate_behavior(self):
        team, owner = self.make_independent_team(name="Phase 2C Same Team Duplicate")
        candidate = UserFactory(username="phase2c_same_team_duplicate")
        TeamMembershipFactory(team=team, user=candidate, role=MembershipRole.PLAYER)

        with self.assertRaises(ConflictError) as ctx:
            TeamService.add_team_member(
                team_id=team.id,
                user_lookup=candidate.username,
                role=MembershipRole.PLAYER,
                added_by_user_id=owner.id,
            )

        self.assertNotEqual(ctx.exception.error_code, "GAME_TEAM_CONFLICT")
        self.assertEqual(
            TeamMembership.objects.filter(
                team=team,
                user=candidate,
                status=MembershipStatus.ACTIVE,
            ).count(),
            1,
        )

    def test_add_team_member_blocks_org_owned_same_game_conflict(self):
        org_manager = UserFactory(username="phase2c_conflict_org_manager")
        org = OrganizationFactory()
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        org_team = TeamFactory(
            organization=org,
            created_by=None,
            name="Phase 2C Org Conflict Add",
            game_id=2200,
        )
        other_team = TeamFactory.create_independent(
            created_by=UserFactory(),
            name="Phase 2C Other Conflict Add",
            game_id=org_team.game_id,
        )
        candidate = UserFactory(username="phase2c_org_conflict_candidate")
        TeamMembershipFactory(team=other_team, user=candidate, role=MembershipRole.PLAYER)

        with self.assertRaises(ConflictError) as ctx:
            TeamService.add_team_member(
                team_id=org_team.id,
                user_lookup=candidate.username,
                role=MembershipRole.PLAYER,
                added_by_user_id=org_manager.id,
            )

        self.assertEqual(ctx.exception.error_code, "GAME_TEAM_CONFLICT")
        self.assertFalse(TeamMembership.objects.filter(team=org_team, user=candidate).exists())

    def test_coach_cannot_add_remove_or_update_roster(self):
        team, _owner = self.make_independent_team(name="Phase 2C Coach Roster Block")
        coach = UserFactory(username="phase2c_roster_coach")
        candidate = UserFactory(username="phase2c_roster_candidate")
        target = UserFactory(username="phase2c_roster_target")
        target_membership = TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        with self.assertRaises(PermissionDeniedError):
            TeamService.add_team_member(
                team_id=team.id,
                user_lookup=candidate.username,
                role=MembershipRole.PLAYER,
                added_by_user_id=coach.id,
            )

        with self.assertRaises(PermissionDeniedError):
            TeamService.update_member_role(
                membership_id=target_membership.id,
                role=MembershipRole.MANAGER,
                updated_by_user_id=coach.id,
            )

        with self.assertRaises(PermissionDeniedError):
            TeamService.remove_team_member(
                membership_id=target_membership.id,
                removed_by_user_id=coach.id,
            )

    def test_org_manager_can_add_member_to_org_owned_team(self):
        org_manager = UserFactory(username="phase2c_service_org_manager")
        org = OrganizationFactory()
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Phase 2C Org Add")
        candidate = UserFactory(username="phase2c_org_candidate")

        membership_id = TeamService.add_team_member(
            team_id=team.id,
            user_lookup=candidate.username,
            role=MembershipRole.PLAYER,
            added_by_user_id=org_manager.id,
        )

        self.assertTrue(TeamMembership.objects.filter(id=membership_id, user=candidate).exists())

    def test_inactive_manager_cannot_manage_through_team_service(self):
        team, _owner = self.make_independent_team(name="Phase 2C Inactive Manager")
        inactive_manager = UserFactory(username="phase2c_inactive_manager")
        candidate = UserFactory(username="phase2c_inactive_candidate")
        TeamMembershipFactory(
            team=team,
            user=inactive_manager,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.INACTIVE,
        )

        with self.assertRaises(PermissionDeniedError):
            TeamService.add_team_member(
                team_id=team.id,
                user_lookup=candidate.username,
                role=MembershipRole.PLAYER,
                added_by_user_id=inactive_manager.id,
            )

        with self.assertRaises(PermissionDeniedError):
            TeamService.update_team_settings(
                team_id=team.id,
                updated_by_user_id=inactive_manager.id,
                description="Blocked update",
            )

    def test_add_team_member_writes_membership_event(self):
        team, owner = self.make_independent_team(name="Phase 2C Add Event")
        candidate = UserFactory(username="phase2c_event_add_candidate")

        membership_id = TeamService.add_team_member(
            team_id=team.id,
            user_lookup=candidate.username,
            role=MembershipRole.PLAYER,
            added_by_user_id=owner.id,
        )
        membership = TeamMembership.objects.get(id=membership_id)

        event = TeamMembershipEvent.objects.get(membership=membership)
        self.assertEqual(event.event_type, MembershipEventType.JOINED)
        self.assertEqual(event.team, team)
        self.assertEqual(event.user, candidate)
        self.assertEqual(event.actor, owner)
        self.assertEqual(event.new_role, MembershipRole.PLAYER)
        self.assertEqual(event.new_status, MembershipStatus.ACTIVE)

    def test_remove_team_member_writes_membership_event(self):
        team, owner = self.make_independent_team(name="Phase 2C Remove Event")
        target = UserFactory(username="phase2c_event_remove_target")
        membership = TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)

        removed = TeamService.remove_team_member(
            membership_id=membership.id,
            removed_by_user_id=owner.id,
        )

        self.assertTrue(removed)
        event = TeamMembershipEvent.objects.get(membership=membership, event_type=MembershipEventType.REMOVED)
        self.assertEqual(event.team, team)
        self.assertEqual(event.user, target)
        self.assertEqual(event.actor, owner)
        self.assertEqual(event.old_role, MembershipRole.PLAYER)
        self.assertEqual(event.old_status, MembershipStatus.ACTIVE)
        self.assertEqual(event.new_status, MembershipStatus.INACTIVE)

    def test_remove_team_member_preserves_membership_history(self):
        team, owner = self.make_independent_team(name="Phase 2C Preserve History")
        target = UserFactory(username="phase2c_history_target")
        membership = TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)

        TeamService.remove_team_member(
            membership_id=membership.id,
            removed_by_user_id=owner.id,
        )

        membership.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.INACTIVE)
        self.assertIsNotNone(membership.left_at)
        self.assertEqual(membership.left_reason, "Removed by manager")
        self.assertTrue(TeamMembership.objects.filter(id=membership.id).exists())
        self.assertTrue(
            TeamMembershipEvent.objects.filter(
                membership=membership,
                event_type=MembershipEventType.REMOVED,
            ).exists()
        )
