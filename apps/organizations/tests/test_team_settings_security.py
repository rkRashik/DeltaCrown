import json

from django.test import TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import TeamMembership
from apps.organizations.tests.factories import TeamFactory, TeamMembershipFactory, UserFactory


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


def json_body(data):
    return json.dumps(data)


class TeamSettingsUrlSecurityTests(TestCase):
    def setUp(self):
        self.owner = UserFactory(username="settings_security_owner")
        self.team = TeamFactory.create_independent(
            created_by=self.owner,
            name="Settings Security Team",
        )
        TeamMembershipFactory(
            team=self.team,
            user=self.owner,
            role=MembershipRole.OWNER,
        )
        self.client.force_login(self.owner)

    def post_json(self, route_name, payload):
        return self.client.post(
            api_url(route_name, slug=self.team.slug),
            data=json_body(payload),
            content_type="application/json",
        )

    def refresh_team(self):
        self.team.refresh_from_db()
        return self.team

    def test_update_profile_rejects_javascript_social_url(self):
        self.team.twitter_url = "https://x.com/safe"
        self.team.save(update_fields=["twitter_url"])

        response = self.post_json(
            "team_manage_update_profile",
            {"twitter_url": "javascript:alert(1)"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refresh_team().twitter_url, "https://x.com/safe")

    def test_update_profile_rejects_non_discord_webhook_url(self):
        self.team.discord_webhook_url = "https://discord.com/api/webhooks/1/token"
        self.team.save(update_fields=["discord_webhook_url"])

        response = self.post_json(
            "team_manage_update_profile",
            {"discord_webhook_url": "https://evil.com/collect"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.refresh_team().discord_webhook_url,
            "https://discord.com/api/webhooks/1/token",
        )

    def test_discord_config_save_rejects_non_discord_webhook_url(self):
        self.team.discord_webhook_url = "https://discord.com/api/webhooks/1/token"
        self.team.save(update_fields=["discord_webhook_url"])

        response = self.post_json(
            "team_discord_config_save",
            {"discord_webhook_url": "https://attacker.com/"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.refresh_team().discord_webhook_url,
            "https://discord.com/api/webhooks/1/token",
        )

    def test_update_settings_rejects_non_discord_invite_url(self):
        self.team.discord_url = "https://discord.gg/safe"
        self.team.save(update_fields=["discord_url"])

        response = self.post_json(
            "team_manage_update_settings",
            {"discord": "https://not-discord.com/invite/abc"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refresh_team().discord_url, "https://discord.gg/safe")

    def test_update_profile_accepts_valid_social_urls(self):
        response = self.post_json(
            "team_manage_update_profile",
            {
                "twitter_url": "https://x.com/deltacrown",
                "instagram_url": "https://instagram.com/deltacrown",
                "website_url": "https://deltacrown.example",
                "youtube_url": "http://youtube.com/@deltacrown",
            },
        )

        self.assertEqual(response.status_code, 200)
        team = self.refresh_team()
        self.assertEqual(team.twitter_url, "https://x.com/deltacrown")
        self.assertEqual(team.instagram_url, "https://instagram.com/deltacrown")
        self.assertEqual(team.website_url, "https://deltacrown.example")
        self.assertEqual(team.youtube_url, "http://youtube.com/@deltacrown")

    def test_valid_discord_invite_url_is_accepted(self):
        response = self.post_json(
            "team_manage_update_profile",
            {"discord_url": "https://discord.com/invite/abc123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.refresh_team().discord_url,
            "https://discord.com/invite/abc123",
        )

        response = self.post_json(
            "team_manage_update_settings",
            {"discord": "https://discord.gg/teamabc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.refresh_team().discord_url, "https://discord.gg/teamabc")

    def test_empty_string_clears_url_field(self):
        self.team.website_url = "https://deltacrown.example"
        self.team.discord_url = "https://discord.gg/safe"
        self.team.discord_webhook_url = "https://discord.com/api/webhooks/1/token"
        self.team.save(update_fields=["website_url", "discord_url", "discord_webhook_url"])

        response = self.post_json(
            "team_manage_update_profile",
            {
                "website_url": "",
                "discord_url": "",
                "discord_webhook_url": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        team = self.refresh_team()
        self.assertEqual(team.website_url, "")
        self.assertEqual(team.discord_url, "")
        self.assertEqual(team.discord_webhook_url, "")

    def test_update_profile_tagline_exactly_140_accepted(self):
        tagline = "x" * 140

        response = self.post_json(
            "team_manage_update_profile",
            {"tagline": tagline},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.refresh_team().tagline, tagline)

    def test_update_profile_tagline_141_chars_rejected(self):
        self.team.tagline = "safe"
        self.team.save(update_fields=["tagline"])

        response = self.post_json(
            "team_manage_update_profile",
            {"tagline": "x" * 141},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refresh_team().tagline, "safe")

    def test_update_settings_tagline_140_accepted(self):
        tagline = "x" * 140

        response = self.post_json(
            "team_manage_update_settings",
            {"tagline": tagline},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.refresh_team().tagline, tagline)

    def test_add_member_bypasses_roster_lock(self):
        target_user = UserFactory(username="locked_admin_add_target")
        applicant = UserFactory(username="locked_apply_target")
        self.team.roster_locked = True
        self.team.save(update_fields=["roster_locked"])

        add_response = self.post_json(
            "team_manage_add_member",
            {
                "identifier": target_user.username,
                "role": MembershipRole.PLAYER,
            },
        )

        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(
            TeamMembership.objects.filter(
                team=self.team,
                user=target_user,
                status=MembershipStatus.ACTIVE,
            ).exists()
        )

        self.client.force_login(applicant)
        apply_response = self.post_json(
            "team_apply",
            {"message": "Let me in"},
        )

        self.assertEqual(apply_response.status_code, 400)
        self.assertIn("locked", apply_response.json()["error"].lower())

    def test_invite_code_visible_to_non_admin_member(self):
        player = UserFactory(username="invite_code_player")
        TeamMembershipFactory(
            team=self.team,
            user=player,
            role=MembershipRole.PLAYER,
        )
        self.team.invite_code = "share-code-123"
        self.team.save(update_fields=["invite_code"])

        self.client.force_login(player)
        response = self.client.get(api_url("team_manage_detail", slug=self.team.slug))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["team"]["invite_code"], "share-code-123")
