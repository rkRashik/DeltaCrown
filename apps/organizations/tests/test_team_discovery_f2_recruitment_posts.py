from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.games.models import Game
from apps.organizations.choices import TeamStatus
from apps.organizations.models import Team
from apps.organizations.models.recruitment import RecruitmentPosition
from apps.user_profile.models import CareerProfile, GameProfile, UserProfile


class TeamDiscoveryF2RecruitmentPostTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="discovery_f2_user",
            email="discovery-f2@example.com",
            password="testpass123",
        )
        self.game = Game.objects.create(
            name="Discovery F2 Game",
            display_name="Discovery F2",
            slug="discovery-f2",
            short_code="DF2",
            category="FPS",
            game_type="TEAM_VS_TEAM",
            platforms=["PC"],
            is_active=True,
        )

    def _team(self, name, slug, *, description="Generic recruiting description."):
        return Team.objects.create(
            name=name,
            slug=slug,
            tag=f"T{Team.objects.count() + 1:04d}",
            created_by=self.user,
            game_id=self.game.id,
            region="Bangladesh",
            status=TeamStatus.ACTIVE,
            visibility="PUBLIC",
            is_recruiting=True,
            description=description,
        )

    def _position(
        self,
        team,
        title,
        *,
        is_active=True,
        platform="PC",
        sort_order=0,
        short_pitch="Reads site hits before they happen.",
    ):
        return RecruitmentPosition.objects.create(
            team=team,
            title=title,
            role_category=RecruitmentPosition.RoleCategory.INITIATOR,
            rank_requirement="Diamond+",
            region="Bangladesh",
            platform=platform,
            short_pitch=short_pitch,
            sort_order=sort_order,
            is_active=is_active,
        )

    def _lft_player(
        self,
        username,
        *,
        display_name=None,
        lft_enabled=True,
        recruiter_visibility="PUBLIC",
        career_status="LOOKING",
        roles=None,
        passport_visibility=None,
        passport_status=GameProfile.STATUS_ACTIVE,
        passport_rank="Diamond 2",
        passport_platform="PC",
        passport_is_lft=True,
    ):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = display_name or username.replace("_", " ").title()
        profile.save(update_fields=["display_name"])
        CareerProfile.objects.update_or_create(
            user_profile=profile,
            defaults={
                "career_status": career_status,
                "lft_enabled": lft_enabled,
                "primary_roles": roles or ["IGL", "Support"],
                "secondary_roles": ["Flex"],
                "preferred_region": "BD",
                "availability": "WEEKENDS",
                "recruiter_visibility": recruiter_visibility,
            },
        )
        if passport_visibility:
            GameProfile.objects.create(
                user=user,
                game=self.game,
                ign=f"{username}Main",
                in_game_name=f"{username}#123",
                rank_name=passport_rank,
                rank_tier=7,
                main_role="Initiator",
                platform=passport_platform,
                region="BD",
                visibility=passport_visibility,
                status=passport_status,
                is_lft=passport_is_lft,
            )
        return user

    def _hub_html(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("organizations:vnext_hub"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_hub_scouting_card_renders_active_recruitment_position_summary(self):
        team = self._team("Protocol V", "protocol-v")
        self._position(team, "Tactical Scanner", short_pitch="Please do not flash us.")

        html = self._hub_html()

        self.assertIn("Tactical Scanner", html)
        self.assertIn("Please do not flash us.", html)
        self.assertIn("Diamond+", html)
        self.assertIn('/teams/protocol-v/', html)

    def test_hub_scouting_card_falls_back_to_team_description_without_position(self):
        self._team(
            "Fallback Squad",
            "fallback-squad",
            description="Fallback description for teams without open recruitment posts.",
        )

        html = self._hub_html()

        self.assertIn("Fallback description for teams without open recruitment posts.", html)

    def test_hub_scouting_card_does_not_render_inactive_recruitment_position(self):
        team = self._team(
            "Inactive Position Squad",
            "inactive-position-squad",
            description="Fallback text when inactive recruitment posts are hidden.",
        )
        self._position(team, "Inactive Tactical Scanner", is_active=False)

        html = self._hub_html()

        self.assertNotIn("Inactive Tactical Scanner", html)
        self.assertIn("Fallback text when inactive recruitment posts are hidden.", html)

    def test_recruiting_directory_renders_active_recruitment_position_summary(self):
        team = self._team("Directory Protocol", "directory-protocol")
        self._position(team, "Directory IGL", short_pitch="Shot-calling role open.")
        self._position(team, "Directory Support", sort_order=1, short_pitch="Utility role open.")

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Find Team", html)
        self.assertIn("Scouting Grounds", html)
        self.assertIn("Filter by game, region, platform, or search", html)
        self.assertIn("Directory IGL", html)
        self.assertIn("Shot-calling role open.", html)
        self.assertIn("Diamond+", html)
        self.assertIn("2 roles", html)
        self.assertIn("View &amp; Apply", html)

    def test_recruiting_directory_does_not_render_inactive_recruitment_position(self):
        team = self._team(
            "Directory Inactive Squad",
            "directory-inactive-squad",
            description="Directory fallback text for inactive recruitment posts.",
        )
        self._position(team, "Directory Inactive IGL", is_active=False)

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("Directory Inactive IGL", html)
        self.assertIn("Directory fallback text for inactive recruitment posts.", html)

    def test_recruiting_directory_falls_back_to_team_description_without_position(self):
        self._team(
            "Directory Fallback Squad",
            "directory-fallback-squad",
            description="Directory fallback copy for a recruiting team without active posts.",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Directory fallback copy for a recruiting team without active posts.",
            response.content.decode(),
        )

    def test_generic_directory_mode_is_preserved_without_recruiting_filter(self):
        self._team("Generic Directory Squad", "generic-directory-squad")

        response = self.client.get(reverse("organizations:team_directory"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Team Directory", html)
        self.assertNotIn("Players Looking For Team", html)
        self.assertNotIn("Scouting Grounds shows public teams that are actively recruiting", html)

    def test_recruiting_directory_platform_filter_matches_recruitment_position(self):
        pc_team = self._team("PC Protocol", "pc-protocol")
        self._position(pc_team, "PC Controller", platform="PC")
        mobile_team = self._team("Mobile Protocol", "mobile-protocol")
        self._position(mobile_team, "Mobile Scanner", platform="Mobile")

        response = self.client.get(
            reverse("organizations:team_directory") + "?filter=recruiting&platform=Mobile"
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Mobile Scanner", html)
        self.assertNotIn("PC Controller", html)

    def test_recruiting_directory_available_players_shows_public_profiles_only(self):
        public_user = get_user_model().objects.create_user(
            username="public_lft_player",
            email="public-lft@example.com",
            password="testpass123",
        )
        private_user = get_user_model().objects.create_user(
            username="private_lft_player",
            email="private-lft@example.com",
            password="testpass123",
        )
        public_profile, _ = UserProfile.objects.get_or_create(user=public_user)
        private_profile, _ = UserProfile.objects.get_or_create(user=private_user)
        public_profile.display_name = "Public LFT Player"
        private_profile.display_name = "Private LFT Player"
        public_profile.save(update_fields=["display_name"])
        private_profile.save(update_fields=["display_name"])
        CareerProfile.objects.update_or_create(
            user_profile=public_profile,
            defaults={
                "career_status": "LOOKING",
                "lft_enabled": True,
                "primary_roles": ["IGL", "Support"],
                "preferred_region": "BD",
                "availability": "WEEKENDS",
                "recruiter_visibility": "PUBLIC",
            },
        )
        CareerProfile.objects.update_or_create(
            user_profile=private_profile,
            defaults={
                "career_status": "LOOKING",
                "lft_enabled": True,
                "primary_roles": ["Duelist"],
                "preferred_region": "BD",
                "availability": "WEEKENDS",
                "recruiter_visibility": "PRIVATE",
            },
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Players Looking For Team", html)
        self.assertIn("Public LFT Player", html)
        self.assertIn("/@public_lft_player/", html)
        self.assertIn("IGL", html)
        self.assertNotIn("Private LFT Player", html)

    def test_recruiting_directory_available_player_shows_public_passport_summary(self):
        self._lft_player(
            "passport_lft_player",
            display_name="Passport LFT Player",
            passport_visibility=GameProfile.VISIBILITY_PUBLIC,
            passport_rank="Ascendant 1",
            passport_platform="PC",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Passport LFT Player", html)
        self.assertIn("Discovery F2", html)
        self.assertIn("passport_lft_player#123", html)
        self.assertIn("Ascendant 1", html)
        self.assertIn("Initiator", html)
        self.assertIn("PC", html)

    def test_recruiting_directory_hides_lft_disabled_career_profile(self):
        self._lft_player(
            "not_lft_player",
            display_name="Not LFT Player",
            lft_enabled=False,
            passport_visibility=GameProfile.VISIBILITY_PUBLIC,
            passport_rank="Hidden Rank",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("Not LFT Player", html)
        self.assertNotIn("Hidden Rank", html)

    def test_recruiting_directory_hides_private_game_profile_data(self):
        self._lft_player(
            "private_passport_player",
            display_name="Private Passport Player",
            passport_visibility=GameProfile.VISIBILITY_PRIVATE,
            passport_rank="Private Immortal",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Private Passport Player", html)
        self.assertNotIn("private_passport_player#123", html)
        self.assertNotIn("Private Immortal", html)

    def test_recruiting_directory_hides_protected_game_profile_data(self):
        self._lft_player(
            "protected_passport_player",
            display_name="Protected Passport Player",
            passport_visibility=GameProfile.VISIBILITY_PROTECTED,
            passport_rank="Protected Immortal",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Protected Passport Player", html)
        self.assertNotIn("protected_passport_player#123", html)
        self.assertNotIn("Protected Immortal", html)

    def test_recruiting_directory_hides_suspended_game_profile_data(self):
        self._lft_player(
            "suspended_passport_player",
            display_name="Suspended Passport Player",
            passport_visibility=GameProfile.VISIBILITY_PUBLIC,
            passport_status=GameProfile.STATUS_SUSPENDED,
            passport_rank="Suspended Radiant",
        )

        response = self.client.get(reverse("organizations:team_directory") + "?filter=recruiting")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Suspended Passport Player", html)
        self.assertNotIn("suspended_passport_player#123", html)
        self.assertNotIn("Suspended Radiant", html)
