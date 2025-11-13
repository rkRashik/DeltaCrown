"""
Tests for Leaderboards Service Layer.

Tests flag-gated behavior, Redis caching, DTO serialization, and edge cases.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.utils import timezone

from apps.leaderboards.services import (
    get_tournament_leaderboard,
    get_player_leaderboard_history,
    get_scoped_leaderboard,
    invalidate_tournament_cache,
    invalidate_player_history_cache,
    invalidate_scoped_cache,
    LeaderboardEntryDTO,
    PlayerHistoryDTO,
    LeaderboardResponseDTO,
)
from apps.leaderboards.models import LeaderboardEntry, LeaderboardSnapshot
from apps.tournaments.models import Tournament
from apps.teams.models import Team
from apps.accounts.models import User


@pytest.mark.django_db
class TestLeaderboardServiceFlags:
    """Test flag-gated behavior (COMPUTE_ENABLED, CACHE_ENABLED)."""
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=False)
    def test_tournament_leaderboard_flags_disabled_returns_empty(self):
        """If COMPUTE_ENABLED=False, return empty DTO with metadata."""
        response = get_tournament_leaderboard(tournament_id=999)
        
        assert response.scope == "tournament"
        assert response.entries == []
        assert response.metadata["count"] == 0
        assert response.metadata["cache_hit"] is False
        assert response.metadata["computation_enabled"] is False
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=False)
    def test_player_history_flags_disabled_returns_empty(self):
        """If COMPUTE_ENABLED=False, return empty DTO."""
        response = get_player_leaderboard_history(player_id=456)
        
        assert response.player_id == 456
        assert response.snapshots == []
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=False)
    def test_scoped_leaderboard_flags_disabled_returns_empty(self):
        """If COMPUTE_ENABLED=False, return empty DTO."""
        response = get_scoped_leaderboard(scope="all_time")
        
        assert response.scope == "all_time"
        assert response.entries == []
        assert response.metadata["computation_enabled"] is False


@pytest.mark.django_db
class TestTournamentLeaderboard:
    """Test get_tournament_leaderboard() with cache hit/miss scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_cache_hit_returns_cached_data(self):
        """If data is in cache, return cached entries without DB query."""
        tournament_id = 123
        cache_key = f"lb:tournament:{tournament_id}"
        
        # Pre-populate cache
        cached_entries = [
            {
                "rank": 1,
                "player_id": 10,
                "team_id": 5,
                "points": 1500,
                "wins": 10,
                "losses": 2,
                "win_rate": 83.33,
                "last_updated": datetime.utcnow(),
            }
        ]
        cache.set(cache_key, {
            "entries": cached_entries,
            "cached_at": datetime.utcnow().isoformat(),
        }, timeout=300)
        
        # Call service (should hit cache)
        response = get_tournament_leaderboard(tournament_id)
        
        assert response.metadata["cache_hit"] is True
        assert len(response.entries) == 1
        assert response.entries[0].rank == 1
        assert response.entries[0].player_id == 10
        assert response.entries[0].points == 1500
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_cache_miss_queries_db_and_writes_cache(self):
        """If cache is empty, query DB and write to cache."""
        # Create test data
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="valorant",
            status="completed"
        )
        player = User.objects.create(username="testplayer", email="test@example.com")
        team = Team.objects.create(name="Test Team", tag="TT")
        
        entry = LeaderboardEntry.objects.create(
            leaderboard_type="tournament",
            tournament=tournament,
            player=player,
            team=team,
            rank=1,
            points=1200,
            wins=8,
            losses=1,
            win_rate=88.89,
            is_active=True,
        )
        
        # Call service (cache is empty)
        response = get_tournament_leaderboard(tournament.id)
        
        assert response.metadata["cache_hit"] is False
        assert len(response.entries) == 1
        assert response.entries[0].rank == 1
        assert response.entries[0].player_id == player.id
        assert response.entries[0].points == 1200
        
        # Verify cache was written
        cache_key = f"lb:tournament:{tournament.id}"
        cached = cache.get(cache_key)
        assert cached is not None
        assert len(cached["entries"]) == 1
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=False)
    def test_cache_disabled_always_queries_db(self):
        """If CACHE_ENABLED=False, always query DB and don't write cache."""
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game="cs2",
            status="completed"
        )
        player = User.objects.create(username="player2", email="player2@example.com")
        
        LeaderboardEntry.objects.create(
            leaderboard_type="tournament",
            tournament=tournament,
            player=player,
            rank=1,
            points=900,
            wins=5,
            losses=0,
            win_rate=100.0,
            is_active=True,
        )
        
        # Call service twice
        response1 = get_tournament_leaderboard(tournament.id)
        response2 = get_tournament_leaderboard(tournament.id)
        
        # Both should be cache misses
        assert response1.metadata["cache_hit"] is False
        assert response2.metadata["cache_hit"] is False
        
        # Verify cache was not written
        cache_key = f"lb:tournament:{tournament.id}"
        assert cache.get(cache_key) is None
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_empty_leaderboard_returns_empty_list(self):
        """If no entries exist, return empty list with metadata."""
        tournament = Tournament.objects.create(
            name="Empty Tournament",
            game="lol",
            status="upcoming"
        )
        
        response = get_tournament_leaderboard(tournament.id)
        
        assert response.entries == []
        assert response.metadata["count"] == 0


