"""/teams/ rendered one Game query per team card (Team.game_obj, OL-10b): now one per minute per process."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.organizations.models import team as team_module
from apps.organizations.models.team import Team


class TeamGameLookupTests(SimpleTestCase):
    def setUp(self):
        team_module._games.update(at=-1e9, by_pk={})

    def test_many_teams_share_one_games_query_and_get_independent_copies(self):
        games = [SimpleNamespace(pk=1, display_name="A"), SimpleNamespace(pk=2, display_name="B")]
        with patch("apps.games.models.Game.objects") as manager:
            manager.all.return_value = games
            teams = [Team(game_id=1 + i % 2) for i in range(12)]
            names = [t.get_game_display() for t in teams]
        self.assertEqual(names, ["A", "B"] * 6)
        manager.all.assert_called_once()
        manager.get.assert_not_called()
        teams[0].game_obj.display_name = "mutated"
        self.assertEqual(teams[2].game_obj.display_name, "A")  # shared cache is never mutated by callers

    def test_unknown_game_falls_back_to_a_direct_lookup_and_failure_stays_none(self):
        with patch("apps.games.models.Game.objects") as manager:
            manager.all.return_value = []
            manager.get.side_effect = [SimpleNamespace(pk=9, display_name="New"), Exception("missing")]
            self.assertEqual(Team(game_id=9).game_obj.display_name, "New")
            self.assertIsNone(Team(game_id=10).game_obj)
