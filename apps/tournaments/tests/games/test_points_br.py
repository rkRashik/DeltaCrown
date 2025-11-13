# apps/tournaments/tests/games/test_points_br.py
"""Tests for Battle Royale point calculators (FF, PUBG Mobile)."""

import pytest
from apps.tournaments.games.points import (
    calc_ff_points,
    calc_pubgm_points,
    get_br_leaderboard
)


class TestFreeFirePoints:
    """Test Free Fire point calculation."""
    
    def test_winner_with_kills(self):
        """1st place + kills gets highest bonus."""
        assert calc_ff_points(5, 1) == 17  # 5 kills + 12 placement
    
    def test_second_place(self):
        """2nd place gets 9 point bonus."""
        assert calc_ff_points(3, 2) == 12  # 3 kills + 9 placement
    
    def test_third_place(self):
        """3rd place gets 7 point bonus."""
        assert calc_ff_points(2, 3) == 9  # 2 kills + 7 placement
    
    def test_mid_placement(self):
        """4th place gets 5pt, 5th-6th gets 4pt bonus."""
        assert calc_ff_points(4, 4) == 9  # 4 kills + 5 placement
        assert calc_ff_points(4, 5) == 8  # 4 kills + 4 placement
        assert calc_ff_points(4, 6) == 8  # 4 kills + 4 placement
    
    def test_low_placement(self):
        """7th-8th gets 3pt, 9th-10th gets 2pt bonus."""
        assert calc_ff_points(6, 7) == 9  # 6 kills + 3 placement
        assert calc_ff_points(6, 10) == 8  # 6 kills + 2 placement
    
    def test_bottom_placement_with_bonus(self):
        """11th-15th place gets 1 point bonus."""
        assert calc_ff_points(5, 11) == 6  # 5 kills + 1 placement
        assert calc_ff_points(5, 15) == 6  # 5 kills + 1 placement
    
    def test_no_placement_bonus(self):
        """16th+ place gets 0 bonus."""
        assert calc_ff_points(10, 16) == 10  # 10 kills + 0 placement
        assert calc_ff_points(10, 20) == 10  # 10 kills + 0 placement
    
    def test_zero_kills(self):
        """Placement points only."""
        assert calc_ff_points(0, 1) == 12  # Pacifist chicken dinner
        assert calc_ff_points(0, 10) == 2  # Survival with no kills
    
    def test_negative_kills_raises(self):
        """Negative kills not allowed."""
        with pytest.raises(ValueError, match="Kills cannot be negative"):
            calc_ff_points(-1, 1)
    
    def test_invalid_placement_raises(self):
        """Placement must be >= 1."""
        with pytest.raises(ValueError, match="Placement must be 1 or higher"):
            calc_ff_points(5, 0)


class TestPubgMobilePoints:
    """Test PUBG Mobile point calculation (same formula as FF)."""
    
    def test_winner_with_kills(self):
        """1st place + kills."""
        assert calc_pubgm_points(8, 1) == 20  # 8 kills + 12 placement
    
    def test_second_place(self):
        """2nd place."""
        assert calc_pubgm_points(4, 2) == 13  # 4 kills + 9 placement
    
    def test_consistent_with_ff(self):
        """PUBG and FF use same formula."""
        for kills in range(0, 15):
            for placement in range(1, 25):
                assert calc_pubgm_points(kills, placement) == calc_ff_points(kills, placement)


class TestBRLeaderboard:
    """Test Battle Royale leaderboard sorting."""
    
    def test_sort_by_points_descending(self):
        """Higher points rank first."""
        results = [
            {'team_id': 1, 'kills': 3, 'placement': 5},  # 3 + 4 = 7
            {'team_id': 2, 'kills': 8, 'placement': 2},  # 8 + 9 = 17
            {'team_id': 3, 'kills': 5, 'placement': 1},  # 5 + 12 = 17
        ]
        
        leaderboard = get_br_leaderboard(results)
        
        assert leaderboard[0]['team_id'] == 3  # 17 points, 1st place (tiebreaker)
        assert leaderboard[0]['points'] == 17
        assert leaderboard[1]['team_id'] == 2  # 17 points, 2nd place
        assert leaderboard[1]['points'] == 17
        assert leaderboard[2]['team_id'] == 1  # 7 points
        assert leaderboard[2]['points'] == 7
    
    def test_tiebreaker_by_placement(self):
        """Same points: better placement ranks first."""
        results = [
            {'team_id': 1, 'kills': 3, 'placement': 3},  # 3 + 7 = 10
            {'team_id': 2, 'kills': 5, 'placement': 4},  # 5 + 5 = 10
            {'team_id': 3, 'kills': 1, 'placement': 2},  # 1 + 9 = 10
        ]
        
        leaderboard = get_br_leaderboard(results)
        
        # All have 10 points, sorted by placement ascending
        assert leaderboard[0]['team_id'] == 3  # 2nd place
        assert leaderboard[1]['team_id'] == 1  # 3rd place
        assert leaderboard[2]['team_id'] == 2  # 4th place
    
    def test_empty_results(self):
        """Empty list returns empty."""
        assert get_br_leaderboard([]) == []
    
    def test_single_team(self):
        """Single team works."""
        results = [{'team_id': 1, 'kills': 10, 'placement': 1}]
        leaderboard = get_br_leaderboard(results)
        
        assert len(leaderboard) == 1
        assert leaderboard[0]['points'] == 22  # 10 + 12