@pytest.mark.django_db
class TestPlayerHistory:
    """Test get_player_leaderboard_history() with cache scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_player_history_cache_hit(self):
        """If player history is cached, return cached snapshots."""
        player_id = 789
        cache_key = f"lb:player_history:{player_id}"
        
        # Pre-populate cache
        cached_snapshots = [
            {
                "date": "2025-11-10",
                "rank": 5,
                "points": 2400,
                "leaderboard_type": "all_time",
            },
            {
                "date": "2025-11-11",
                "rank": 4,
                "points": 2600,
                "leaderboard_type": "all_time",
            },
        ]
        cache.set(cache_key, {
            "snapshots": cached_snapshots,
            "cached_at": datetime.utcnow().isoformat(),
        }, timeout=3600)
        
        # Call service
        response = get_player_leaderboard_history(player_id)
        
        assert response.player_id == player_id
        assert len(response.snapshots) == 2
        assert response.snapshots[0]["rank"] == 5
        assert response.snapshots[1]["rank"] == 4
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_player_history_cache_miss_queries_db(self):
        """If cache is empty, query LeaderboardSnapshot and write cache."""
        player = User.objects.create(username="player3", email="player3@example.com")
        
        # Create snapshots
        snapshot1 = LeaderboardSnapshot.objects.create(
            date=timezone.now().date() - timedelta(days=2),
            leaderboard_type="season",
            player=player,
            rank=10,
            points=1800,
        )
        snapshot2 = LeaderboardSnapshot.objects.create(
            date=timezone.now().date() - timedelta(days=1),
            leaderboard_type="season",
            player=player,
            rank=8,
            points=2000,
        )
        
        # Call service
        response = get_player_leaderboard_history(player.id)
        
        assert len(response.snapshots) == 2
        # Should be ordered by date descending (most recent first)
        assert response.snapshots[0]["rank"] == 8  # Yesterday
        assert response.snapshots[1]["rank"] == 10  # 2 days ago
        
        # Verify cache was written
        cache_key = f"lb:player_history:{player.id}"
        cached = cache.get(cache_key)
        assert cached is not None
        assert len(cached["snapshots"]) == 2


@pytest.mark.django_db
class TestScopedLeaderboard:
    """Test get_scoped_leaderboard() with season/all-time scopes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_seasonal_leaderboard_requires_season_id(self):
        """If scope='season' but season_id is None, raise ValueError."""
        with pytest.raises(ValueError, match="season_id is required"):
            get_scoped_leaderboard(scope="season")
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalid_scope_raises_error(self):
        """If scope not in ['season', 'all_time'], raise ValueError."""
        with pytest.raises(ValueError, match="Invalid scope"):
            get_scoped_leaderboard(scope="invalid_scope")
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_seasonal_leaderboard_with_game_filter(self):
        """Query seasonal leaderboard for specific game."""
        player = User.objects.create(username="player4", email="player4@example.com")
        
        # Create seasonal entries for different games
        entry_valorant = LeaderboardEntry.objects.create(
            leaderboard_type="season",
            season="2025_S1",
            game="valorant",
            player=player,
            rank=1,
            points=3000,
            wins=15,
            losses=2,
            win_rate=88.24,
            is_active=True,
        )
        entry_cs2 = LeaderboardEntry.objects.create(
            leaderboard_type="season",
            season="2025_S1",
            game="cs2",
            player=player,
            rank=5,
            points=1500,
            wins=8,
            losses=3,
            win_rate=72.73,
            is_active=True,
        )
        
        # Query Valorant leaderboard only
        response = get_scoped_leaderboard(
            scope="season",
            game_code="valorant",
            season_id="2025_S1"
        )
        
        assert len(response.entries) == 1
        assert response.entries[0].points == 3000
        assert response.metadata["game_code"] == "valorant"
        assert response.metadata["season_id"] == "2025_S1"
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_all_time_leaderboard_no_game_filter(self):
        """Query all-time leaderboard across all games."""
        player1 = User.objects.create(username="player5", email="player5@example.com")
        player2 = User.objects.create(username="player6", email="player6@example.com")
        
        # Create all-time entries for different games
        LeaderboardEntry.objects.create(
            leaderboard_type="all_time",
            player=player1,
            rank=1,
            points=5000,
            wins=30,
            losses=5,
            win_rate=85.71,
            is_active=True,
        )
        LeaderboardEntry.objects.create(
            leaderboard_type="all_time",
            player=player2,
            rank=2,
            points=4500,
            wins=28,
            losses=6,
            win_rate=82.35,
            is_active=True,
        )
        
        # Query all-time (no game filter)
        response = get_scoped_leaderboard(scope="all_time")
        
        assert len(response.entries) == 2
        assert response.entries[0].rank == 1
        assert response.entries[1].rank == 2
        assert response.metadata["game_code"] is None
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_scoped_leaderboard_cache_ttl_differs_by_scope(self):
        """Seasonal leaderboards have 1h TTL, all-time have 24h TTL."""
        player = User.objects.create(username="player7", email="player7@example.com")
        
        # Create seasonal entry
        LeaderboardEntry.objects.create(
            leaderboard_type="season",
            season="2025_S2",
            player=player,
            rank=1,
            points=2000,
            wins=10,
            losses=1,
            win_rate=90.91,
            is_active=True,
        )
        
        # Query seasonal leaderboard (TTL=3600s)
        response_season = get_scoped_leaderboard(scope="season", season_id="2025_S2")
        
        # Create all-time entry
        LeaderboardEntry.objects.create(
            leaderboard_type="all_time",
            player=player,
            rank=1,
            points=5500,
            wins=35,
            losses=5,
            win_rate=87.50,
            is_active=True,
        )
        
        # Query all-time leaderboard (TTL=86400s)
        response_all_time = get_scoped_leaderboard(scope="all_time")
        
        # Both should be cache misses initially
        assert response_season.metadata["cache_hit"] is False
        assert response_all_time.metadata["cache_hit"] is False
        
        # Verify cache keys exist
        cache_key_season = "lb:season:2025_S2:ALL"
        cache_key_all_time = "lb:all_time:ALL"
        assert cache.get(cache_key_season) is not None
        assert cache.get(cache_key_all_time) is not None


