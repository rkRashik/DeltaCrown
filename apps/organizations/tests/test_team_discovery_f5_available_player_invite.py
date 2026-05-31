import json

from django.test import TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import TeamInvite, TeamMembership
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.user_profile.models import CareerProfile, UserProfile


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


class AvailablePlayerInviteTests(TestCase):
    def _team(self, name="F5 Team", *, owner=None, game=None):
        owner = owner or UserFactory()
        game = game or GameFactory()
        team = TeamFactory.create_independent(
            created_by=owner,
            name=name,
            game_id=game.id,
        )
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        return team, owner, game

    def _available_player(
        self,
        username="f5_available_player",
        *,
        lft_enabled=True,
        recruiter_visibility="PUBLIC",
        career_status="LOOKING",
        email=None,
    ):
        user = UserFactory(username=username, email=email or f"{username}@example.com")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = username.replace("_", " ").title()
        profile.save(update_fields=["display_name"])
        CareerProfile.objects.update_or_create(
            user_profile=profile,
            defaults={
                "career_status": career_status,
                "lft_enabled": lft_enabled,
                "primary_roles": ["IGL"],
                "secondary_roles": ["Support"],
                "preferred_region": "BD",
                "availability": "WEEKENDS",
                "recruiter_visibility": recruiter_visibility,
            },
        )
        return user

    def _post_invite(self, team, user, actor=None):
        if actor is not None:
            self.client.force_login(actor)
        return self.client.post(
            api_url("team_manage_invite_available_player", slug=team.slug, user_id=user.id),
            data="{}",
            content_type="application/json",
        )

    def test_owner_can_invite_public_available_player_by_user_id(self):
        team, owner, _game = self._team("F5 Owner Invite")
        target = self._available_player("f5_owner_target", email="private-target@example.com")

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["invite"]["username"], target.username)
        self.assertEqual(body["invite"]["role"], MembershipRole.PLAYER)
        self.assertNotIn("private-target@example.com", json.dumps(body))
        self.assertTrue(TeamInvite.objects.filter(team=team, invited_user=target, status="PENDING").exists())
        self.assertTrue(
            TeamMembership.objects.filter(
                team=team,
                user=target,
                role=MembershipRole.PLAYER,
                status=MembershipStatus.INVITED,
            ).exists()
        )

    def test_manager_can_invite_public_available_player_by_user_id(self):
        team, _owner, _game = self._team("F5 Manager Invite")
        manager = UserFactory(username="f5_invite_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        target = self._available_player("f5_manager_target")

        response = self._post_invite(team, target, manager)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(TeamInvite.objects.filter(team=team, invited_user=target, status="PENDING").exists())

    def test_anonymous_cannot_invite_available_player(self):
        team, _owner, _game = self._team("F5 Anonymous Block")
        target = self._available_player("f5_anon_target")

        response = self._post_invite(team, target)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())

    def test_non_manager_cannot_invite_available_player(self):
        team, _owner, _game = self._team("F5 Player Block")
        actor = UserFactory(username="f5_player_actor")
        TeamMembershipFactory(team=team, user=actor, role=MembershipRole.PLAYER)
        target = self._available_player("f5_player_block_target")

        response = self._post_invite(team, target, actor)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())

    def test_private_lft_player_cannot_be_invited_via_available_player_endpoint(self):
        team, owner, _game = self._team("F5 Private LFT Block")
        target = self._available_player("f5_private_lft_target", recruiter_visibility="PRIVATE")

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "AVAILABLE_PLAYER_NOT_FOUND")
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())

    def test_non_lft_player_cannot_be_invited_via_available_player_endpoint(self):
        team, owner, _game = self._team("F5 Non LFT Block")
        target = self._available_player("f5_non_lft_target", lft_enabled=False)

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "AVAILABLE_PLAYER_NOT_FOUND")
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())

    def test_same_game_active_team_conflict_is_blocked(self):
        team, owner, game = self._team("F5 Conflict Team")
        other_team = TeamFactory.create_independent(
            created_by=UserFactory(username="f5_conflict_other_owner"),
            name="F5 Other Active Team",
            game_id=game.id,
        )
        target = self._available_player("f5_conflict_target")
        TeamMembershipFactory(team=other_team, user=target, role=MembershipRole.PLAYER)

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "GAME_TEAM_CONFLICT")
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())

    def test_duplicate_pending_invite_is_blocked(self):
        team, owner, _game = self._team("F5 Duplicate Invite")
        target = self._available_player("f5_duplicate_target")
        TeamInvite.objects.create(
            team=team,
            invited_user=target,
            inviter=owner,
            role=MembershipRole.PLAYER,
            status="PENDING",
        )

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 400)
        self.assertIn("pending invite", response.json()["error"])
        self.assertEqual(TeamInvite.objects.filter(team=team, invited_user=target, status="PENDING").count(), 1)

    def test_existing_active_member_is_blocked(self):
        team, owner, _game = self._team("F5 Existing Member")
        target = self._available_player("f5_existing_member")
        TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)

        response = self._post_invite(team, target, owner)

        self.assertEqual(response.status_code, 400)
        self.assertIn("already a member", response.json()["error"])
        self.assertFalse(TeamInvite.objects.filter(team=team, invited_user=target).exists())
