import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import Organization, Team, TeamMembership
from apps.user_profile.models import UserProfile


User = get_user_model()


class TeamPaymentMethodsPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.game = Game.objects.create(name="Treasury Game", slug="treasury-game")
        self.owner = self._user("treasury-owner")
        self.manager = self._user("treasury-manager")
        self.creator = self._user("treasury-creator")
        self.org_ceo = self._user("treasury-org-ceo")
        self.org_creator = self._user("treasury-org-creator")

    def _user(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass123",
        )
        UserProfile.objects.get_or_create(user=user)
        return user

    def _team(self, slug, *, created_by=None, organization=None, status=TeamStatus.ACTIVE):
        return Team.objects.create(
            name=f"Team {slug}",
            tag=slug[:4].upper(),
            slug=slug,
            game_id=self.game.id,
            created_by=created_by or self.owner,
            organization=organization,
            status=status,
            visibility="PUBLIC",
        )

    def _url(self, team):
        return reverse("organizations_api:team_manage_payment_methods", kwargs={"slug": team.slug})

    def _post_payment_method(self, user, team):
        self.client.force_login(user)
        return self.client.post(
            self._url(team),
            data=json.dumps({"method": "bkash", "value": "01712345678"}),
            content_type="application/json",
        )

    def test_owner_can_update_payment_methods(self):
        team = self._team("owner-payments", created_by=self.owner)
        TeamMembership.objects.create(
            team=team,
            user=self.owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

        response = self._post_payment_method(self.owner, team)

        self.assertEqual(response.status_code, 200)
        self.owner.profile.dc_wallet.refresh_from_db()
        self.assertEqual(self.owner.profile.dc_wallet.bkash_number, "01712345678")

    def test_manager_cannot_update_payment_methods(self):
        team = self._team("manager-payments", created_by=self.owner)
        TeamMembership.objects.create(
            team=team,
            user=self.manager,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.ACTIVE,
        )

        response = self._post_payment_method(self.manager, team)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Only the team owner can manage payment methods.")

    def test_org_ceo_can_update_payment_methods_without_team_membership(self):
        org = Organization.objects.create(
            name="Treasury Org",
            slug="treasury-org",
            ceo=self.org_ceo,
        )
        team = self._team("org-ceo-payments", created_by=self.org_creator, organization=org)

        response = self._post_payment_method(self.org_ceo, team)

        self.assertEqual(response.status_code, 200)
        self.org_ceo.profile.dc_wallet.refresh_from_db()
        self.assertEqual(self.org_ceo.profile.dc_wallet.bkash_number, "01712345678")

    def test_team_creator_without_active_membership_can_update_payment_methods(self):
        team = self._team("creator-payments", created_by=self.creator)

        response = self._post_payment_method(self.creator, team)

        self.assertEqual(response.status_code, 200)
        self.creator.profile.dc_wallet.refresh_from_db()
        self.assertEqual(self.creator.profile.dc_wallet.bkash_number, "01712345678")

    def test_inactive_team_cannot_update_payment_methods(self):
        team = self._team(
            "disbanded-payments",
            created_by=self.owner,
            status=TeamStatus.DISBANDED,
        )
        TeamMembership.objects.create(
            team=team,
            user=self.owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

        response = self._post_payment_method(self.owner, team)

        self.assertEqual(response.status_code, 403)
