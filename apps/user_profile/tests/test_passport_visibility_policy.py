from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.games.models import Game
from apps.user_profile.models import GameProfile
from apps.user_profile.services.career_tab_service import CareerTabService
from apps.user_profile.services.passport_visibility import visible_passport_visibilities
from apps.user_profile.views.legacy_views import profile_view as legacy_profile_view


class PassportVisibilityPolicyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="passport_owner",
            email="passport-owner@example.com",
        )

    def test_none_viewer_gets_public_only(self):
        self.assertEqual(
            visible_passport_visibilities(None, self.owner),
            [GameProfile.VISIBILITY_PUBLIC],
        )

    def test_unauthenticated_viewer_gets_public_only(self):
        self.assertEqual(
            visible_passport_visibilities(AnonymousUser(), self.owner),
            [GameProfile.VISIBILITY_PUBLIC],
        )

    def test_unrelated_authenticated_viewer_gets_public_and_protected(self):
        viewer = User.objects.create_user(
            username="passport_viewer",
            email="passport-viewer@example.com",
        )

        self.assertEqual(
            visible_passport_visibilities(viewer, self.owner),
            [GameProfile.VISIBILITY_PUBLIC, GameProfile.VISIBILITY_PROTECTED],
        )

    def test_owner_gets_all_visibilities(self):
        self.assertEqual(
            visible_passport_visibilities(self.owner, self.owner),
            [
                GameProfile.VISIBILITY_PUBLIC,
                GameProfile.VISIBILITY_PROTECTED,
                GameProfile.VISIBILITY_PRIVATE,
            ],
        )

    def test_staff_viewer_gets_all_visibilities(self):
        staff = User.objects.create_superuser(
            username="passport_staff",
            email="passport-staff@example.com",
            password="test-pass",
        )

        self.assertEqual(
            visible_passport_visibilities(staff, self.owner),
            [
                GameProfile.VISIBILITY_PUBLIC,
                GameProfile.VISIBILITY_PROTECTED,
                GameProfile.VISIBILITY_PRIVATE,
            ],
        )


class CareerTabPassportSortSourceTests(TestCase):
    def test_duplicate_passport_fallback_uses_explicit_visibility_priority(self):
        source = Path(settings.BASE_DIR) / "apps/user_profile/services/career_tab_service.py"
        text = source.read_text(encoding="utf-8")

        self.assertIn("When(visibility=GameProfile.VISIBILITY_PUBLIC, then=0)", text)
        self.assertIn("When(visibility=GameProfile.VISIBILITY_PROTECTED, then=1)", text)
        self.assertIn("When(visibility=GameProfile.VISIBILITY_PRIVATE, then=2)", text)
        self.assertNotIn(".order_by('visibility').first()", text)


class PassportVisibilityReadPathTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            username="passport_path_owner",
            email="passport-path-owner@example.com",
        )
        self.viewer = User.objects.create_user(
            username="passport_path_viewer",
            email="passport-path-viewer@example.com",
        )
        self.public_game = self._create_game("passport-public", "PPUB")
        self.protected_game = self._create_game("passport-protected", "PPRO")
        self.private_game = self._create_game("passport-private", "PPRI")
        self.suspended_game = self._create_game("passport-suspended", "PSUS")

        self._create_passport(
            self.public_game,
            GameProfile.VISIBILITY_PUBLIC,
            "PublicPlayer",
        )
        self._create_passport(
            self.protected_game,
            GameProfile.VISIBILITY_PROTECTED,
            "ProtectedPlayer",
        )
        self._create_passport(
            self.private_game,
            GameProfile.VISIBILITY_PRIVATE,
            "PrivatePlayer",
        )
        self._create_passport(
            self.suspended_game,
            GameProfile.VISIBILITY_PUBLIC,
            "SuspendedPlayer",
            status=GameProfile.STATUS_SUSPENDED,
        )

    def _create_game(self, slug, short_code):
        return Game.objects.create(
            name=slug.title(),
            display_name=slug.title(),
            slug=slug,
            short_code=short_code,
            category="FPS",
            platforms=["PC"],
            is_passport_supported=True,
        )

    def _create_passport(self, game, visibility, in_game_name, status=GameProfile.STATUS_ACTIVE):
        return GameProfile.objects.create(
            user=self.owner,
            game=game,
            in_game_name=in_game_name,
            visibility=visibility,
            status=status,
        )

    def _linked_game_slugs(self, viewer):
        return {
            item["game_slug"]
            for item in CareerTabService.get_linked_games(self.owner.profile, viewer=viewer)
        }

    def _legacy_game_profile_context(self, viewer):
        request = self.factory.get(f"/legacy/@{self.owner.username}/")
        request.user = viewer

        with patch(
            "apps.user_profile.views.legacy_views.render",
            return_value=HttpResponse("ok"),
        ) as render_mock:
            response = legacy_profile_view(request, username=self.owner.username)

        self.assertEqual(response.status_code, 200)
        return render_mock.call_args.args[2]["game_profiles"]

    def test_career_tab_anonymous_viewer_sees_public_only(self):
        self.assertEqual(
            self._linked_game_slugs(None),
            {self.public_game.slug},
        )

    def test_career_tab_authenticated_non_owner_sees_public_and_protected(self):
        self.assertEqual(
            self._linked_game_slugs(self.viewer),
            {self.public_game.slug, self.protected_game.slug},
        )

    def test_career_tab_owner_sees_public_protected_and_private(self):
        self.assertEqual(
            self._linked_game_slugs(self.owner),
            {self.public_game.slug, self.protected_game.slug, self.private_game.slug},
        )

    def test_legacy_profile_non_owner_does_not_see_private_passport(self):
        game_profiles = list(self._legacy_game_profile_context(self.viewer))
        self.assertEqual(
            {passport.game_id for passport in game_profiles},
            {self.public_game.id, self.protected_game.id},
        )

    def test_legacy_profile_authenticated_non_owner_can_see_protected(self):
        game_profiles = list(self._legacy_game_profile_context(self.viewer))
        self.assertIn(
            self.protected_game.id,
            {passport.game_id for passport in game_profiles},
        )

    def test_legacy_profile_owner_can_see_private(self):
        game_profiles = list(self._legacy_game_profile_context(self.owner))
        self.assertEqual(
            {passport.game_id for passport in game_profiles},
            {self.public_game.id, self.protected_game.id, self.private_game.id},
        )

    def test_suspended_passport_hidden_regardless_of_visibility(self):
        self.assertNotIn(self.suspended_game.slug, self._linked_game_slugs(self.owner))
        game_profiles = list(self._legacy_game_profile_context(self.owner))
        self.assertNotIn(
            self.suspended_game.id,
            {passport.game_id for passport in game_profiles},
        )
