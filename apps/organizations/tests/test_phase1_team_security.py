import json
from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership, Team
from apps.organizations.permissions import can_view_team
from apps.organizations.tests.factories import (
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


class TeamManagePhase1PermissionsTests(TestCase):
    def test_org_ceo_and_manager_can_load_bootstrap_without_admins_relation(self):
        ceo = UserFactory(username="phase1_ceo")
        org_manager = UserFactory(username="phase1_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Phase One Org Team")

        for user in (ceo, org_manager):
            self.client.force_login(user)
            response = self.client.get(api_url("team_manage_detail", slug=team.slug))
            self.assertEqual(response.status_code, 200)

    def test_coach_can_access_hq_page_but_not_sensitive_mutation_apis(self):
        owner = UserFactory(username="phase1_owner")
        coach = UserFactory(username="phase1_coach")
        team = TeamFactory.create_independent(created_by=owner, name="Phase One Coach Team")
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        self.client.force_login(coach)
        manage_response = self.client.get(reverse("organizations:team_manage", kwargs={"team_slug": team.slug}))
        self.assertEqual(manage_response.status_code, 200)

        payload = json.dumps({"tagline": "coach edit attempt"})
        for name in ("team_manage_update_profile", "team_manage_update_settings", "team_discord_config_save"):
            response = self.client.post(
                api_url(name, slug=team.slug),
                data=payload,
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 403)

    def test_active_owner_and_manager_can_mutate_profile(self):
        owner = UserFactory(username="phase1_active_owner")
        manager = UserFactory(username="phase1_active_manager")
        team = TeamFactory.create_independent(created_by=owner, name="Phase One Active Admin Team")
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)

        for user in (owner, manager):
            self.client.force_login(user)
            response = self.client.post(
                api_url("team_manage_update_profile", slug=team.slug),
                data=json.dumps({"tagline": f"updated by {user.username}"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

    def test_inactive_manager_cannot_mutate(self):
        self._assert_stale_admin_cannot_mutate(MembershipStatus.INACTIVE)

    def test_suspended_owner_membership_cannot_mutate(self):
        self._assert_stale_admin_cannot_mutate(MembershipStatus.SUSPENDED, role=MembershipRole.OWNER)

    def test_removed_manager_cannot_mutate(self):
        self._assert_stale_admin_cannot_mutate(MembershipStatus.REMOVED)

    def _assert_stale_admin_cannot_mutate(self, status, role=MembershipRole.MANAGER):
        owner = UserFactory(username=f"phase1_owner_{status.lower()}")
        stale_admin = UserFactory(username=f"phase1_stale_{status.lower()}")
        team = TeamFactory.create_independent(created_by=owner, name=f"Phase One {status} Team")
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        TeamMembershipFactory(team=team, user=stale_admin, role=role, status=status)

        self.client.force_login(stale_admin)
        response = self.client.post(
            api_url("team_manage_update_profile", slug=team.slug),
            data=json.dumps({"tagline": "stale edit attempt"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_manage_page_rejects_inactive_team(self):
        owner = UserFactory(username="phase1_inactive_team_owner")
        team = TeamFactory.create_independent(created_by=owner, name="Phase One Disbanded Team")
        team.status = TeamStatus.DISBANDED
        team.save(update_fields=["status"])
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)

        self.client.force_login(owner)
        response = self.client.get(reverse("organizations:team_manage", kwargs={"team_slug": team.slug}))
        self.assertEqual(response.status_code, 302)


class BootstrapLeakageTests(TestCase):
    def test_bootstrap_returns_active_members_only_without_email_or_raw_webhook(self):
        owner = UserFactory(username="phase1_bootstrap_owner", email="owner@example.com")
        active = UserFactory(username="phase1_bootstrap_active", email="active@example.com")
        inactive = UserFactory(username="phase1_bootstrap_inactive", email="inactive@example.com")
        team = TeamFactory.create_independent(created_by=owner, name="Phase One Bootstrap Team")
        team.discord_webhook_url = "https://discord.com/api/webhooks/123/token"
        team.save(update_fields=["discord_webhook_url"])
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        TeamMembershipFactory(team=team, user=active, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=inactive, role=MembershipRole.PLAYER, status=MembershipStatus.INACTIVE)

        self.client.force_login(owner)
        response = self.client.get(api_url("team_manage_detail", slug=team.slug))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        usernames = {member["username"] for member in data["members"]}
        self.assertIn(active.username, usernames)
        self.assertNotIn(inactive.username, usernames)
        self.assertTrue(all("email" not in member for member in data["members"]))
        self.assertNotIn("discord_webhook_url", data["team"])
        self.assertIs(data["team"]["has_webhook"], True)
        self.assertTrue(data["team"]["discord_webhook_url_masked"])


class DiscordWebhookSSRFValidationTests(TestCase):
    def setUp(self):
        self.owner = UserFactory(username="phase1_webhook_owner")
        self.team = TeamFactory.create_independent(created_by=self.owner, name="Phase One Webhook Team")
        TeamMembershipFactory(team=self.team, user=self.owner, role=MembershipRole.OWNER)
        self.client.force_login(self.owner)

    def _post_test_webhook(self):
        return self.client.post(api_url("team_discord_test_webhook", slug=self.team.slug))

    @patch("requests.post")
    def test_valid_discord_webhook_reaches_requests_post(self, mock_post):
        self.team.discord_webhook_url = "https://discord.com/api/webhooks/123/token"
        self.team.save(update_fields=["discord_webhook_url"])
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        response = self._post_test_webhook()

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "https://discord.com/api/webhooks/123/token")

    @patch("requests.post")
    def test_rejects_non_https_discord_webhook(self, mock_post):
        self._assert_webhook_rejected("http://discord.com/api/webhooks/123/token", mock_post)

    @patch("requests.post")
    def test_rejects_non_discord_host(self, mock_post):
        self._assert_webhook_rejected("https://evil.com/api/webhooks/123/token", mock_post)

    @patch("requests.post")
    def test_rejects_discord_host_suffix_trick(self, mock_post):
        self._assert_webhook_rejected("https://discord.com.evil.com/api/webhooks/123/token", mock_post)

    @patch("requests.post")
    def test_rejects_non_webhook_discord_path(self, mock_post):
        self._assert_webhook_rejected("https://discord.com/not-webhook/123/token", mock_post)

    @patch("requests.post")
    def test_blank_webhook_keeps_existing_bad_request_behavior(self, mock_post):
        self.team.discord_webhook_url = ""
        self.team.save(update_fields=["discord_webhook_url"])

        response = self._post_test_webhook()

        self.assertEqual(response.status_code, 400)
        self.assertIn("No webhook URL configured", response.json()["error"])
        mock_post.assert_not_called()

    def _assert_webhook_rejected(self, webhook_url, mock_post):
        self.team.discord_webhook_url = webhook_url
        self.team.save(update_fields=["discord_webhook_url"])

        response = self._post_test_webhook()

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid Discord webhook URL", response.json()["error"])
        self.assertNotIn(webhook_url, response.content.decode())
        mock_post.assert_not_called()


class MemberRemovalGuardTests(TestCase):
    def test_cannot_remove_last_active_member_when_historical_rows_exist(self):
        ceo = UserFactory(username="phase1_remove_ceo")
        active = UserFactory(username="phase1_remove_active")
        historical = UserFactory(username="phase1_remove_historical")
        org = OrganizationFactory(ceo=ceo)
        team = TeamFactory(organization=org, created_by=None, name="Phase One Last Active Team")
        active_membership = TeamMembershipFactory(team=team, user=active, role=MembershipRole.PLAYER)
        TeamMembershipFactory(
            team=team,
            user=historical,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.INACTIVE,
        )

        self.client.force_login(ceo)
        response = self.client.post(api_url("team_manage_remove_member", slug=team.slug, membership_id=active_membership.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("last active member", response.json()["error"].lower())

    def test_can_remove_one_member_when_another_active_member_remains(self):
        ceo = UserFactory(username="phase1_remove_ceo_two")
        player_one = UserFactory(username="phase1_remove_one")
        player_two = UserFactory(username="phase1_remove_two")
        historical = UserFactory(username="phase1_remove_historical_two")
        org = OrganizationFactory(ceo=ceo)
        team = TeamFactory(organization=org, created_by=None, name="Phase One Two Active Team")
        membership = TeamMembershipFactory(team=team, user=player_one, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=player_two, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=historical, role=MembershipRole.PLAYER, status=MembershipStatus.INACTIVE)

        self.client.force_login(ceo)
        response = self.client.post(api_url("team_manage_remove_member", slug=team.slug, membership_id=membership.id))
        self.assertEqual(response.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.status, MembershipStatus.INACTIVE)


class PrivateIndependentTeamPermissionsTests(TestCase):
    def test_private_independent_team_view_permission_does_not_crash(self):
        owner = UserFactory(username="phase1_private_owner")
        outsider = UserFactory(username="phase1_private_outsider")
        member = UserFactory(username="phase1_private_member")
        team = TeamFactory.create_independent(
            created_by=owner,
            name="Phase One Private Team",
            visibility="PRIVATE",
        )
        TeamMembershipFactory(team=team, user=member, role=MembershipRole.PLAYER)

        self.assertIs(can_view_team(AnonymousUser(), team), False)
        self.assertIs(can_view_team(outsider, team), False)
        self.assertIs(can_view_team(member, team), True)
        self.assertIs(can_view_team(owner, team), True)


class TeamLightboxSourceSafetyTests(SimpleTestCase):
    def test_lightbox_no_dynamic_media_innerhtml(self):
        source = Path(settings.BASE_DIR) / "templates/organizations/team/partials/_scripts.html"
        with source.open(encoding="utf-8") as handle:
            body = handle.read()
        lightbox_body = body.split("function dcOpenLightbox", 1)[1].split("function dcCloseLightbox", 1)[0]
        self.assertNotIn("content.innerHTML", lightbox_body)
        self.assertIn("document.createElement", lightbox_body)
        self.assertIn("safeMediaUrl", lightbox_body)

    def test_discord_templates_do_not_render_raw_webhook_value(self):
        for relative in (
            "templates/organizations/team/manage_hq/partials/_section_discord.html",
            "templates/organizations/team/manage_hq/partials/_section_team_profile.html",
        ):
            source = Path(settings.BASE_DIR) / relative
            body = source.read_text(encoding="utf-8")
            self.assertNotIn('value="{{ team.discord_webhook_url', body)


class TeamColorValidationTests(SimpleTestCase):
    def test_model_accepts_valid_team_colors(self):
        team = Team(name="Color Valid", slug="color-valid", game_id=1, region="NA")
        team.primary_color = "#3B82F6"
        team.accent_color = "#3BF"
        team.clean_fields(exclude=["organization", "created_by"])

    def test_model_rejects_invalid_team_colors(self):
        for color in ["red", "#zzzzzz", "javascript:alert(1)", "#12345", "#1234567"]:
            team = Team(name="Color Invalid", slug="color-invalid", game_id=1, region="NA")
            team.primary_color = color
            with self.assertRaises(ValidationError):
                team.clean_fields(exclude=["organization", "created_by"])
