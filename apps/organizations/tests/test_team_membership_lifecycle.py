import json

from django.test import TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipEventType, MembershipRole, MembershipStatus
from apps.organizations.models import TeamMembershipEvent
from apps.organizations.services.team_invite_service import TeamInviteService
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.user_profile.models import UserProfile
from apps.user_profile.services.career_tab_service import CareerTabService


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


class TeamMembershipLifecycleTests(TestCase):
    def _independent_team(self, name="Lifecycle Team"):
        game = GameFactory()
        owner = UserFactory()
        team = TeamFactory.create_independent(created_by=owner, name=name, game_id=game.id)
        owner_membership = TeamMembershipFactory(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        return game, team, owner, owner_membership

    def test_decline_membership_invite_sets_inactive(self):
        _game, team, _owner, _owner_membership = self._independent_team("Lifecycle Decline Status")
        invited_user = UserFactory(username="lifecycle_invited_status")
        membership = TeamMembershipFactory(
            team=team,
            user=invited_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INVITED,
        )

        result = TeamInviteService.decline_membership_invite(membership.id, invited_user.id)

        self.assertEqual(result, {"success": True})
        membership.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.INACTIVE)
        self.assertNotEqual(membership.status, "DECLINED")

    def test_decline_membership_invite_writes_status_changed_event(self):
        _game, team, _owner, _owner_membership = self._independent_team("Lifecycle Decline Event")
        invited_user = UserFactory(username="lifecycle_invited_event")
        membership = TeamMembershipFactory(
            team=team,
            user=invited_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INVITED,
        )

        TeamInviteService.decline_membership_invite(membership.id, invited_user.id)

        event = TeamMembershipEvent.objects.get(
            membership=membership,
            event_type=MembershipEventType.STATUS_CHANGED,
        )
        self.assertEqual(event.team, team)
        self.assertEqual(event.user, invited_user)
        self.assertEqual(event.actor, invited_user)
        self.assertEqual(event.old_status, MembershipStatus.INVITED)
        self.assertEqual(event.new_status, MembershipStatus.INACTIVE)
        self.assertEqual(event.metadata.get("reason"), "invite_declined")

    def test_change_role_with_no_actual_changes_writes_no_event(self):
        _game, team, owner, _owner_membership = self._independent_team("Lifecycle Noop Role")
        player = UserFactory(username="lifecycle_noop_player")
        player_membership = TeamMembershipFactory(
            team=team,
            user=player,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
        )

        self.client.force_login(owner)
        response = self.client.post(
            api_url("team_manage_change_role", slug=team.slug, membership_id=player_membership.id),
            data=json.dumps({"role": MembershipRole.PLAYER}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TeamMembershipEvent.objects.filter(
                membership=player_membership,
                event_type=MembershipEventType.ROLE_CHANGED,
            ).exists()
        )

    def test_transfer_ownership_writes_event_for_both_members(self):
        _game, team, owner, owner_membership = self._independent_team("Lifecycle Transfer")
        target_user = UserFactory(username="lifecycle_new_owner")
        target_membership = TeamMembershipFactory(
            team=team,
            user=target_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
        )

        self.client.force_login(owner)
        response = self.client.post(
            api_url("team_manage_transfer", slug=team.slug),
            data=json.dumps({"member_id": target_membership.id, "confirm": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        old_owner_event = TeamMembershipEvent.objects.get(
            membership=owner_membership,
            event_type=MembershipEventType.ROLE_CHANGED,
        )
        new_owner_event = TeamMembershipEvent.objects.get(
            membership=target_membership,
            event_type=MembershipEventType.ROLE_CHANGED,
        )
        self.assertEqual(old_owner_event.old_role, MembershipRole.OWNER)
        self.assertEqual(old_owner_event.new_role, MembershipRole.MANAGER)
        self.assertEqual(old_owner_event.metadata.get("action"), "ownership_transferred")
        self.assertEqual(old_owner_event.metadata.get("to_user"), target_user.username)
        self.assertEqual(new_owner_event.old_role, MembershipRole.PLAYER)
        self.assertEqual(new_owner_event.new_role, MembershipRole.OWNER)

    def test_career_history_excludes_invited_membership(self):
        game, team, _owner, _owner_membership = self._independent_team("Lifecycle Career Invited")
        user = UserFactory(username="lifecycle_career_invited")
        profile, _created = UserProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": user.username},
        )
        TeamMembershipFactory(
            team=team,
            user=user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INVITED,
        )

        history = CareerTabService.get_team_affiliation_history(profile, game)

        self.assertEqual(history, [])

    def test_career_history_includes_inactive_membership(self):
        game, team, _owner, _owner_membership = self._independent_team("Lifecycle Career Inactive")
        user = UserFactory(username="lifecycle_career_inactive")
        profile, _created = UserProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": user.username},
        )
        TeamMembershipFactory(
            team=team,
            user=user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INACTIVE,
        )

        history = CareerTabService.get_team_affiliation_history(profile, game)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["team_id"], team.id)
