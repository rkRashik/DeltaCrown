from django.core.cache import cache
from django.test import TestCase

from apps.organizations.choices import MembershipRole
from apps.organizations.models import OrganizationMembership
from apps.organizations.services.team_detail_context import get_team_detail_context
from apps.organizations.tests.factories import (
    GameFactory,
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


class TeamDetailAuthorityContextTests(TestCase):
    def setUp(self):
        cache.clear()
        self.game = GameFactory()

    def test_superuser_can_report_matches(self):
        superuser = UserFactory(username="tdac_superuser", is_superuser=True)
        team = TeamFactory.create_independent(
            created_by=UserFactory(username="tdac_owner"),
            game_id=self.game.id,
            name="Authority Context Team",
            visibility="PUBLIC",
        )

        context = get_team_detail_context(team_slug=team.slug, viewer=superuser)

        self.assertTrue(context["permissions"]["can_report_matches"])

    def test_coach_and_player_cannot_report_matches(self):
        team = TeamFactory.create_independent(
            created_by=UserFactory(username="tdac_owner_roles"),
            game_id=self.game.id,
            name="Authority Context Roles",
            visibility="PUBLIC",
        )
        coach = UserFactory(username="tdac_coach")
        player = UserFactory(username="tdac_player")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)

        for viewer in (coach, player):
            with self.subTest(viewer=viewer.username):
                cache.clear()
                context = get_team_detail_context(team_slug=team.slug, viewer=viewer)
                self.assertFalse(context["permissions"]["can_report_matches"])

    def test_org_manager_without_team_membership_gets_full_private_team_context(self):
        org = OrganizationFactory()
        org_manager = UserFactory(username="tdac_org_manager")
        OrganizationMembership.objects.create(
            organization=org,
            user=org_manager,
            role="MANAGER",
        )
        team = TeamFactory(
            organization=org,
            created_by=None,
            game_id=self.game.id,
            name="Private Org Team",
            tagline="Private competitive unit",
            visibility="PRIVATE",
        )

        context = get_team_detail_context(team_slug=team.slug, viewer=org_manager)

        self.assertEqual(context["viewer"]["role"], "MANAGER")
        self.assertTrue(context["permissions"]["can_view_private"])
        self.assertTrue(context["permissions"]["can_report_matches"])
        self.assertEqual(context["team"]["tagline"], "Private competitive unit")

    def test_org_scout_and_non_member_remain_restricted_on_private_team(self):
        org = OrganizationFactory()
        scout = UserFactory(username="tdac_org_scout")
        analyst = UserFactory(username="tdac_org_analyst")
        outsider = UserFactory(username="tdac_outsider")
        OrganizationMembership.objects.create(
            organization=org,
            user=scout,
            role="SCOUT",
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=analyst,
            role="ANALYST",
        )
        team = TeamFactory(
            organization=org,
            created_by=None,
            game_id=self.game.id,
            name="Restricted Org Team",
            tagline="Hidden private context",
            visibility="PRIVATE",
        )

        for viewer in (scout, analyst, outsider):
            with self.subTest(viewer=viewer.username):
                cache.clear()
                context = get_team_detail_context(team_slug=team.slug, viewer=viewer)
                self.assertEqual(context["viewer"]["role"], "PUBLIC")
                self.assertFalse(context["permissions"]["can_view_private"])
                self.assertFalse(context["permissions"]["can_report_matches"])
                self.assertNotEqual(
                    context["team"].get("tagline"),
                    "Hidden private context",
                )
