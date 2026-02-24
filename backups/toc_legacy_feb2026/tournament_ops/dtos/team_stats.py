"""
Data Transfer Objects for Team Stats

Phase 8, Epic 8.3: Team Stats & Ranking System
DTOs for team statistics and ELO ratings.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TeamStatsDTO:
    """
    Team statistics data transfer object.
    
    Represents aggregated match statistics for a team in a specific game.
    Immutable DTO for cross-boundary communication.
    
    Reference: Phase 8, Epic 8.3 - Team Stats
    """
    
    team_id: int
    game_slug: str
    matches_played: int
    matches_won: int
    matches_lost: int
    matches_drawn: int
    tournaments_played: int
    tournaments_won: int
    win_rate: Decimal
    last_match_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_model(cls, stats):
        """
        Create DTO from TeamStats model (duck-typed, no ORM import).
        
        Args:
            stats: TeamStats model instance
            
        Returns:
            TeamStatsDTO
        """
        return cls(
            team_id=stats.team_id,
            game_slug=stats.game_slug,
            matches_played=stats.matches_played,
            matches_won=stats.matches_won,
            matches_lost=stats.matches_lost,
            matches_drawn=stats.matches_drawn,
            tournaments_played=stats.tournaments_played,
            tournaments_won=stats.tournaments_won,
            win_rate=stats.win_rate,
            last_match_at=stats.last_match_at,
            created_at=stats.created_at,
            updated_at=stats.updated_at,
        )
    
    def validate(self):
        """
        Validate DTO data integrity.
        
        Raises:
            ValidationError: If data is invalid
        """
        from apps.tournament_ops.exceptions import ValidationError
        
        if not self.team_id or self.team_id <= 0:
            raise ValidationError("team_id is required and must be positive")
        
        if not self.game_slug or not self.game_slug.strip():
            raise ValidationError("game_slug cannot be empty")
        
        if self.matches_played < 0:
            raise ValidationError("matches_played must be >= 0")
        
        if self.matches_won < 0:
            raise ValidationError("matches_won must be >= 0")
        
        if self.matches_lost < 0:
            raise ValidationError("matches_lost must be >= 0")
        
        if self.matches_drawn < 0:
            raise ValidationError("matches_drawn must be >= 0")
        
        if self.tournaments_played < 0:
            raise ValidationError("tournaments_played must be >= 0")
        
        if self.tournaments_won < 0:
            raise ValidationError("tournaments_won must be >= 0")
        
        if self.win_rate < Decimal("0.00") or self.win_rate > Decimal("100.00"):
            raise ValidationError("win_rate must be between 0.00 and 100.00")
    
    def to_dict(self):
        """Serialize to plain dict for API responses."""
        return {
            "team_id": self.team_id,
            "game_slug": self.game_slug,
            "matches_played": self.matches_played,
            "matches_won": self.matches_won,
            "matches_lost": self.matches_lost,
            "matches_drawn": self.matches_drawn,
            "tournaments_played": self.tournaments_played,
            "tournaments_won": self.tournaments_won,
            "win_rate": self.win_rate,
            "last_match_at": self.last_match_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class TeamRankingDTO:
    """
    Team ranking/ELO data transfer object.
    
    Represents competitive rating for a team in a specific game.
    Uses ELO rating system (K-factor = 32).
    
    Reference: Phase 8, Epic 8.3 - Team Ranking System
    """
    
    team_id: int
    game_slug: str
    elo_rating: int
    peak_elo: int
    games_played: int
    wins: int
    losses: int
    draws: int
    rank: Optional[int]  # Computed rank position (1 = top)
    last_updated: datetime
    created_at: datetime
    
    @classmethod
    def from_model(cls, ranking):
        """
        Create DTO from TeamRanking model (duck-typed).
        
        Args:
            ranking: TeamRanking model instance
            
        Returns:
            TeamRankingDTO
        """
        return cls(
            team_id=ranking.team_id,
            game_slug=ranking.game_slug,
            elo_rating=ranking.elo_rating,
            peak_elo=ranking.peak_elo,
            games_played=ranking.games_played,
            wins=ranking.wins,
            losses=ranking.losses,
            draws=ranking.draws,
            rank=ranking.rank,
            last_updated=ranking.last_updated,
            created_at=ranking.created_at,
        )
    
    def validate(self):
        """
        Validate DTO data integrity.
        
        Raises:
            ValidationError: If data is invalid
        """
        from apps.tournament_ops.exceptions import ValidationError
        
        if not self.team_id or self.team_id <= 0:
            raise ValidationError("team_id is required and must be positive")
        
        if not self.game_slug or not self.game_slug.strip():
            raise ValidationError("game_slug cannot be empty")
        
        if self.elo_rating < 0:
            raise ValidationError("elo_rating must be >= 0")
        
        if self.peak_elo < 0:
            raise ValidationError("peak_elo must be >= 0")
        
        if self.games_played < 0:
            raise ValidationError("games_played must be >= 0")
        
        if self.wins < 0:
            raise ValidationError("wins must be >= 0")
        
        if self.losses < 0:
            raise ValidationError("losses must be >= 0")
        
        if self.draws < 0:
            raise ValidationError("draws must be >= 0")
        
        if self.rank is not None and self.rank < 1:
            raise ValidationError("rank must be >= 1 when set")
    
    def to_dict(self):
        """Serialize to plain dict for API responses."""
        return {
            "team_id": self.team_id,
            "game_slug": self.game_slug,
            "elo_rating": self.elo_rating,
            "peak_elo": self.peak_elo,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "rank": self.rank,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TeamStatsSummaryDTO:
    """
    Lightweight team stats summary for UI widgets.
    
    Aggregated view of team performance metrics.
    Used for dashboard cards, leaderboard listings, etc.
    
    Reference: Phase 8, Epic 8.3 - Team Stats API
    """
    
    team_id: int
    game_slug: Optional[str]  # None = all games aggregated
    total_matches: int
    total_wins: int
    win_rate: Decimal
    total_tournaments: int
    elo_rating: Optional[int]  # Current ELO (if available)
    rank: Optional[int]  # Current rank (if available)
    last_played: Optional[datetime]
    
    @classmethod
    def from_team_stats_dto(cls, stats: TeamStatsDTO, ranking: Optional[TeamRankingDTO] = None):
        """
        Create summary from full TeamStatsDTO + optional ranking.
        
        Args:
            stats: Full team stats DTO
            ranking: Optional ranking DTO for ELO/rank data
            
        Returns:
            TeamStatsSummaryDTO
        """
        return cls(
            team_id=stats.team_id,
            game_slug=stats.game_slug,
            total_matches=stats.matches_played,
            total_wins=stats.matches_won,
            win_rate=stats.win_rate,
            total_tournaments=stats.tournaments_played,
            elo_rating=ranking.elo_rating if ranking else None,
            rank=ranking.rank if ranking else None,
            last_played=stats.last_match_at,
        )
    
    def validate(self):
        """
        Validate summary data.
        
        Raises:
            ValidationError: If data is invalid
        """
        from apps.tournament_ops.exceptions import ValidationError
        
        if not self.team_id or self.team_id <= 0:
            raise ValidationError("team_id is required and must be positive")
        
        if self.total_matches < 0:
            raise ValidationError("total_matches must be >= 0")
        
        if self.total_wins < 0:
            raise ValidationError("total_wins must be >= 0")
    
    def to_dict(self):
        """Serialize to plain dict for API responses."""
        return {
            "team_id": self.team_id,
            "game_slug": self.game_slug,
            "total_matches": self.total_matches,
            "total_wins": self.total_wins,
            "win_rate": self.win_rate,
            "total_tournaments": self.total_tournaments,
            "elo_rating": self.elo_rating,
            "rank": self.rank,
            "last_played": self.last_played,
        }


@dataclass(frozen=True)
class TeamMatchStatsUpdateDTO:
    """
    Event payload for team match completion stats updates.
    
    Used by MatchCompletedEvent handlers to update team stats + rankings.
    Contains match outcome data needed for stats/ELO calculations.
    
    Reference: Phase 8, Epic 8.3 - Event Integration
    """
    
    team_id: int
    game_slug: str
    is_winner: bool
    is_draw: bool
    opponent_team_id: int  # For ELO calculations
    opponent_elo: int  # Opponent's current ELO rating
    match_id: int
    
    def validate(self):
        """
        Validate event payload data.
        
        Raises:
            ValidationError: If data is invalid
        """
        from apps.tournament_ops.exceptions import ValidationError
        
        if not self.team_id or self.team_id <= 0:
            raise ValidationError("team_id is required and must be positive")
        
        if not self.game_slug or not self.game_slug.strip():
            raise ValidationError("game_slug cannot be empty")
        
        if self.is_winner and self.is_draw:
            raise ValidationError("Cannot be both winner and draw")
        
        if not self.opponent_team_id or self.opponent_team_id <= 0:
            raise ValidationError("opponent_team_id is required and must be positive")
        
        if self.opponent_elo < 0:
            raise ValidationError("opponent_elo must be >= 0")
        
        if not self.match_id or self.match_id <= 0:
            raise ValidationError("match_id is required and must be positive")
    
    def to_dict(self):
        """Serialize to plain dict."""
        return {
            "team_id": self.team_id,
            "game_slug": self.game_slug,
            "is_winner": self.is_winner,
            "is_draw": self.is_draw,
            "opponent_team_id": self.opponent_team_id,
            "opponent_elo": self.opponent_elo,
            "match_id": self.match_id,
        }
