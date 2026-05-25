from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from apps.organizations.choices import MembershipRole
from apps.organizations.models import Team
from apps.organizations.templatetags.org_media import safe_href
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


class SafeHrefFilterTests(TestCase):
    def test_safe_href_allows_valid_https_url(self):
        self.assertEqual(
            safe_href("https://x.com/deltacrown"),
            "https://x.com/deltacrown",
        )

    def test_safe_href_allows_valid_http_url(self):
        self.assertEqual(
            safe_href("http://example.com/team"),
            "http://example.com/team",
        )

    def test_safe_href_rejects_javascript_url(self):
        self.assertEqual(safe_href("javascript:alert(1)"), "")

    def test_safe_href_rejects_data_url(self):
        self.assertEqual(safe_href("data:text/html;base64,PHNjcmlwdA=="), "")

    def test_safe_href_rejects_ftp_url(self):
        self.assertEqual(safe_href("ftp://example.com/team"), "")

    def test_safe_href_rejects_blank_and_none(self):
        self.assertEqual(safe_href(""), "")
        self.assertEqual(safe_href(None), "")


class TeamSocialHrefRenderTests(TestCase):
    def setUp(self):
        cache.clear()
        self.game = GameFactory()
        self.owner = UserFactory()
        self.team = TeamFactory.create_independent(
            created_by=self.owner,
            game_id=self.game.id,
            name="Social Href Safety",
        )
        TeamMembershipFactory(
            team=self.team,
            user=self.owner,
            role=MembershipRole.OWNER,
        )

    def detail_response(self):
        return self.client.get(
            reverse("organizations:team_detail", kwargs={"team_slug": self.team.slug})
        )

    def set_team_urls(self, **kwargs):
        Team.objects.filter(pk=self.team.pk).update(**kwargs)
        self.team.refresh_from_db()

    def test_public_team_detail_renders_valid_twitter_href(self):
        self.set_team_urls(twitter_url="https://x.com/deltacrown")

        response = self.detail_response()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="https://x.com/deltacrown"')

    def test_public_team_detail_does_not_render_javascript_twitter_href(self):
        self.set_team_urls(twitter_url="javascript:alert(1)")

        response = self.detail_response()

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="javascript:alert(1)"')

    def test_public_team_detail_does_not_render_data_or_ftp_social_hrefs(self):
        self.set_team_urls(
            twitter_url="data:text/html;base64,PHNjcmlwdA==",
            discord_url="ftp://discord.gg/teamabc",
        )

        response = self.detail_response()

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="data:text/html;base64,PHNjcmlwdA=="')
        self.assertNotContains(response, 'href="ftp://discord.gg/teamabc"')

    def test_public_team_detail_renders_valid_discord_invite_href(self):
        self.set_team_urls(discord_url="https://discord.gg/teamabc")

        response = self.detail_response()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="https://discord.gg/teamabc"')

    def test_public_team_detail_does_not_render_invalid_discord_scheme_href(self):
        self.set_team_urls(discord_url="javascript:alert(1)")

        response = self.detail_response()

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="javascript:alert(1)"')
