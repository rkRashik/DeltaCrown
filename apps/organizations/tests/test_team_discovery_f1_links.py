from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.games.models import Game
from apps.organizations.choices import TeamStatus
from apps.organizations.models import Team


class TeamDiscoveryF1LinkTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="discovery_f1_user",
            email="discovery-f1@example.com",
            password="testpass123",
        )
        self.game = Game.objects.create(
            name="Discovery F1 Game",
            display_name="Discovery F1",
            slug="discovery-f1",
            short_code="DF1",
            category="FPS",
            game_type="TEAM_VS_TEAM",
            platforms=["PC"],
            is_active=True,
        )
        Team.objects.create(
            name="Discovery F1 Team",
            slug="discovery-f1-team",
            tag="DF1",
            created_by=self.user,
            game_id=self.game.id,
            region="Bangladesh",
            status=TeamStatus.ACTIVE,
            visibility="PUBLIC",
            is_recruiting=True,
            description="Recruiting for the focused F1 link regression test.",
        )

    def test_hub_recruiting_links_use_find_team_route(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("organizations:vnext_hub"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        expected_href = 'href="/teams/find/"'
        self.assertGreaterEqual(html.count(expected_href), 2)
        self.assertNotIn('href="/teams/directory/?filter=recruiting"', html)
        self.assertNotIn('href="/teams?filter=recruiting"', html)
