from django.test import TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import TeamInvite, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.organizations.services.team_invite_service import (
    InviteConflictError,
    TeamInviteService,
)
from apps.organizations.tests.factories import TeamFactory, TeamMembershipFactory, UserFactory


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


class OneTeamPerGameInviteAcceptTests(TestCase):
    def _team(self, name, owner=None, game_id=1):
        return TeamFactory.create_independent(
            created_by=owner or UserFactory(),
            name=name,
            game_id=game_id,
        )

    def test_accept_membership_invite_conflict_keeps_invite_pending(self):
        user = UserFactory(username="p0b_membership_conflict")
        team_a = self._team("P0B Invite Team A", game_id=77)
        team_b = self._team("P0B Active Team B", game_id=77)
        TeamMembershipFactory(team=team_b, user=user, role=MembershipRole.PLAYER)
        invite_membership = TeamMembershipFactory(
            team=team_a,
            user=user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INVITED,
        )

        with self.assertRaises(InviteConflictError) as ctx:
            TeamInviteService.accept_membership_invite(invite_membership.id, user.id)

        self.assertEqual(ctx.exception.error_code, "GAME_TEAM_CONFLICT")
        invite_membership.refresh_from_db()
        self.assertEqual(invite_membership.status, MembershipStatus.INVITED)
        self.assertFalse(
            TeamMembership.objects.filter(team=team_a, user=user, status=MembershipStatus.ACTIVE).exists()
        )

    def test_accept_membership_invite_different_game_succeeds(self):
        user = UserFactory(username="p0b_membership_different_game")
        team_a = self._team("P0B Invite Different Game A", game_id=78)
        team_b = self._team("P0B Active Different Game B", game_id=79)
        TeamMembershipFactory(team=team_b, user=user, role=MembershipRole.PLAYER)
        invite_membership = TeamMembershipFactory(
            team=team_a,
            user=user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INVITED,
        )

        result = TeamInviteService.accept_membership_invite(invite_membership.id, user.id)

        self.assertEqual(result["team_id"], team_a.id)
        invite_membership.refresh_from_db()
        self.assertEqual(invite_membership.status, MembershipStatus.ACTIVE)

    def test_accept_email_invite_new_membership_conflict_keeps_pending(self):
        user = UserFactory(username="p0b_email_conflict", email="p0b-email-conflict@example.com")
        inviter = UserFactory(username="p0b_email_inviter")
        team_a = self._team("P0B Email Team A", game_id=80)
        team_b = self._team("P0B Email Team B", game_id=80)
        TeamMembershipFactory(team=team_b, user=user, role=MembershipRole.PLAYER)
        invite = TeamInvite.objects.create(
            team=team_a,
            invited_email=user.email,
            inviter=inviter,
            role=MembershipRole.PLAYER,
            status="PENDING",
        )

        with self.assertRaises(InviteConflictError):
            TeamInviteService.accept_email_invite(str(invite.token), user.id)

        invite.refresh_from_db()
        self.assertEqual(invite.status, "PENDING")
        self.assertFalse(TeamMembership.objects.filter(team=team_a, user=user).exists())

    def test_accept_email_invite_reactivation_conflict_keeps_inactive_and_pending(self):
        user = UserFactory(username="p0b_email_reactivation", email="p0b-reactivation@example.com")
        inviter = UserFactory(username="p0b_reactivation_inviter")
        team_a = self._team("P0B Reactivate Team A", game_id=81)
        team_b = self._team("P0B Reactivate Team B", game_id=81)
        inactive_membership = TeamMembershipFactory(
            team=team_a,
            user=user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.INACTIVE,
        )
        TeamMembershipFactory(team=team_b, user=user, role=MembershipRole.PLAYER)
        invite = TeamInvite.objects.create(
            team=team_a,
            invited_email=user.email,
            inviter=inviter,
            role=MembershipRole.MANAGER,
            status="PENDING",
        )

        with self.assertRaises(InviteConflictError):
            TeamInviteService.accept_email_invite(str(invite.token), user.id)

        inactive_membership.refresh_from_db()
        invite.refresh_from_db()
        self.assertEqual(inactive_membership.status, MembershipStatus.INACTIVE)
        self.assertEqual(invite.status, "PENDING")

    def test_accept_email_invite_without_conflict_succeeds(self):
        user = UserFactory(username="p0b_email_success", email="p0b-email-success@example.com")
        inviter = UserFactory(username="p0b_email_success_inviter")
        team = self._team("P0B Email Success Team", game_id=82)
        invite = TeamInvite.objects.create(
            team=team,
            invited_email=user.email,
            inviter=inviter,
            role=MembershipRole.PLAYER,
            status="PENDING",
        )

        result = TeamInviteService.accept_email_invite(str(invite.token), user.id)

        self.assertEqual(result["team_id"], team.id)
        invite.refresh_from_db()
        self.assertEqual(invite.status, "ACCEPTED")
        self.assertTrue(
            TeamMembership.objects.filter(team=team, user=user, status=MembershipStatus.ACTIVE).exists()
        )


class OneTeamPerGameOfferAcceptTests(TestCase):
    def _team(self, name, owner=None, game_id=1):
        return TeamFactory.create_independent(
            created_by=owner or UserFactory(),
            name=name,
            game_id=game_id,
        )

    def test_accept_offer_and_join_conflict_returns_400_and_keeps_offer_sent(self):
        user = UserFactory(username="p0b_offer_conflict")
        team_a = self._team("P0B Offer Team A", game_id=83)
        team_b = self._team("P0B Offer Team B", game_id=83)
        TeamMembershipFactory(team=team_b, user=user, role=MembershipRole.PLAYER)
        join_request = TeamJoinRequest.objects.create(
            team=team_a,
            user=user,
            status=TeamJoinRequest.Status.OFFER_SENT,
        )
        self.client.force_login(user)

        response = self.client.post(
            api_url("team_offer_action", slug=team_a.slug, request_id=join_request.id),
            data='{"action": "accept"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "GAME_TEAM_CONFLICT")
        self.assertFalse(TeamMembership.objects.filter(team=team_a, user=user).exists())
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TeamJoinRequest.Status.OFFER_SENT)

    def test_accept_offer_and_join_without_conflict_succeeds(self):
        user = UserFactory(username="p0b_offer_success")
        team = self._team("P0B Offer Success Team", game_id=84)
        join_request = TeamJoinRequest.objects.create(
            team=team,
            user=user,
            status=TeamJoinRequest.Status.OFFER_SENT,
        )
        self.client.force_login(user)

        response = self.client.post(
            api_url("team_offer_action", slug=team.slug, request_id=join_request.id),
            data='{"action": "accept"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            TeamMembership.objects.filter(team=team, user=user, status=MembershipStatus.ACTIVE).exists()
        )
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, TeamJoinRequest.Status.ACCEPTED)
