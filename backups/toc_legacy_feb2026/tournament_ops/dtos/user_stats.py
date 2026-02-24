"""
Data Transfer Objects (DTOs) for User Stats System

Phase 8, Epic 8.2: User Stats Service
Provides DTOs for user statistics and performance metrics.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


@dataclass
class UserStatsDTO:
    """
    DTO for comprehensive user statistics.
    Represents aggregated stats for a user in a specific game.
    """
    user_id: int
    game_slug: str
    matches_played: int
    matches_won: int
    matches_lost: int
    matches_drawn: int
    tournaments_played: int
    tournaments_won: int
    win_rate: Decimal
    total_kills: int
    total_deaths: int
    kd_ratio: Decimal
    last_match_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, user_stats) -> 'UserStatsDTO':
        """
        Convert UserStats model instance to DTO.
        
        Args:
            user_stats: UserStats model instance
            
        Returns:
            UserStatsDTO instance
        """
        return cls(
            user_id=user_stats.user_id,
            game_slug=user_stats.game_slug,
            matches_played=user_stats.matches_played,
            matches_won=user_stats.matches_won,
            matches_lost=user_stats.matches_lost,
            matches_drawn=user_stats.matches_drawn,
            tournaments_played=user_stats.tournaments_played,
            tournaments_won=user_stats.tournaments_won,
            win_rate=user_stats.win_rate,
            total_kills=user_stats.total_kills,
            total_deaths=user_stats.total_deaths,
            kd_ratio=user_stats.kd_ratio,
            last_match_at=user_stats.last_match_at,
            created_at=user_stats.created_at,
            updated_at=user_stats.updated_at,
        )
    
    def validate(self):
        """Validate DTO fields."""
        if self.user_id is None or self.user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        if not self.game_slug:
            raise ValueError("game_slug is required")
        if self.matches_played < 0:
            raise ValueError("matches_played cannot be negative")
        if self.matches_won < 0:
            raise ValueError("matches_won cannot be negative")
        if self.matches_lost < 0:
            raise ValueError("matches_lost cannot be negative")
        if self.matches_drawn < 0:
            raise ValueError("matches_drawn cannot be negative")
        if self.tournaments_played < 0:
            raise ValueError("tournaments_played cannot be negative")
        if self.tournaments_won < 0:
            raise ValueError("tournaments_won cannot be negative")
        if self.win_rate < 0 or self.win_rate > 100:
            raise ValueError("win_rate must be between 0 and 100")
        if self.total_kills < 0:
            raise ValueError("total_kills cannot be negative")
        if self.total_deaths < 0:
            raise ValueError("total_deaths cannot be negative")
        if self.kd_ratio < 0:
            raise ValueError("kd_ratio cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'user_id': self.user_id,
            'game_slug': self.game_slug,
            'matches_played': self.matches_played,
            'matches_won': self.matches_won,
            'matches_lost': self.matches_lost,
            'matches_drawn': self.matches_drawn,
            'tournaments_played': self.tournaments_played,
            'tournaments_won': self.tournaments_won,
            'win_rate': float(self.win_rate),
            'total_kills': self.total_kills,
            'total_deaths': self.total_deaths,
            'kd_ratio': float(self.kd_ratio),
            'last_match_at': self.last_match_at.isoformat() if self.last_match_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class UserStatsSummaryDTO:
    """
    DTO for lightweight user stats summary (for UI lists/cards).
    Contains only essential metrics for display purposes.
    """
    user_id: int
    username: str
    game_slug: str
    matches_played: int
    matches_won: int
    win_rate: Decimal
    kd_ratio: Decimal
    last_match_at: Optional[datetime] = None
    
    @classmethod
    def from_user_stats_dto(cls, user_stats_dto: UserStatsDTO, username: str) -> 'UserStatsSummaryDTO':
        """
        Create summary DTO from full UserStatsDTO.
        
        Args:
            user_stats_dto: Full UserStatsDTO instance
            username: User's username
            
        Returns:
            UserStatsSummaryDTO instance
        """
        return cls(
            user_id=user_stats_dto.user_id,
            username=username,
            game_slug=user_stats_dto.game_slug,
            matches_played=user_stats_dto.matches_played,
            matches_won=user_stats_dto.matches_won,
            win_rate=user_stats_dto.win_rate,
            kd_ratio=user_stats_dto.kd_ratio,
            last_match_at=user_stats_dto.last_match_at,
        )
    
    def validate(self):
        """Validate DTO fields."""
        if self.user_id is None or self.user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        if not self.username:
            raise ValueError("username is required")
        if not self.game_slug:
            raise ValueError("game_slug is required")
        if self.matches_played < 0:
            raise ValueError("matches_played cannot be negative")
        if self.matches_won < 0:
            raise ValueError("matches_won cannot be negative")
        if self.win_rate < 0 or self.win_rate > 100:
            raise ValueError("win_rate must be between 0 and 100")
        if self.kd_ratio < 0:
            raise ValueError("kd_ratio cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'game_slug': self.game_slug,
            'matches_played': self.matches_played,
            'matches_won': self.matches_won,
            'win_rate': float(self.win_rate),
            'kd_ratio': float(self.kd_ratio),
            'last_match_at': self.last_match_at.isoformat() if self.last_match_at else None,
        }


@dataclass
class MatchStatsUpdateDTO:
    """
    DTO for match stats update payload.
    Contains data needed to update user stats after match completion.
    """
    user_id: int
    game_slug: str
    tournament_id: int
    match_id: int
    is_winner: bool
    is_draw: bool = False
    kills: int = 0
    deaths: int = 0
    match_completed_at: Optional[datetime] = None
    
    def validate(self):
        """Validate DTO fields."""
        if self.user_id is None or self.user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        if not self.game_slug:
            raise ValueError("game_slug is required")
        if self.tournament_id is None or self.tournament_id <= 0:
            raise ValueError("tournament_id must be a positive integer")
        if self.match_id is None or self.match_id <= 0:
            raise ValueError("match_id must be a positive integer")
        if self.kills < 0:
            raise ValueError("kills cannot be negative")
        if self.deaths < 0:
            raise ValueError("deaths cannot be negative")
        if self.is_winner and self.is_draw:
            raise ValueError("match cannot be both won and drawn")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'user_id': self.user_id,
            'game_slug': self.game_slug,
            'tournament_id': self.tournament_id,
            'match_id': self.match_id,
            'is_winner': self.is_winner,
            'is_draw': self.is_draw,
            'kills': self.kills,
            'deaths': self.deaths,
            'match_completed_at': self.match_completed_at.isoformat() if self.match_completed_at else None,
        }
