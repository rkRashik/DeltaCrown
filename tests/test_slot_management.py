# tests/test_slot_management.py
"""
Test tournament slot management functionality.
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.registration import (
    register_valorant_team, register_efootball_player,
    TeamRegistrationInput, SoloRegistrationInput
)
from apps.user_profile.models import UserProfile
from apps.teams.models import Team


class SlotManagementTestCase(TestCase):
    """Test slot limits and validation."""

    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user("user1", "user1@test.com", "pass123")
        self.user2 = User.objects.create_user("user2", "user2@test.com", "pass123")
        self.user3 = User.objects.create_user("user3", "user3@test.com", "pass123")
        
        # Create profiles (get_or_create in case they auto-exist)
        self.profile1, _ = UserProfile.objects.get_or_create(
            user=self.user1, defaults={"display_name": "Player1"}
        )
        self.profile2, _ = UserProfile.objects.get_or_create(
            user=self.user2, defaults={"display_name": "Player2"}
        )
        self.profile3, _ = UserProfile.objects.get_or_create(
            user=self.user3, defaults={"display_name": "Player3"}
        )

        # Create teams
        self.team1 = Team.objects.create(
            name="Team Alpha", tag="ALPH", captain=self.profile1, game="valorant"
        )
        self.team2 = Team.objects.create(
            name="Team Beta", tag="BETA", captain=self.profile2, game="valorant"
        )
        self.team3 = Team.objects.create(
            name="Team Gamma", tag="GAMM", captain=self.profile3, game="valorant"
        )

    def test_tournament_slot_properties(self):
        """Test Tournament slot tracking properties."""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game="valorant",
            slot_size=2
        )
        
        # Initially empty
        self.assertEqual(tournament.slots_total, 2)
        self.assertEqual(tournament.slots_taken, 0)
        self.assertEqual(tournament.slots_text, "0/2 slots")

        # Add one registration
        Registration.objects.create(tournament=tournament, team=self.team1, status="CONFIRMED")
        
        # Refresh from DB to get updated counts
        tournament.refresh_from_db()
        self.assertEqual(tournament.slots_taken, 1)
        self.assertEqual(tournament.slots_text, "1/2 slots")

    def test_valorant_team_slot_validation(self):
        """Test slot limits for Valorant team registrations."""
        tournament = Tournament.objects.create(
            name="Valorant Championship",
            slug="valorant-championship", 
            game="valorant",
            slot_size=2  # Only 2 teams allowed
        )

        # First registration should succeed
        reg1 = register_valorant_team(TeamRegistrationInput(
            tournament_id=tournament.id,
            team_id=self.team1.id
        ))
        self.assertIsNotNone(reg1)

        # Second registration should succeed
        reg2 = register_valorant_team(TeamRegistrationInput(
            tournament_id=tournament.id,
            team_id=self.team2.id
        ))
        self.assertIsNotNone(reg2)

        # Third registration should fail (tournament full)
        with self.assertRaises(ValidationError) as cm:
            register_valorant_team(TeamRegistrationInput(
                tournament_id=tournament.id,
                team_id=self.team3.id
            ))
        
        self.assertIn("Tournament is full", str(cm.exception))

    def test_efootball_solo_slot_validation(self):
        """Test slot limits for eFootball solo registrations."""
        tournament = Tournament.objects.create(
            name="eFootball Solo Cup",
            slug="efootball-solo-cup",
            game="efootball", 
            slot_size=2  # Only 2 players allowed
        )

        # First registration should succeed
        reg1 = register_efootball_player(SoloRegistrationInput(
            tournament_id=tournament.id,
            user_id=self.profile1.id
        ))
        self.assertIsNotNone(reg1)

        # Second registration should succeed  
        reg2 = register_efootball_player(SoloRegistrationInput(
            tournament_id=tournament.id,
            user_id=self.profile2.id
        ))
        self.assertIsNotNone(reg2)

        # Third registration should fail (tournament full)
        with self.assertRaises(ValidationError) as cm:
            register_efootball_player(SoloRegistrationInput(
                tournament_id=tournament.id,
                user_id=self.profile3.id
            ))
        
        self.assertIn("Tournament is full", str(cm.exception))

    def test_unlimited_slots(self):
        """Test tournaments with no slot limit work normally."""
        tournament = Tournament.objects.create(
            name="Open Tournament",
            slug="open-tournament",
            game="valorant",
            slot_size=None  # No limit
        )

        # Should be able to register many teams
        reg1 = register_valorant_team(TeamRegistrationInput(
            tournament_id=tournament.id,
            team_id=self.team1.id
        ))
        reg2 = register_valorant_team(TeamRegistrationInput(
            tournament_id=tournament.id,
            team_id=self.team2.id
        ))
        reg3 = register_valorant_team(TeamRegistrationInput(
            tournament_id=tournament.id,
            team_id=self.team3.id
        ))
        
        # All should succeed
        self.assertIsNotNone(reg1)
        self.assertIsNotNone(reg2)
        self.assertIsNotNone(reg3)

    def test_zero_slots(self):
        """Test tournament with 0 slots prevents all registrations."""
        tournament = Tournament.objects.create(
            name="Closed Tournament",
            slug="closed-tournament",
            game="valorant",
            slot_size=0  # No registrations allowed
        )

        # Should immediately fail
        with self.assertRaises(ValidationError) as cm:
            register_valorant_team(TeamRegistrationInput(
                tournament_id=tournament.id,
                team_id=self.team1.id
            ))
        
        self.assertIn("Registration is not allowed", str(cm.exception))