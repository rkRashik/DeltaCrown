"""
Phase 8, Epic 8.4: Match History DTOs

Data Transfer Objects for match history queries and timeline data.
Provides structured match history for users, teams, and tournaments with filtering.

Reference: ROADMAP_AND_EPICS_PART_4.md, Epic 8.4
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class MatchHistoryEntryDTO:
    """
    Base match history entry for timeline display.
    
    Contains denormalized match details for fast timeline rendering
    without additional queries. Common fields for both user and team history.
    """
    
    match_id: int
    tournament_id: int
    tournament_name: str
    game_slug: str
    
    # Result
    is_winner: bool
    is_draw: bool
    score_summary: str
    
    # Opponent (denormalized)
    opponent_id: Optional[int]
    opponent_name: str
    
    # Flags
    had_dispute: bool
    is_forfeit: bool
    
    # Timeline
    completed_at: datetime
    
    @classmethod
    def validate(cls, **kwargs) -> "MatchHistoryEntryDTO":
        """
        Validate and construct DTO with business rules.
        
        Rules:
        - match_id, tournament_id must be positive
        - game_slug must not be empty
        - completed_at must be provided
        - opponent_name defaults to "Unknown" if empty
        - score_summary defaults to empty string
        """
        match_id = kwargs.get("match_id")
        tournament_id = kwargs.get("tournament_id")
        game_slug = kwargs.get("game_slug", "").strip()
        completed_at = kwargs.get("completed_at")
        
        if not match_id or match_id <= 0:
            raise ValueError("match_id must be a positive integer")
        
        if not tournament_id or tournament_id <= 0:
            raise ValueError("tournament_id must be a positive integer")
        
        if not game_slug:
            raise ValueError("game_slug cannot be empty")
        
        if not completed_at:
            raise ValueError("completed_at must be provided")
        
        # Defaults
        opponent_name = kwargs.get("opponent_name", "").strip() or "Unknown"
        score_summary = kwargs.get("score_summary", "").strip()
        
        return cls(
            match_id=match_id,
            tournament_id=tournament_id,
            tournament_name=kwargs.get("tournament_name", "").strip(),
            game_slug=game_slug,
            is_winner=kwargs.get("is_winner", False),
            is_draw=kwargs.get("is_draw", False),
            score_summary=score_summary,
            opponent_id=kwargs.get("opponent_id"),
            opponent_name=opponent_name,
            had_dispute=kwargs.get("had_dispute", False),
            is_forfeit=kwargs.get("is_forfeit", False),
            completed_at=completed_at,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "match_id": self.match_id,
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "game_slug": self.game_slug,
            "is_winner": self.is_winner,
            "is_draw": self.is_draw,
            "score_summary": self.score_summary,
            "opponent_id": self.opponent_id,
            "opponent_name": self.opponent_name,
            "had_dispute": self.had_dispute,
            "is_forfeit": self.is_forfeit,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass(frozen=True)
class UserMatchHistoryDTO:
    """
    User match history entry with player-specific stats.
    
    Extends base match history with kills/deaths/assists for FPS games.
    Used for user profile timeline and match history queries.
    """
    
    # Identity
    user_id: int
    username: str
    
    # Match context (from base)
    match_id: int
    tournament_id: int
    tournament_name: str
    game_slug: str
    
    # Result
    is_winner: bool
    is_draw: bool
    score_summary: str
    
    # Opponent
    opponent_user_id: Optional[int]
    opponent_name: str
    
    # Player stats (optional, game-dependent)
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    
    # Flags
    had_dispute: bool = False
    is_forfeit: bool = False
    
    # Timeline
    completed_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, history_entry) -> "UserMatchHistoryDTO":
        """
        Construct DTO from UserMatchHistory model instance.
        
        Args:
            history_entry: UserMatchHistory model instance
            
        Returns:
            UserMatchHistoryDTO with all fields populated
        """
        return cls(
            user_id=history_entry.user_id,
            username=history_entry.user.username if history_entry.user else "Unknown",
            match_id=history_entry.match_id,
            tournament_id=history_entry.tournament_id,
            tournament_name=history_entry.tournament.name if history_entry.tournament else "",
            game_slug=history_entry.game_slug,
            is_winner=history_entry.is_winner,
            is_draw=history_entry.is_draw,
            score_summary=history_entry.score_summary or "",
            opponent_user_id=history_entry.opponent_user_id,
            opponent_name=history_entry.opponent_name or "Unknown",
            kills=history_entry.kills,
            deaths=history_entry.deaths,
            assists=history_entry.assists,
            had_dispute=history_entry.had_dispute,
            is_forfeit=history_entry.is_forfeit,
            completed_at=history_entry.completed_at,
        )
    
    @classmethod
    def validate(cls, **kwargs) -> "UserMatchHistoryDTO":
        """
        Validate and construct DTO with business rules.
        
        Rules:
        - user_id must be positive
        - username must not be empty
        - kills/deaths/assists must be non-negative
        - completed_at must be provided
        """
        user_id = kwargs.get("user_id")
        username = kwargs.get("username", "").strip()
        kills = kwargs.get("kills", 0)
        deaths = kwargs.get("deaths", 0)
        assists = kwargs.get("assists", 0)
        completed_at = kwargs.get("completed_at")
        
        if not user_id or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        
        if not username:
            raise ValueError("username cannot be empty")
        
        if kills < 0 or deaths < 0 or assists < 0:
            raise ValueError("kills, deaths, and assists must be non-negative")
        
        if not completed_at:
            raise ValueError("completed_at must be provided")
        
        # Defaults
        opponent_name = kwargs.get("opponent_name", "").strip() or "Unknown"
        score_summary = kwargs.get("score_summary", "").strip()
        
        return cls(
            user_id=user_id,
            username=username,
            match_id=kwargs.get("match_id", 0),
            tournament_id=kwargs.get("tournament_id", 0),
            tournament_name=kwargs.get("tournament_name", "").strip(),
            game_slug=kwargs.get("game_slug", "").strip(),
            is_winner=kwargs.get("is_winner", False),
            is_draw=kwargs.get("is_draw", False),
            score_summary=score_summary,
            opponent_user_id=kwargs.get("opponent_user_id"),
            opponent_name=opponent_name,
            kills=kills,
            deaths=deaths,
            assists=assists,
            had_dispute=kwargs.get("had_dispute", False),
            is_forfeit=kwargs.get("is_forfeit", False),
            completed_at=completed_at,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "match_id": self.match_id,
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "game_slug": self.game_slug,
            "is_winner": self.is_winner,
            "is_draw": self.is_draw,
            "score_summary": self.score_summary,
            "opponent_user_id": self.opponent_user_id,
            "opponent_name": self.opponent_name,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "had_dispute": self.had_dispute,
            "is_forfeit": self.is_forfeit,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass(frozen=True)
class TeamMatchHistoryDTO:
    """
    Team match history entry with ELO tracking.
    
    Extends base match history with ELO rating changes for competitive tracking.
    Used for team profile timeline and match history queries.
    """
    
    # Identity
    team_id: int
    team_name: str
    
    # Match context
    match_id: int
    tournament_id: int
    tournament_name: str
    game_slug: str
    
    # Result
    is_winner: bool
    is_draw: bool
    score_summary: str
    
    # Opponent
    opponent_team_id: Optional[int]
    opponent_team_name: str
    
    # ELO tracking
    elo_before: Optional[int] = None
    elo_after: Optional[int] = None
    elo_change: int = 0
    
    # Flags
    had_dispute: bool = False
    is_forfeit: bool = False
    
    # Timeline
    completed_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, history_entry) -> "TeamMatchHistoryDTO":
        """
        Construct DTO from TeamMatchHistory model instance.
        
        Args:
            history_entry: TeamMatchHistory model instance
            
        Returns:
            TeamMatchHistoryDTO with all fields populated
        """
        return cls(
            team_id=history_entry.team_id,
            team_name=history_entry.team.name if history_entry.team else "Unknown",
            match_id=history_entry.match_id,
            tournament_id=history_entry.tournament_id,
            tournament_name=history_entry.tournament.name if history_entry.tournament else "",
            game_slug=history_entry.game_slug,
            is_winner=history_entry.is_winner,
            is_draw=history_entry.is_draw,
            score_summary=history_entry.score_summary or "",
            opponent_team_id=history_entry.opponent_team_id,
            opponent_team_name=history_entry.opponent_team_name or "Unknown",
            elo_before=history_entry.elo_before,
            elo_after=history_entry.elo_after,
            elo_change=history_entry.elo_change,
            had_dispute=history_entry.had_dispute,
            is_forfeit=history_entry.is_forfeit,
            completed_at=history_entry.completed_at,
        )
    
    @classmethod
    def validate(cls, **kwargs) -> "TeamMatchHistoryDTO":
        """
        Validate and construct DTO with business rules.
        
        Rules:
        - team_id must be positive
        - team_name must not be empty
        - elo_before/elo_after must be valid ELO values if provided (400-3000)
        - completed_at must be provided
        """
        team_id = kwargs.get("team_id")
        team_name = kwargs.get("team_name", "").strip()
        elo_before = kwargs.get("elo_before")
        elo_after = kwargs.get("elo_after")
        completed_at = kwargs.get("completed_at")
        
        if not team_id or team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        
        if not team_name:
            raise ValueError("team_name cannot be empty")
        
        if elo_before is not None and (elo_before < 400 or elo_before > 3000):
            raise ValueError("elo_before must be between 400 and 3000")
        
        if elo_after is not None and (elo_after < 400 or elo_after > 3000):
            raise ValueError("elo_after must be between 400 and 3000")
        
        if not completed_at:
            raise ValueError("completed_at must be provided")
        
        # Calculate elo_change if both before/after provided
        elo_change = kwargs.get("elo_change", 0)
        if elo_before is not None and elo_after is not None:
            elo_change = elo_after - elo_before
        
        # Defaults
        opponent_team_name = kwargs.get("opponent_team_name", "").strip() or "Unknown"
        score_summary = kwargs.get("score_summary", "").strip()
        
        return cls(
            team_id=team_id,
            team_name=team_name,
            match_id=kwargs.get("match_id", 0),
            tournament_id=kwargs.get("tournament_id", 0),
            tournament_name=kwargs.get("tournament_name", "").strip(),
            game_slug=kwargs.get("game_slug", "").strip(),
            is_winner=kwargs.get("is_winner", False),
            is_draw=kwargs.get("is_draw", False),
            score_summary=score_summary,
            opponent_team_id=kwargs.get("opponent_team_id"),
            opponent_team_name=opponent_team_name,
            elo_before=elo_before,
            elo_after=elo_after,
            elo_change=elo_change,
            had_dispute=kwargs.get("had_dispute", False),
            is_forfeit=kwargs.get("is_forfeit", False),
            completed_at=completed_at,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "match_id": self.match_id,
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "game_slug": self.game_slug,
            "is_winner": self.is_winner,
            "is_draw": self.is_draw,
            "score_summary": self.score_summary,
            "opponent_team_id": self.opponent_team_id,
            "opponent_team_name": self.opponent_team_name,
            "elo_before": self.elo_before,
            "elo_after": self.elo_after,
            "elo_change": self.elo_change,
            "had_dispute": self.had_dispute,
            "is_forfeit": self.is_forfeit,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass(frozen=True)
class MatchHistoryFilterDTO:
    """
    Query filter for match history searches.
    
    Supports filtering by entity (user/team), tournament, game, and date range.
    Includes pagination (limit/offset) for timeline queries.
    """
    
    # Entity filter (user OR team, mutually exclusive)
    user_id: Optional[int] = None
    team_id: Optional[int] = None
    
    # Context filters
    tournament_id: Optional[int] = None
    game_slug: Optional[str] = None
    
    # Date range
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    # Result filter
    only_wins: bool = False
    only_losses: bool = False
    
    # Pagination
    limit: int = 20
    offset: int = 0
    
    @classmethod
    def validate(cls, **kwargs) -> "MatchHistoryFilterDTO":
        """
        Validate and construct filter DTO with business rules.
        
        Rules:
        - Either user_id OR team_id must be provided (not both)
        - limit must be between 1 and 100
        - offset must be non-negative
        - from_date must be before to_date if both provided
        - only_wins and only_losses cannot both be True
        """
        user_id = kwargs.get("user_id")
        team_id = kwargs.get("team_id")
        tournament_id = kwargs.get("tournament_id")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)
        from_date = kwargs.get("from_date")
        to_date = kwargs.get("to_date")
        only_wins = kwargs.get("only_wins", False)
        only_losses = kwargs.get("only_losses", False)
        
        # Mutual exclusivity: user_id XOR team_id (at least one required)
        if not user_id and not team_id:
            raise ValueError("Either user_id or team_id must be provided")
        
        if user_id and team_id:
            raise ValueError("Cannot filter by both user_id and team_id")
        
        # Validate IDs
        if user_id is not None and user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        
        if team_id is not None and team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        
        if tournament_id is not None and tournament_id <= 0:
            raise ValueError("tournament_id must be a positive integer")
        
        # Pagination
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        
        if offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Date range
        if from_date and to_date and from_date > to_date:
            raise ValueError("from_date must be before to_date")
        
        # Result filter
        if only_wins and only_losses:
            raise ValueError("only_wins and only_losses cannot both be True")
        
        # Clean game_slug (handle None values)
        game_slug_raw = kwargs.get("game_slug", "")
        game_slug = game_slug_raw.strip() if game_slug_raw else None
        
        return cls(
            user_id=user_id,
            team_id=team_id,
            tournament_id=tournament_id,
            game_slug=game_slug,
            from_date=from_date,
            to_date=to_date,
            only_wins=only_wins,
            only_losses=only_losses,
            limit=limit,
            offset=offset,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/debugging."""
        return {
            "user_id": self.user_id,
            "team_id": self.team_id,
            "tournament_id": self.tournament_id,
            "game_slug": self.game_slug,
            "from_date": self.from_date.isoformat() if self.from_date else None,
            "to_date": self.to_date.isoformat() if self.to_date else None,
            "only_wins": self.only_wins,
            "only_losses": self.only_losses,
            "limit": self.limit,
            "offset": self.offset,
        }
