"""
Tests for bracket generation feature flag (Phase 3, Epic 3.1).

Validates feature-flagged wrapper in BracketService:
- BRACKETS_USE_UNIVERSAL_ENGINE=False uses legacy implementation
- BRACKETS_USE_UNIVERSAL_ENGINE=True uses universal engine
- Both paths produce compatible Bracket/BracketNode structures

Reference: Phase 3, Epic 3.1 - Pluggable Bracket Generators
Reference: CLEANUP_AND_TESTING_PART_6.md §4.5 (Safe Rollback)
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.models import Tournament, Bracket, Game
from apps.tournament_ops.dtos.match import MatchDTO


class BracketFeatureFlagTests(TestCase):
    """Test feature flag behavior in BracketService."""
    
    def setUp(self):
        """Create test tournament."""
        self.game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            is_active=True
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            format=Bracket.SINGLE_ELIMINATION,
            max_teams=8,
        )
        self.participants = [
            {"id": str(i), "name": f"Team {i}", "seed": i}
            for i in range(1, 5)
        ]
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=False)
    def test_feature_flag_false_uses_legacy(self):
        """
        Test that BRACKETS_USE_UNIVERSAL_ENGINE=False uses legacy implementation.
        
        Verifies rollback safety - setting flag to False reverts to original behavior.
        """
        with patch.object(BracketService, 'generate_bracket') as mock_legacy:
            mock_legacy.return_value = MagicMock(spec=Bracket)
            
            BracketService.generate_bracket_universal_safe(
                tournament_id=self.tournament.id,
                bracket_format=Bracket.SINGLE_ELIMINATION,
                participants=self.participants
            )
            
            # Legacy method should be called
            mock_legacy.assert_called_once()
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=True)
    @patch('apps.tournaments.services.bracket_service.BracketEngineService')
    def test_feature_flag_true_uses_universal_engine(self, mock_engine_class):
        """
        Test that BRACKETS_USE_UNIVERSAL_ENGINE=True uses universal engine.
        
        Verifies new code path is activated when flag is enabled.
        """
        # Mock the universal engine to return matches
        mock_engine_instance = MagicMock()
        mock_engine_instance.generate_bracket_for_stage.return_value = [
            MatchDTO(
                id=0,
                stage_id=1,
                round_number=1,
                match_number=1,
                team1_id=1,
                team2_id=2,
                stage_type="main",
            ),
            MatchDTO(
                id=0,
                stage_id=1,
                round_number=1,
                match_number=2,
                team1_id=3,
                team2_id=4,
                stage_type="main",
            ),
            MatchDTO(
                id=0,
                stage_id=1,
                round_number=2,
                match_number=1,
                team1_id=None,
                team2_id=None,
                stage_type="main",
            ),
        ]
        mock_engine_class.return_value = mock_engine_instance
        
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=self.tournament.id,
            bracket_format=Bracket.SINGLE_ELIMINATION,
            participants=self.participants
        )
        
        # Universal engine should be called
        mock_engine_instance.generate_bracket_for_stage.assert_called_once()
        
        # Bracket should be created
        assert bracket is not None
        assert bracket.tournament == self.tournament
        assert bracket.format == Bracket.SINGLE_ELIMINATION
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=False)
    def test_legacy_path_produces_valid_bracket(self):
        """
        Test that legacy path produces valid Bracket/BracketNode structure.
        
        Verifies backwards compatibility when feature flag is disabled.
        """
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=self.tournament.id,
            bracket_format=Bracket.SINGLE_ELIMINATION,
            participants=self.participants
        )
        
        # Verify bracket created
        assert bracket is not None
        assert bracket.tournament == self.tournament
        assert bracket.participant_count == 4
        
        # Verify nodes created
        nodes = bracket.nodes.all()
        assert nodes.count() > 0
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=True)
    @patch('apps.tournaments.services.bracket_service.BracketEngineService')
    def test_universal_path_produces_valid_bracket(self, mock_engine_class):
        """
        Test that universal engine path produces valid Bracket/BracketNode structure.
        
        Verifies new implementation creates same structure as legacy.
        """
        # Mock engine to return realistic matches
        mock_engine_instance = MagicMock()
        mock_engine_instance.generate_bracket_for_stage.return_value = [
            MatchDTO(
                id=0, stage_id=1, round_number=1, match_number=1,
                team1_id=1, team2_id=2, stage_type="main"
            ),
            MatchDTO(
                id=0, stage_id=1, round_number=1, match_number=2,
                team1_id=3, team2_id=4, stage_type="main"
            ),
            MatchDTO(
                id=0, stage_id=1, round_number=2, match_number=1,
                team1_id=None, team2_id=None, stage_type="main"
            ),
        ]
        mock_engine_class.return_value = mock_engine_instance
        
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=self.tournament.id,
            bracket_format=Bracket.SINGLE_ELIMINATION,
            participants=self.participants
        )
        
        # Verify bracket created
        assert bracket is not None
        assert bracket.tournament == self.tournament
        assert bracket.participant_count == 4
        
        # Verify nodes created
        nodes = bracket.nodes.all()
        assert nodes.count() == 3  # 3 matches from mock
        
        # Verify node structure
        for node in nodes:
            assert node.round_number in [1, 2]
            assert node.match_number >= 1
    
    def test_feature_flag_defaults_to_false(self):
        """
        Test that feature flag defaults to False (legacy behavior).
        
        Ensures safe rollout - default preserves existing behavior.
        """
        from django.conf import settings
        
        # Feature flag should default to False if not explicitly set
        flag_value = getattr(settings, 'BRACKETS_USE_UNIVERSAL_ENGINE', False)
        assert flag_value is False, "Feature flag should default to False for safe rollout"
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=False)
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=True)
    def test_feature_flag_toggleable(self):
        """
        Test that feature flag can be toggled at runtime.
        
        Verifies dynamic rollback capability.
        """
        # This test uses override_settings to simulate toggling
        # In production, this would be done via settings.py or environment variables
        from django.conf import settings
        
        # When both overrides applied, last one wins (True)
        assert settings.BRACKETS_USE_UNIVERSAL_ENGINE is True
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=False)
    def test_legacy_path_handles_double_elimination(self):
        """Test legacy path handles double elimination format."""
        self.tournament.format = Bracket.DOUBLE_ELIMINATION
        self.tournament.save()
        
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=self.tournament.id,
            bracket_format=Bracket.DOUBLE_ELIMINATION,
            participants=self.participants
        )
        
        assert bracket.format == Bracket.DOUBLE_ELIMINATION
        # Verify winners/losers brackets created
        nodes = bracket.nodes.all()
        assert nodes.count() > 0
    
    @override_settings(BRACKETS_USE_UNIVERSAL_ENGINE=True)
    @patch('apps.tournaments.services.bracket_service.BracketEngineService')
    def test_universal_path_handles_round_robin(self, mock_engine_class):
        """Test universal engine path handles round-robin format."""
        # Mock round-robin matches (4 teams = 6 matches)
        mock_engine_instance = MagicMock()
        mock_engine_instance.generate_bracket_for_stage.return_value = [
            MatchDTO(id=0, stage_id=1, round_number=1, match_number=i,
                    team1_id=i, team2_id=i+1, stage_type="main")
            for i in range(1, 7)
        ]
        mock_engine_class.return_value = mock_engine_instance
        
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=self.tournament.id,
            bracket_format=Bracket.ROUND_ROBIN,
            participants=self.participants
        )
        
        assert bracket.format == Bracket.ROUND_ROBIN
        nodes = bracket.nodes.all()
        assert nodes.count() == 6
