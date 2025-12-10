"""
Analytics DTOs for Epic 8.5 - Advanced Analytics, Ranking Tiers & Real-Time Leaderboards.

Data Transfer Objects for analytics snapshots, leaderboard entries, seasons, and queries.
All DTOs provide validation, serialization, and model mapping.

Reference: Phase 8, Epic 8.5 - Advanced Analytics & Ranking Tiers
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base import DTOBase


# =============================================================================
# Base Analytics DTO
# =============================================================================

@dataclass
class AnalyticsSnapshotDTO(DTOBase):
    """
    Base analytics snapshot DTO.
    
    Provides common fields and validation for user and team analytics snapshots.
    """
    
    game_slug: str
    elo_snapshot: int
    win_rate: Decimal
    tier: str
    percentile_rank: Decimal
    recalculated_at: datetime
    
    def validate(self) -> None:
        """Validate analytics snapshot fields."""
        if not self.game_slug or not self.game_slug.strip():
            raise ValueError("game_slug cannot be empty")
        
        if self.elo_snapshot < 0:
            raise ValueError("elo_snapshot cannot be negative")
        
        if not (0 <= self.win_rate <= 100):
            raise ValueError("win_rate must be between 0 and 100")
        
        valid_tiers = ["bronze", "silver", "gold", "diamond", "crown"]
        if self.tier not in valid_tiers:
            raise ValueError(f"tier must be one of {valid_tiers}")
        
        if not (0 <= self.percentile_rank <= 100):
            raise ValueError("percentile_rank must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict with datetime formatting."""
        data = asdict(self)
        # Convert datetime to ISO format
        if isinstance(data.get("recalculated_at"), datetime):
            data["recalculated_at"] = data["recalculated_at"].isoformat()
        # Convert Decimal to float for JSON serialization
        for key in ["win_rate", "percentile_rank"]:
            if key in data and isinstance(data[key], Decimal):
                data[key] = float(data[key])
        return data


# =============================================================================
# User Analytics DTO
# =============================================================================

