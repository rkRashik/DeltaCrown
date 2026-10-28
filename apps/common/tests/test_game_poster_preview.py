"""Browsers use small, public-intended previews without modifying originals."""
from types import SimpleNamespace
from django.test import SimpleTestCase, override_settings
from apps.common.game_poster_preview import fast_game_card


class TrackedFile:
    def __init__(self, name, url):
        self.name = name
        self.url = url
    def __bool__(self):
        return True


class GamePosterPreviewTests(SimpleTestCase):
    @override_settings(STATIC_URL="/static/")
    def test_known_card_uses_compact_static_asset(self):
        game = SimpleNamespace(
            slug="valorant",
            card_image=TrackedFile("media/games/cards/Valorant_c4snne",
                                   "/files/games.game/card_image/1/"),
        )
        self.assertIn("img/games/posters/valorant", fast_game_card(game))
        self.assertNotIn("/files/", fast_game_card(game))

    def test_edited_card_preserves_staff_choice_and_governed_url(self):
        game = SimpleNamespace(
            slug="valorant",
            card_image=TrackedFile("media/games/cards/new-staff-art",
                                   "/files/games.game/card_image/1/"),
        )
        self.assertEqual(fast_game_card(game), "/files/games.game/card_image/1/")

    def test_unknown_game_never_uses_someone_elses_thumbnail(self):
        game = SimpleNamespace(
            slug="custom-game",
            card_image=TrackedFile("media/custom-card", "/files/custom/"),
        )
        self.assertEqual(fast_game_card(game), "/files/custom/")

    def test_fc27_uses_fc27_art_not_old_fc26_preview(self):
        game = SimpleNamespace(
            slug="ea-fc",
            card_image=TrackedFile("media/games/cards/fc-27-1nv56_ciqgqr",
                                   "/files/games.game/card_image/4/"),
        )
        self.assertIn("img/games/fc27-key-art", fast_game_card(game))
