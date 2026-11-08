"""The team detail page asked for the same registration ids four times per request (OL-11)."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.organizations.services import team_detail_context as ctx


class RegistrationIdsMemoTests(SimpleTestCase):
    def test_one_query_per_team_object_and_callers_cannot_corrupt_the_cache(self):
        team = SimpleNamespace(id=5, slug="t")
        with patch("apps.tournaments.models.Registration.objects") as manager:
            manager.filter.return_value.values_list.return_value = [1, 2, 3]
            first = ctx._get_team_registration_ids(team)
            first.append(99)
            second = ctx._get_team_registration_ids(team)
            ctx._get_team_registration_ids(team)
        self.assertEqual(second, [1, 2, 3])
        manager.filter.assert_called_once()

    def test_failure_is_not_memoised(self):
        team = SimpleNamespace(id=5, slug="t")
        with patch("apps.tournaments.models.Registration.objects") as manager:
            manager.filter.side_effect = [RuntimeError("db"), SimpleNamespace(values_list=lambda *a, **k: [7])]
            self.assertEqual(ctx._get_team_registration_ids(team), [])
            self.assertEqual(ctx._get_team_registration_ids(team), [7])