@dataclass
class UserAnalyticsDTO(AnalyticsSnapshotDTO):
    """
    User analytics snapshot DTO.
    
    Represents rich analytics for a user's performance in a specific game.
    Includes MMR/ELO snapshot, win rates, KDA, rolling averages, streaks, tier, percentile.
    """
    
    user_id: int = 0
    mmr_snapshot: int = 1200
    kda_ratio: Decimal = Decimal("0.0")
    matches_last_7d: int = 0
    matches_last_30d: int = 0
    win_rate_7d: Decimal = Decimal("0.0")
    win_rate_30d: Decimal = Decimal("0.0")
    current_streak: int = 0
    longest_win_streak: int = 0
    
    @classmethod
    def from_model(cls, snapshot: Any) -> "UserAnalyticsDTO":
        """
        Create DTO from UserAnalyticsSnapshot model instance.
        
        Args:
            snapshot: UserAnalyticsSnapshot model instance (ORM object)
        
        Returns:
            UserAnalyticsDTO instance
        """
        return cls(
            user_id=snapshot.user_id,
            game_slug=snapshot.game_slug,
            mmr_snapshot=snapshot.mmr_snapshot,
            elo_snapshot=snapshot.elo_snapshot,
            win_rate=snapshot.win_rate,
            kda_ratio=snapshot.kda_ratio,
            matches_last_7d=snapshot.matches_last_7d,
            matches_last_30d=snapshot.matches_last_30d,
            win_rate_7d=snapshot.win_rate_7d,
            win_rate_30d=snapshot.win_rate_30d,
            current_streak=snapshot.current_streak,
            longest_win_streak=snapshot.longest_win_streak,
            tier=snapshot.tier,
            percentile_rank=snapshot.percentile_rank,
            recalculated_at=snapshot.recalculated_at,
        )
    
    def validate(self) -> None:
        """Validate user analytics fields."""
        super().validate()
        
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        
        if self.mmr_snapshot < 0:
            raise ValueError("mmr_snapshot cannot be negative")
        
        if self.kda_ratio < 0:
            raise ValueError("kda_ratio cannot be negative")
        
        if self.matches_last_7d < 0 or self.matches_last_30d < 0:
            raise ValueError("match counts cannot be negative")
        
        if not (0 <= self.win_rate_7d <= 100) or not (0 <= self.win_rate_30d <= 100):
            raise ValueError("rolling win rates must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict with proper type conversions."""
        data = super().to_dict()
        # Convert additional Decimal fields
        for key in ["kda_ratio", "win_rate_7d", "win_rate_30d"]:
            if key in data and isinstance(data[key], Decimal):
                data[key] = float(data[key])
        return data


# =============================================================================
# Team Analytics DTO
# =============================================================================

@dataclass
class TeamAnalyticsDTO(AnalyticsSnapshotDTO):
    """
    Team analytics snapshot DTO.
    
    Represents rich analytics for a team's performance in a specific game.
    Includes ELO snapshot, volatility, avg member skill, win rates, synergy, activity.
    """
    
    team_id: int = 0
    elo_volatility: Decimal = Decimal("0.0")
    avg_member_skill: Decimal = Decimal("1200.0")
    win_rate_7d: Decimal = Decimal("0.0")
    win_rate_30d: Decimal = Decimal("0.0")
    synergy_score: Decimal = Decimal("0.0")
    activity_score: Decimal = Decimal("0.0")
    matches_last_7d: int = 0
    matches_last_30d: int = 0
    
    @classmethod
    def from_model(cls, snapshot: Any) -> "TeamAnalyticsDTO":
        """
        Create DTO from TeamAnalyticsSnapshot model instance.
        
        Args:
            snapshot: TeamAnalyticsSnapshot model instance
        
        Returns:
            TeamAnalyticsDTO instance
        """
        return cls(
            team_id=snapshot.team_id,
            game_slug=snapshot.game_slug,
            elo_snapshot=snapshot.elo_snapshot,
            elo_volatility=snapshot.elo_volatility,
            avg_member_skill=snapshot.avg_member_skill,
            win_rate=snapshot.win_rate,
            win_rate_7d=snapshot.win_rate_7d,
            win_rate_30d=snapshot.win_rate_30d,
            synergy_score=snapshot.synergy_score,
            activity_score=snapshot.activity_score,
            matches_last_7d=snapshot.matches_last_7d,
            matches_last_30d=snapshot.matches_last_30d,
            tier=snapshot.tier,
            percentile_rank=snapshot.percentile_rank,
            recalculated_at=snapshot.recalculated_at,
        )
    
    def validate(self) -> None:
        """Validate team analytics fields."""
        super().validate()
        
        if self.team_id <= 0:
            raise ValueError("team_id must be positive")
        
        if self.elo_volatility < 0:
            raise ValueError("elo_volatility cannot be negative")
        
        if self.avg_member_skill < 0:
            raise ValueError("avg_member_skill cannot be negative")
        
        if not (0 <= self.win_rate_7d <= 100) or not (0 <= self.win_rate_30d <= 100):
            raise ValueError("rolling win rates must be between 0 and 100")
        
        if not (0 <= self.synergy_score <= 100):
            raise ValueError("synergy_score must be between 0 and 100")
        
        if not (0 <= self.activity_score <= 100):
            raise ValueError("activity_score must be between 0 and 100")
        
        if self.matches_last_7d < 0 or self.matches_last_30d < 0:
            raise ValueError("match counts cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict with proper type conversions."""
        data = super().to_dict()
        # Convert additional Decimal fields
        for key in ["elo_volatility", "avg_member_skill", "win_rate_7d", "win_rate_30d", "synergy_score", "activity_score"]:
            if key in data and isinstance(data[key], Decimal):
                data[key] = float(data[key])
        return data


# =============================================================================
# Leaderboard Entry DTO
# =============================================================================

@dataclass
class LeaderboardEntryDTO(DTOBase):
    """
    Leaderboard entry DTO.
    
    Represents a single leaderboard entry with rank, score, and metadata.
    Supports flexible payload for leaderboard-specific data (tier, percentile, streak, etc.).
    """
    
    leaderboard_type: str
    rank: int
    reference_id: int  # User ID or Team ID
    game_slug: Optional[str] = None
    season_id: Optional[str] = None
    score: int = 0  # Could be ELO, MMR, or custom points
    wins: int = 0
    losses: int = 0
    win_rate: Decimal = Decimal("0.0")
    payload: Dict[str, Any] = field(default_factory=dict)
    computed_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, entry: Any) -> "LeaderboardEntryDTO":
        """
        Create DTO from LeaderboardEntry model instance.
        
        Args:
            entry: LeaderboardEntry model instance
        
        Returns:
            LeaderboardEntryDTO instance
        """
        return cls(
            leaderboard_type=entry.leaderboard_type,
            rank=entry.rank,
            reference_id=entry.reference_id or (entry.player_id or entry.team_id),
            game_slug=entry.game,
            season_id=entry.season,
            score=entry.points,
            wins=entry.wins,
            losses=entry.losses,
            win_rate=entry.win_rate,
            payload=entry.payload_json or {},
            computed_at=entry.computed_at,
        )
    
    def validate(self) -> None:
        """Validate leaderboard entry fields."""
        if not self.leaderboard_type or not self.leaderboard_type.strip():
            raise ValueError("leaderboard_type cannot be empty")
        
        if self.rank <= 0:
            raise ValueError("rank must be positive")
        
        if self.reference_id <= 0:
            raise ValueError("reference_id must be positive")
        
        if self.wins < 0 or self.losses < 0:
            raise ValueError("wins and losses cannot be negative")
        
        if not (0 <= self.win_rate <= 100):
            raise ValueError("win_rate must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict with proper type conversions."""
        data = asdict(self)
        # Convert datetime
        if isinstance(data.get("computed_at"), datetime):
            data["computed_at"] = data["computed_at"].isoformat()
        # Convert Decimal
        if isinstance(data.get("win_rate"), Decimal):
            data["win_rate"] = float(data["win_rate"])
        return data


# =============================================================================
# Season DTO
# =============================================================================

@dataclass
class SeasonDTO(DTOBase):
    """
    Season DTO.
    
    Represents a competitive season with time boundaries and decay rules.
    """
    
    season_id: str
    name: str
    start_date: datetime
    end_date: datetime
    is_active: bool = False
    decay_rules: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_model(cls, season: Any) -> "SeasonDTO":
        """
        Create DTO from Season model instance.
        
        Args:
            season: Season model instance
        
        Returns:
            SeasonDTO instance
        """
        return cls(
            season_id=season.season_id,
            name=season.name,
            start_date=season.start_date,
            end_date=season.end_date,
            is_active=season.is_active,
            decay_rules=season.decay_rules_json or {},
        )
    
    def validate(self) -> None:
        """Validate season fields."""
        if not self.season_id or not self.season_id.strip():
            raise ValueError("season_id cannot be empty")
        
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict with datetime formatting."""
        data = asdict(self)
        # Convert datetime fields
        for key in ["start_date", "end_date"]:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        return data


# =============================================================================
# Analytics Query DTO
# =============================================================================

@dataclass
class AnalyticsQueryDTO(DTOBase):
    """
    Analytics query DTO for filtering and pagination.
    
    Provides filtering options for analytics and leaderboard queries.
    """
    
    game_slug: Optional[str] = None
    season_id: Optional[str] = None
    tier: Optional[str] = None
    min_elo: Optional[int] = None
    max_elo: Optional[int] = None
    min_percentile: Optional[Decimal] = None
    max_percentile: Optional[Decimal] = None
    limit: int = 100
    offset: int = 0
    order_by: str = "-elo_snapshot"  # Default: highest ELO first
    
    def validate(self) -> None:
        """Validate query parameters."""
        if self.tier:
            valid_tiers = ["bronze", "silver", "gold", "diamond", "crown"]
            if self.tier not in valid_tiers:
                raise ValueError(f"tier must be one of {valid_tiers}")
        
        if self.min_elo is not None and self.min_elo < 0:
            raise ValueError("min_elo cannot be negative")
        
        if self.max_elo is not None and self.max_elo < 0:
            raise ValueError("max_elo cannot be negative")
        
        if self.min_elo is not None and self.max_elo is not None and self.min_elo > self.max_elo:
            raise ValueError("min_elo cannot be greater than max_elo")
        
        if self.min_percentile is not None and not (0 <= self.min_percentile <= 100):
            raise ValueError("min_percentile must be between 0 and 100")
        
        if self.max_percentile is not None and not (0 <= self.max_percentile <= 100):
            raise ValueError("max_percentile must be between 0 and 100")
        
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        
        valid_order_by = ["elo_snapshot", "-elo_snapshot", "percentile_rank", "-percentile_rank", "win_rate", "-win_rate"]
        if self.order_by not in valid_order_by:
            raise ValueError(f"order_by must be one of {valid_order_by}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize DTO to dict, excluding None values."""
        data = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}


# =============================================================================
# Tier Boundary Helpers
# =============================================================================

class TierBoundaries:
    """
    Tier boundary definitions for ELO/MMR-based tiering.
    
    Tier boundaries:
    - Bronze: 0-1199
    - Silver: 1200-1599
    - Gold: 1600-1999
    - Diamond: 2000-2399
    - Crown: 2400+
    """
    
    BRONZE_MIN = 0
    BRONZE_MAX = 1199
    SILVER_MIN = 1200
    SILVER_MAX = 1599
    GOLD_MIN = 1600
    GOLD_MAX = 1999
    DIAMOND_MIN = 2000
    DIAMOND_MAX = 2399
    CROWN_MIN = 2400
    
    @staticmethod
    def calculate_tier(elo_or_mmr: int) -> str:
        """
        Calculate tier based on ELO/MMR rating.
        
        Args:
            elo_or_mmr: ELO or MMR rating
        
        Returns:
            Tier name (bronze, silver, gold, diamond, crown)
        """
        if elo_or_mmr >= TierBoundaries.CROWN_MIN:
            return "crown"
        elif elo_or_mmr >= TierBoundaries.DIAMOND_MIN:
            return "diamond"
        elif elo_or_mmr >= TierBoundaries.GOLD_MIN:
            return "gold"
        elif elo_or_mmr >= TierBoundaries.SILVER_MIN:
            return "silver"
        else:
            return "bronze"
    
    @staticmethod
    def get_tier_boundaries() -> Dict[str, Dict[str, int]]:
        """
        Get all tier boundaries as a dictionary.
        
        Returns:
            Dictionary mapping tier names to min/max ELO values
        """
        return {
            "bronze": {"min": TierBoundaries.BRONZE_MIN, "max": TierBoundaries.BRONZE_MAX},
            "silver": {"min": TierBoundaries.SILVER_MIN, "max": TierBoundaries.SILVER_MAX},
            "gold": {"min": TierBoundaries.GOLD_MIN, "max": TierBoundaries.GOLD_MAX},
            "diamond": {"min": TierBoundaries.DIAMOND_MIN, "max": TierBoundaries.DIAMOND_MAX},
            "crown": {"min": TierBoundaries.CROWN_MIN, "max": None},  # Open-ended
        }
