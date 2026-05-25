"""
Integration tests for TeamAdapter with tournament eligibility.

These tests use the current vNext team schema:
- games.Game stores game identity only.
- games.GameRosterConfig stores roster-size rules.
- organizations.Team uses game_id.
- organizations.TeamMembership uses user, not profile.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from unittest.mock import patch

from apps.games.models import Game, GameRosterConfig
from apps.organizations.choices import MembershipRole, MembershipStatus, RosterSlot, TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.tournaments.models import Tournament
from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
from apps.user_profile.models import UserProfile

User = get_user_model()


def create_game(*, slug="test-game", min_team_size=5, max_team_size=5, min_roster_size=None):
    game = Game.objects.create(
        name=f"Test Game {slug}",
        display_name=f"TEST GAME {slug}",
        slug=slug,
        short_code=slug[:8].upper().replace("-", ""),
        category="FPS",
        game_type="TEAM_VS_TEAM",
        platforms=["PC"],
        is_active=True,
    )
    GameRosterConfig.objects.create(
        game=game,
        min_team_size=min_team_size,
        max_team_size=max_team_size,
        min_substitutes=0,
        max_substitutes=2,
        min_roster_size=min_roster_size or min_team_size,
        max_roster_size=max(max_team_size + 2, min_team_size),
    )
    return game


def create_tournament(game, *, slug="test-tournament"):
    now = timezone.now()
    organizer = User.objects.create_user(
        username=f"organizer_{slug}",
        email=f"organizer_{slug}@example.com",
    )
    return Tournament.objects.create(
        name=f"Test Tournament {slug}",
        slug=slug,
        organizer=organizer,
        game=game,
        participation_type=Tournament.TEAM,
        status=Tournament.REGISTRATION_OPEN,
        registration_start=now - timezone.timedelta(days=1),
        registration_end=now + timezone.timedelta(days=7),
        tournament_start=now + timezone.timedelta(days=8),
        tournament_end=now + timezone.timedelta(days=9),
    )


def create_user(username):
    user = User.objects.create_user(username=username, email=f"{username}@example.com")
    UserProfile.objects.get_or_create(user=user)
    return user


def create_team(game, owner, *, team_id=None, slug="test-team", name="Test Team"):
    kwargs = {}
    if team_id is not None:
        kwargs["id"] = team_id
    return Team.objects.create(
        **kwargs,
        name=name,
        slug=slug,
        game_id=game.id,
        created_by=owner,
        region="BD",
        status=TeamStatus.ACTIVE,
        visibility="PUBLIC",
    )


def add_member(team, user, *, role=MembershipRole.PLAYER, slot=RosterSlot.STARTER):
    return TeamMembership.objects.create(
        team=team,
        user=user,
        role=role,
        roster_slot=slot,
        status=MembershipStatus.ACTIVE,
    )


def create_team_with_roster(game, owner, *, active_players, team_id=None, slug="test-team"):
    team = create_team(game, owner, team_id=team_id, slug=slug)
    add_member(team, owner, role=MembershipRole.OWNER, slot=RosterSlot.STARTER)
    for idx in range(max(active_players - 1, 0)):
        add_member(
            team,
            create_user(f"{slug}_member_{idx}"),
            role=MembershipRole.PLAYER,
            slot=RosterSlot.STARTER,
        )
    return team


class TestLegacyDefaultSafety(TestCase):
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=False)
    @patch("apps.organizations.adapters.team_adapter.TeamAdapter.validate_roster")
    @patch("apps.organizations.adapters.team_adapter.record_routing_decision")
    def test_adapter_disabled_uses_legacy_path(self, mock_record, mock_validate):
        game = create_game(slug="legacy-disabled", min_team_size=5)
        tournament = create_tournament(game, slug="legacy-disabled-cup")
        user = create_user("legacy_disabled_user")
        create_team_with_roster(game, user, active_players=5, slug="legacy-disabled-team")

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertTrue(result["eligible"])
        mock_validate.assert_not_called()
        mock_record.assert_called()
        self.assertEqual(mock_record.call_args[0][1], "legacy")
        self.assertIn("adapter_disabled", mock_record.call_args[0][2])

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="legacy_only",
    )
    @patch("apps.organizations.adapters.team_adapter.TeamAdapter.validate_roster")
    def test_legacy_only_mode_uses_legacy_path(self, mock_validate):
        game = create_game(slug="legacy-only", min_team_size=5)
        tournament = create_tournament(game, slug="legacy-only-cup")
        user = create_user("legacy_only_user")
        create_team_with_roster(game, user, active_players=1, slug="legacy-only-team")

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertFalse(result["eligible"])
        self.assertIn("members", result["reason"].lower())
        mock_validate.assert_not_called()


class TestVNextRosterValidationRouting(TestCase):
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_valid_vnext_roster_passes_with_game_roster_config(self):
        game = create_game(slug="vnext-valid", min_team_size=2, max_team_size=5)
        tournament = create_tournament(game, slug="vnext-valid-cup")
        user = create_user("vnext_valid_user")
        create_team_with_roster(game, user, active_players=2, slug="vnext-valid-team")

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertTrue(result["eligible"])

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_invalid_vnext_roster_fails_with_game_roster_config(self):
        game = create_game(slug="vnext-invalid", min_team_size=3, max_team_size=5)
        tournament = create_tournament(game, slug="vnext-invalid-cup")
        user = create_user("vnext_invalid_user")
        create_team_with_roster(game, user, active_players=1, slug="vnext-invalid-team")

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "roster_invalid")
        self.assertIn("active members", result["reason"].lower())

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    def test_allowlisted_team_uses_vnext_path(self):
        game = create_game(slug="allowlisted", min_team_size=2, max_team_size=5)
        tournament = create_tournament(game, slug="allowlisted-cup")
        user = create_user("allowlisted_user")
        create_team_with_roster(
            game,
            user,
            active_players=2,
            team_id=999,
            slug="allowlisted-team",
        )

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertTrue(result["eligible"])

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    def test_non_allowlisted_team_uses_legacy_path(self):
        game = create_game(slug="not-allowlisted", min_team_size=5)
        tournament = create_tournament(game, slug="not-allowlisted-cup")
        user = create_user("not_allowlisted_user")
        create_team_with_roster(
            game,
            user,
            active_players=1,
            team_id=888,
            slug="not-allowlisted-team",
        )

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "roster_too_small")


class TestEmergencyRollback(TestCase):
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=True,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
        TEAM_VNEXT_TEAM_ALLOWLIST=[999],
    )
    @patch("apps.organizations.adapters.team_adapter.TeamService")
    def test_force_legacy_overrides_all_settings(self, mock_service):
        game = create_game(slug="force-legacy", min_team_size=5)
        tournament = create_tournament(game, slug="force-legacy-cup")
        user = create_user("force_legacy_user")
        create_team_with_roster(game, user, active_players=1, team_id=999, slug="force-legacy-team")

        result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "roster_too_small")
        mock_service.validate_roster.assert_not_called()


class TestQueryCountPerformance(TransactionTestCase):
    @override_settings(TEAM_VNEXT_ADAPTER_ENABLED=False)
    def test_legacy_path_query_count(self):
        game = create_game(slug="query-legacy", min_team_size=5)
        tournament = create_tournament(game, slug="query-legacy-cup")
        user = create_user("query_legacy_user")
        create_team_with_roster(game, user, active_players=5, slug="query-legacy-team")

        with CaptureQueriesContext(connection) as context:
            result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertTrue(result["eligible"])
        query_count = len(context.captured_queries)
        self.assertLessEqual(query_count, 14, f"Legacy path exceeded 14 queries: {query_count}")

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_vnext_path_query_count(self):
        game = create_game(slug="query-vnext", min_team_size=2, max_team_size=5)
        tournament = create_tournament(game, slug="query-vnext-cup")
        user = create_user("query_vnext_user")
        create_team_with_roster(game, user, active_players=2, slug="query-vnext-team")

        with CaptureQueriesContext(connection) as context:
            result = RegistrationEligibilityService._check_team_eligibility(tournament, user)

        self.assertTrue(result["eligible"])
        query_count = len(context.captured_queries)
        # Current vNext route includes permission/team discovery, adapter routing,
        # duplicate-registration check, and GameRosterConfig-backed validation.
        self.assertLessEqual(query_count, 18, f"vNext path exceeded 18 queries: {query_count}")
