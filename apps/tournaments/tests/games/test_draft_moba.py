# apps/tournaments/tests/games/test_draft_moba.py
"""Tests for MOBA draft/ban validators (Dota 2, MLBB)."""

import pytest
from apps.tournaments.games.draft import validate_dota2_draft, validate_mlbb_draft


class TestDota2DraftFlow:
    """Test Dota 2 draft/ban validation."""
    
    def test_captains_mode_valid(self):
        """Valid Captain's Mode draft (7 bans, 5 picks each)."""
        draft = {
            "mode": "captains_mode",
            "team_a_bans": [1, 2, 3, 4, 5, 6, 7],
            "team_b_bans": [8, 9, 10, 11, 12, 13, 14],
            "team_a_picks": [15, 16, 17, 18, 19],
            "team_b_picks": [20, 21, 22, 23, 24],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is True
        assert error is None
    
    def test_all_pick_valid(self):
        """Valid All-Pick mode (no bans, 5 picks each)."""
        draft = {
            "mode": "all_pick",
            "team_a_bans": [],
            "team_b_bans": [],
            "team_a_picks": [1, 2, 3, 4, 5],
            "team_b_picks": [6, 7, 8, 9, 10],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is True
        assert error is None
    
    def test_captains_mode_insufficient_bans(self):
        """Captain's Mode requires exactly 7 bans."""
        draft = {
            "mode": "captains_mode",
            "team_a_bans": [1, 2, 3],  # Only 3 bans
            "team_b_bans": [4, 5, 6, 7, 8, 9, 10],
            "team_a_picks": [11, 12, 13, 14, 15],
            "team_b_picks": [16, 17, 18, 19, 20],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "7 bans" in error
    
    def test_all_pick_with_bans_invalid(self):
        """All-Pick mode cannot have bans."""
        draft = {
            "mode": "all_pick",
            "team_a_bans": [1],  # Bans not allowed
            "team_b_bans": [],
            "team_a_picks": [2, 3, 4, 5, 6],
            "team_b_picks": [7, 8, 9, 10, 11],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "All-Pick mode does not allow bans" in error
    
    def test_insufficient_picks(self):
        """Must have exactly 5 picks per team."""
        draft = {
            "mode": "captains_mode",
            "team_a_bans": [1, 2, 3, 4, 5, 6, 7],
            "team_b_bans": [8, 9, 10, 11, 12, 13, 14],
            "team_a_picks": [15, 16, 17],  # Only 3 picks
            "team_b_picks": [20, 21, 22, 23, 24],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "5 hero picks" in error
    
    def test_duplicate_picks_invalid(self):
        """Cannot pick same hero twice."""
        draft = {
            "mode": "all_pick",
            "team_a_bans": [],
            "team_b_bans": [],
            "team_a_picks": [1, 2, 3, 4, 5],
            "team_b_picks": [5, 6, 7, 8, 9],  # Hero 5 picked twice
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "Duplicate hero picks" in error
    
    def test_duplicate_bans_invalid(self):
        """Cannot ban same hero twice."""
        draft = {
            "mode": "captains_mode",
            "team_a_bans": [1, 2, 3, 4, 5, 6, 7],
            "team_b_bans": [7, 8, 9, 10, 11, 12, 13],  # Hero 7 banned twice
            "team_a_picks": [14, 15, 16, 17, 18],
            "team_b_picks": [19, 20, 21, 22, 23],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "Duplicate hero bans" in error
    
    def test_banned_hero_picked_invalid(self):
        """Cannot pick a banned hero."""
        draft = {
            "mode": "captains_mode",
            "team_a_bans": [1, 2, 3, 4, 5, 6, 7],
            "team_b_bans": [8, 9, 10, 11, 12, 13, 14],
            "team_a_picks": [1, 15, 16, 17, 18],  # Hero 1 is banned
            "team_b_picks": [19, 20, 21, 22, 23],
            "draft_order": []
        }
        
        is_valid, error = validate_dota2_draft(draft)
        assert is_valid is False
        assert "banned and picked" in error


class TestMlbbDraftFlow:
    """Test Mobile Legends draft/ban validation."""
    
    def test_draft_mode_valid(self):
        """Valid Draft Mode (3 bans, 5 picks each)."""
        draft = {
            "mode": "draft",
            "team_a_bans": [1, 2, 3],
            "team_b_bans": [4, 5, 6],
            "team_a_picks": [10, 11, 12, 13, 14],
            "team_b_picks": [20, 21, 22, 23, 24],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is True
        assert error is None
    
    def test_classic_mode_valid(self):
        """Valid Classic Mode (no bans, 5 picks each)."""
        draft = {
            "mode": "classic",
            "team_a_bans": [],
            "team_b_bans": [],
            "team_a_picks": [1, 2, 3, 4, 5],
            "team_b_picks": [6, 7, 8, 9, 10],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is True
        assert error is None
    
    def test_draft_mode_insufficient_bans(self):
        """Draft Mode requires exactly 3 bans."""
        draft = {
            "mode": "draft",
            "team_a_bans": [1, 2],  # Only 2 bans
            "team_b_bans": [3, 4, 5],
            "team_a_picks": [10, 11, 12, 13, 14],
            "team_b_picks": [20, 21, 22, 23, 24],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is False
        assert "3 bans" in error
    
    def test_classic_mode_with_bans_invalid(self):
        """Classic Mode cannot have bans."""
        draft = {
            "mode": "classic",
            "team_a_bans": [1],  # Bans not allowed
            "team_b_bans": [],
            "team_a_picks": [2, 3, 4, 5, 6],
            "team_b_picks": [7, 8, 9, 10, 11],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is False
        assert "Classic mode does not allow bans" in error
    
    def test_invalid_mode(self):
        """Unknown mode rejected."""
        draft = {
            "mode": "unknown_mode",
            "team_a_bans": [],
            "team_b_bans": [],
            "team_a_picks": [1, 2, 3, 4, 5],
            "team_b_picks": [6, 7, 8, 9, 10],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is False
        assert "Invalid mode" in error
    
    def test_duplicate_picks_invalid(self):
        """Cannot pick same hero twice."""
        draft = {
            "mode": "draft",
            "team_a_bans": [1, 2, 3],
            "team_b_bans": [4, 5, 6],
            "team_a_picks": [10, 11, 12, 13, 14],
            "team_b_picks": [14, 15, 16, 17, 18],  # Hero 14 picked twice
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is False
        assert "Duplicate hero picks" in error
    
    def test_banned_hero_picked_invalid(self):
        """Cannot pick a banned hero."""
        draft = {
            "mode": "draft",
            "team_a_bans": [1, 2, 3],
            "team_b_bans": [4, 5, 6],
            "team_a_picks": [1, 10, 11, 12, 13],  # Hero 1 is banned
            "team_b_picks": [14, 15, 16, 17, 18],
            "draft_order": []
        }
        
        is_valid, error = validate_mlbb_draft(draft)
        assert is_valid is False
        assert "banned and picked" in error