@pytest.mark.django_db
class TestCacheInvalidation:
    """Test cache invalidation functions."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalidate_tournament_cache(self):
        """invalidate_tournament_cache() should clear cache key."""
        tournament_id = 555
        cache_key = f"lb:tournament:{tournament_id}"
        
        # Pre-populate cache
        cache.set(cache_key, {"entries": []}, timeout=300)
        assert cache.get(cache_key) is not None
        
        # Invalidate
        result = invalidate_tournament_cache(tournament_id)
        
        assert result is True
        assert cache.get(cache_key) is None
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=False)
    def test_invalidate_tournament_cache_disabled_returns_false(self):
        """If CACHE_ENABLED=False, invalidate returns False."""
        result = invalidate_tournament_cache(999)
        assert result is False
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalidate_player_history_cache(self):
        """invalidate_player_history_cache() should clear cache key."""
        player_id = 888
        cache_key = f"lb:player_history:{player_id}"
        
        # Pre-populate cache
        cache.set(cache_key, {"snapshots": []}, timeout=3600)
        assert cache.get(cache_key) is not None
        
        # Invalidate
        result = invalidate_player_history_cache(player_id)
        
        assert result is True
        assert cache.get(cache_key) is None
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalidate_scoped_cache_season(self):
        """invalidate_scoped_cache() should clear season cache."""
        cache_key = "lb:season:2025_S3:cs2"
        
        # Pre-populate cache
        cache.set(cache_key, {"entries": []}, timeout=3600)
        assert cache.get(cache_key) is not None
        
        # Invalidate
        result = invalidate_scoped_cache(scope="season", game_code="cs2", season_id="2025_S3")
        
        assert result is True
        assert cache.get(cache_key) is None
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalidate_scoped_cache_all_time(self):
        """invalidate_scoped_cache() should clear all-time cache."""
        cache_key = "lb:all_time:valorant"
        
        # Pre-populate cache
        cache.set(cache_key, {"entries": []}, timeout=86400)
        assert cache.get(cache_key) is not None
        
        # Invalidate
        result = invalidate_scoped_cache(scope="all_time", game_code="valorant")
        
        assert result is True
        assert cache.get(cache_key) is None
    
    @override_settings(LEADERBOARDS_CACHE_ENABLED=True)
    def test_invalidate_scoped_cache_requires_season_id_for_season(self):
        """If scope='season' but season_id is None, raise ValueError."""
        with pytest.raises(ValueError, match="season_id required"):
            invalidate_scoped_cache(scope="season")


@pytest.mark.django_db
class TestDTOSerialization:
    """Test DTO to_dict() serialization."""
    
    def test_leaderboard_entry_dto_to_dict(self):
        """LeaderboardEntryDTO.to_dict() should return JSON-serializable dict."""
        dto = LeaderboardEntryDTO(
            rank=3,
            player_id=123,
            team_id=45,
            points=1800,
            wins=12,
            losses=4,
            win_rate=75.0,
            last_updated=datetime(2025, 11, 13, 12, 30, 0),
        )
        
        result = dto.to_dict()
        
        assert result["rank"] == 3
        assert result["player_id"] == 123
        assert result["team_id"] == 45
        assert result["points"] == 1800
        assert result["wins"] == 12
        assert result["losses"] == 4
        assert result["win_rate"] == 75.0
        assert result["last_updated"] == "2025-11-13T12:30:00"
    
    def test_player_history_dto_to_dict(self):
        """PlayerHistoryDTO.to_dict() should return JSON-serializable dict."""
        dto = PlayerHistoryDTO(
            player_id=456,
            snapshots=[
                {"date": "2025-11-10", "rank": 5, "points": 2000},
                {"date": "2025-11-11", "rank": 4, "points": 2200},
            ]
        )
        
        result = dto.to_dict()
        
        assert result["player_id"] == 456
        assert result["count"] == 2
        assert len(result["history"]) == 2
        assert result["history"][0]["rank"] == 5
    
    def test_leaderboard_response_dto_to_dict(self):
        """LeaderboardResponseDTO.to_dict() should return JSON-serializable dict."""
        entry1 = LeaderboardEntryDTO(
            rank=1,
            player_id=10,
            team_id=None,
            points=3000,
            wins=20,
            losses=2,
            win_rate=90.91,
            last_updated=datetime(2025, 11, 13, 14, 0, 0),
        )
        
        dto = LeaderboardResponseDTO(
            scope="all_time",
            entries=[entry1],
            metadata={"count": 1, "cache_hit": True},
        )
        
        result = dto.to_dict()
        
        assert result["scope"] == "all_time"
        assert len(result["entries"]) == 1
        assert result["entries"][0]["rank"] == 1
        assert result["metadata"]["count"] == 1


@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_tournament_leaderboard_nonexistent_tournament(self):
        """Query for nonexistent tournament returns empty list."""
        response = get_tournament_leaderboard(tournament_id=99999)
        
        assert response.entries == []
        assert response.metadata["count"] == 0
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_player_history_nonexistent_player(self):
        """Query for nonexistent player returns empty snapshots."""
        response = get_player_leaderboard_history(player_id=99999)
        
        assert response.snapshots == []
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_scoped_leaderboard_no_entries(self):
        """Query for scope with no entries returns empty list."""
        response = get_scoped_leaderboard(scope="all_time", game_code="nonexistent_game")
        
        assert response.entries == []
        assert response.metadata["count"] == 0
    
    @override_settings(LEADERBOARDS_COMPUTE_ENABLED=True, LEADERBOARDS_CACHE_ENABLED=True)
    def test_entries_with_null_team_id(self):
        """Entries with team_id=None should serialize correctly."""
        player = User.objects.create(username="solo", email="solo@example.com")
        
        entry = LeaderboardEntry.objects.create(
            leaderboard_type="all_time",
            player=player,
            team=None,  # No team
            rank=1,
            points=2500,
            wins=18,
            losses=3,
            win_rate=85.71,
            is_active=True,
        )
        
        response = get_scoped_leaderboard(scope="all_time")
        
        assert len(response.entries) == 1
        assert response.entries[0].team_id is None
        assert response.entries[0].player_id == player.id
