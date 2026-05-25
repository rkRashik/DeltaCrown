from django.test import TestCase, override_settings
from django.utils import timezone

from apps.games.models import GameRosterConfig
from apps.organizations.choices import MembershipRole, RosterSlot
from apps.organizations.services.team_service import TeamService
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.tournaments.models import Tournament
from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
from apps.user_profile.models import UserProfile


class TeamServiceRosterValidationTests(TestCase):
    def setUp(self):
        self.game = GameFactory(name="Roster Validation Game")
        self.config = GameRosterConfig.objects.create(
            game=self.game,
            min_team_size=2,
            max_team_size=3,
            min_substitutes=0,
            max_substitutes=2,
            min_roster_size=2,
            max_roster_size=5,
            allow_coaches=True,
            max_coaches=1,
            allow_managers=True,
            max_managers=2,
        )

    def make_team(self, *, game=None, name="Roster Validation Team"):
        owner = UserFactory()
        team = TeamFactory.create_independent(
            created_by=owner,
            game_id=(game or self.game).id,
            name=name,
        )
        return team, owner

    def add_member(self, team, *, role=MembershipRole.PLAYER, slot=RosterSlot.STARTER, username=None):
        return TeamMembershipFactory(
            team=team,
            user=UserFactory(username=username) if username else UserFactory(),
            role=role,
            roster_slot=slot,
        )

    def test_valid_roster_passes_game_roster_config(self):
        team, _owner = self.make_team(name="Valid Roster")
        self.add_member(team, username="valid_starter_1")
        self.add_member(team, username="valid_starter_2")
        self.add_member(team, role=MembershipRole.COACH, slot=RosterSlot.COACH, username="valid_coach")

        result = TeamService.validate_roster(team.id, game_id=self.game.id)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.roster_data["starter_count"], 2)
        self.assertEqual(result.roster_data["coach_count"], 1)

    def test_too_few_players_fails(self):
        team, _owner = self.make_team(name="Too Few Roster")
        self.add_member(team, username="too_few_starter_1")

        result = TeamService.validate_roster(team.id, game_id=self.game.id)

        self.assertFalse(result.is_valid)
        self.assertIn("below minimum", result.errors[0])

    def test_too_many_players_fails(self):
        team, _owner = self.make_team(name="Too Many Roster")
        for idx in range(4):
            self.add_member(team, username=f"too_many_starter_{idx}")

        result = TeamService.validate_roster(team.id, game_id=self.game.id)

        self.assertFalse(result.is_valid)
        self.assertTrue(any("Too many starting players" in error for error in result.errors))

    def test_coach_limit_is_enforced(self):
        team, _owner = self.make_team(name="Coach Limit Roster")
        self.add_member(team, username="coach_limit_starter_1")
        self.add_member(team, username="coach_limit_starter_2")
        self.add_member(team, role=MembershipRole.COACH, slot=RosterSlot.COACH, username="coach_limit_1")
        self.add_member(team, role=MembershipRole.COACH, slot=RosterSlot.COACH, username="coach_limit_2")

        result = TeamService.validate_roster(team.id, game_id=self.game.id)

        self.assertFalse(result.is_valid)
        self.assertTrue(any("Too many coaches" in error for error in result.errors))

    def test_missing_game_roster_config_allows_with_warning(self):
        game_without_config = GameFactory(name="No Config Game")
        team, _owner = self.make_team(game=game_without_config, name="No Config Roster")

        result = TeamService.validate_roster(team.id, game_id=game_without_config.id)

        self.assertTrue(result.is_valid)
        self.assertTrue(result.warnings)
        self.assertTrue(result.roster_data["config_missing"])

    def test_validate_roster_no_longer_raises_not_implemented(self):
        team, _owner = self.make_team(name="No Stub Roster")

        result = TeamService.validate_roster(team.id, game_id=self.game.id)

        self.assertIsInstance(result.is_valid, bool)


class TournamentEligibilityRosterValidationTests(TestCase):
    def setUp(self):
        self.game = GameFactory(name="Eligibility Roster Game")
        self.config = GameRosterConfig.objects.create(
            game=self.game,
            min_team_size=2,
            max_team_size=5,
            min_substitutes=0,
            max_substitutes=2,
            min_roster_size=2,
            max_roster_size=7,
        )
        self.organizer = UserFactory(username="roster_tournament_organizer")
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name="Roster Eligibility Cup",
            slug="roster-eligibility-cup",
            organizer=self.organizer,
            game=self.game,
            participation_type=Tournament.TEAM,
            status=Tournament.REGISTRATION_OPEN,
            registration_start=now - timezone.timedelta(days=1),
            registration_end=now + timezone.timedelta(days=7),
            tournament_start=now + timezone.timedelta(days=8),
            tournament_end=now + timezone.timedelta(days=9),
        )

    def make_team_for_user(self, user, *, name="Eligibility Team"):
        UserProfile.objects.get_or_create(user=user)
        team = TeamFactory.create_independent(
            created_by=user,
            game_id=self.game.id,
            name=name,
        )
        TeamMembershipFactory(
            team=team,
            user=user,
            role=MembershipRole.OWNER,
            roster_slot=None,
        )
        return team

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_eligibility_blocks_roster_too_small(self):
        captain = UserFactory(username="eligibility_too_small_captain")
        self.make_team_for_user(captain, name="Eligibility Too Small")

        result = RegistrationEligibilityService._check_team_eligibility(self.tournament, captain)

        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "roster_invalid")
        self.assertIn("at least 2 active members", result["reason"].lower())

    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_eligibility_allows_valid_roster(self):
        captain = UserFactory(username="eligibility_valid_captain")
        team = self.make_team_for_user(captain, name="Eligibility Valid")
        self.add_starter(team, "eligibility_valid_player_1")
        self.add_starter(team, "eligibility_valid_player_2")

        result = RegistrationEligibilityService._check_team_eligibility(self.tournament, captain)

        self.assertTrue(result["eligible"])

    def add_starter(self, team, username):
        TeamMembershipFactory(
            team=team,
            user=UserFactory(username=username),
            role=MembershipRole.PLAYER,
            roster_slot=RosterSlot.STARTER,
        )
