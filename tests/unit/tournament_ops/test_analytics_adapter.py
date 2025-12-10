"""
Epic 8.5 Adapter Tests - AnalyticsAdapter CRUD operations.

Tests for analytics ORM operations including snapshots, leaderboards, seasons.
Uses real test database (ORM allowed in adapters).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.leaderboards.models import (
    UserAnalyticsSnapshot,
    TeamAnalyticsSnapshot,
    LeaderboardEntry,
    Season,
)
from apps.teams.models import Team
from apps.games.models import Game
from apps.tournament_ops.adapters.analytics_adapter import AnalyticsAdapter
from apps.tournament_ops.dtos.analytics import (
    UserAnalyticsDTO,
    TeamAnalyticsDTO,
    LeaderboardEntryDTO,
    SeasonDTO,
    AnalyticsQueryDTO,
)

User = get_user_model()


@pytest.mark.django_db
class TestAnalyticsAdapter:
    """Test AnalyticsAdapter ORM operations."""
    
    @pytest.fixture
    def game(self):
        """Create test game."""
        return Game.objects.create(slug="valorant", name="Valorant")
    
    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(username="testuser", email="test@example.com")
    
    @pytest.fixture
    def team(self, game):
        """Create test team."""
        return Team.objects.create(name="Test Team", tag="TEST", game=game)
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return AnalyticsAdapter()
    
    def test_get_user_snapshot_exists(self, adapter, user, game):
        """Test get_user_snapshot returns existing snapshot."""
        # Create snapshot
        snapshot = UserAnalyticsSnapshot.objects.create(
            user=user,
            game=game,
            elo_snapshot=1500,
            win_rate=Decimal("50.0"),
            tier="silver",
            percentile_rank=Decimal("50.0"),
        )
        
        dto = adapter.get_user_snapshot(user_id=user.id, game_slug=game.slug)
        assert dto is not None
        assert dto.user_id == user.id
        assert dto.game_slug == game.slug
        assert dto.elo_snapshot == 1500
        assert dto.tier == "silver"
    
    def test_get_user_snapshot_not_exists(self, adapter, user):
        """Test get_user_snapshot returns None when not found."""
        dto = adapter.get_user_snapshot(user_id=user.id, game_slug="nonexistent")
        assert dto is None
    
    def test_update_user_snapshot_create(self, adapter, user, game):
        """Test update_user_snapshot creates new snapshot."""
        dto = UserAnalyticsDTO(
            user_id=user.id,
            game_slug=game.slug,
            elo_snapshot=1600,
            win_rate=Decimal("60.0"),
            kda_ratio=Decimal("1.5"),
            tier="gold",
            percentile_rank=Decimal("70.0"),
            recalculated_at=timezone.now(),
        )
        
        result = adapter.update_user_snapshot(dto)
        assert result.user_id == user.id
        assert result.elo_snapshot == 1600
        
        # Verify in DB
        snapshot = UserAnalyticsSnapshot.objects.get(user=user, game=game)
        assert snapshot.elo_snapshot == 1600
        assert snapshot.tier == "gold"
    
    def test_update_user_snapshot_update(self, adapter, user, game):
        """Test update_user_snapshot updates existing snapshot."""
        # Create initial
        UserAnalyticsSnapshot.objects.create(
            user=user,
            game=game,
            elo_snapshot=1500,
            win_rate=Decimal("50.0"),
            tier="silver",
            percentile_rank=Decimal("50.0"),
        )
        
        # Update
        dto = UserAnalyticsDTO(
            user_id=user.id,
            game_slug=game.slug,
            elo_snapshot=1700,
            win_rate=Decimal("65.0"),
            tier="gold",
            percentile_rank=Decimal("75.0"),
            recalculated_at=timezone.now(),
        )
        
        result = adapter.update_user_snapshot(dto)
        assert result.elo_snapshot == 1700
        
        # Verify only one snapshot exists
        assert UserAnalyticsSnapshot.objects.filter(user=user, game=game).count() == 1
        snapshot = UserAnalyticsSnapshot.objects.get(user=user, game=game)
        assert snapshot.elo_snapshot == 1700
        assert snapshot.tier == "gold"
    
    def test_list_user_snapshots_filtering(self, adapter, user, game):
        """Test list_user_snapshots with filters."""
        # Create multiple snapshots
        UserAnalyticsSnapshot.objects.create(
            user=user, game=game, elo_snapshot=1500, tier="silver", percentile_rank=Decimal("50.0")
        )
        other_user = User.objects.create_user(username="other", email="other@example.com")
        UserAnalyticsSnapshot.objects.create(
            user=other_user, game=game, elo_snapshot=1800, tier="gold", percentile_rank=Decimal("80.0")
        )
        
        # Filter by game
        query = AnalyticsQueryDTO(game_slug=game.slug)
        results = adapter.list_user_snapshots(query)
        assert len(results) == 2
        
        # Filter by tier
        query = AnalyticsQueryDTO(tier="gold")
        results = adapter.list_user_snapshots(query)
        assert len(results) == 1
        assert results[0].tier == "gold"
        
        # Filter by ELO range
        query = AnalyticsQueryDTO(min_elo=1600, max_elo=2000)
        results = adapter.list_user_snapshots(query)
        assert len(results) == 1
        assert results[0].elo_snapshot == 1800
    
    def test_get_team_snapshot(self, adapter, team):
        """Test get_team_snapshot retrieves team analytics."""
        TeamAnalyticsSnapshot.objects.create(
            team=team,
            game=team.game,
            elo_snapshot=1800,
            win_rate=Decimal("55.0"),
            synergy_score=Decimal("75.0"),
            activity_score=Decimal("80.0"),
            tier="gold",
            percentile_rank=Decimal("65.0"),
        )
        
        dto = adapter.get_team_snapshot(team_id=team.id, game_slug=team.game.slug)
        assert dto is not None
        assert dto.team_id == team.id
        assert dto.elo_snapshot == 1800
        assert dto.synergy_score == Decimal("75.0")
    
    def test_update_team_snapshot(self, adapter, team):
        """Test update_team_snapshot."""
        dto = TeamAnalyticsDTO(
            team_id=team.id,
            game_slug=team.game.slug,
            elo_snapshot=1900,
            win_rate=Decimal("60.0"),
            synergy_score=Decimal("80.0"),
            activity_score=Decimal("85.0"),
            tier="gold",
            percentile_rank=Decimal("70.0"),
            recalculated_at=timezone.now(),
        )
        
        result = adapter.update_team_snapshot(dto)
        assert result.elo_snapshot == 1900
        
        # Verify in DB
        snapshot = TeamAnalyticsSnapshot.objects.get(team=team)
        assert snapshot.synergy_score == Decimal("80.0")
    
    def test_save_leaderboard_entries_bulk(self, adapter, user, game):
        """Test save_leaderboard_entries bulk insert."""
        now = timezone.now()
        entries = [
            LeaderboardEntryDTO(
                leaderboard_type="game_user",
                rank=1,
                reference_id=user.id,
                game_slug=game.slug,
                score=2000,
                wins=50,
                losses=10,
                win_rate=Decimal("83.33"),
                payload={"tier": "diamond"},
                computed_at=now,
            ),
            LeaderboardEntryDTO(
                leaderboard_type="game_user",
                rank=2,
                reference_id=999,
                game_slug=game.slug,
                score=1900,
                wins=45,
                losses=15,
                win_rate=Decimal("75.0"),
                payload={"tier": "gold"},
                computed_at=now,
            ),
        ]
        
        adapter.save_leaderboard_entries(entries, clear_existing=True)
        
        # Verify entries
        assert LeaderboardEntry.objects.count() == 2
        top_entry = LeaderboardEntry.objects.get(rank=1)
        assert top_entry.reference_id == user.id
        assert top_entry.score == 2000
    
    def test_get_leaderboard(self, adapter, user, game):
        """Test get_leaderboard filtering."""
        now = timezone.now()
        LeaderboardEntry.objects.create(
            leaderboard_type="game_user",
            rank=1,
            reference_id=user.id,
            game_slug=game.slug,
            score=2000,
            computed_at=now,
        )
        
        results = adapter.get_leaderboard(
            leaderboard_type="game_user",
            game_slug=game.slug,
            limit=10,
        )
        
        assert len(results) == 1
        assert results[0].rank == 1
        assert results[0].reference_id == user.id
    
    def test_get_current_season_single_active(self, adapter):
        """Test get_current_season with single active season."""
        Season.objects.create(
            season_id="S1-2024",
            name="Season 1",
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() + timedelta(days=60),
            is_active=True,
        )
        
        dto = adapter.get_current_season()
        assert dto is not None
        assert dto.season_id == "S1-2024"
        assert dto.is_active is True
    
    def test_get_current_season_none_active(self, adapter):
        """Test get_current_season with no active season."""
        Season.objects.create(
            season_id="S1-2024",
            name="Season 1",
            start_date=timezone.now() - timedelta(days=90),
            end_date=timezone.now() - timedelta(days=1),
            is_active=False,
        )
        
        dto = adapter.get_current_season()
        assert dto is None
    
    def test_list_seasons_include_inactive(self, adapter):
        """Test list_seasons with include_inactive flag."""
        Season.objects.create(
            season_id="S1-2024",
            name="Season 1",
            start_date=timezone.now() - timedelta(days=90),
            end_date=timezone.now() - timedelta(days=1),
            is_active=False,
        )
        Season.objects.create(
            season_id="S2-2024",
            name="Season 2",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=90),
            is_active=True,
        )
        
        # Only active
        active_seasons = adapter.list_seasons(include_inactive=False)
        assert len(active_seasons) == 1
        assert active_seasons[0].season_id == "S2-2024"
        
        # All seasons
        all_seasons = adapter.list_seasons(include_inactive=True)
        assert len(all_seasons) == 2
