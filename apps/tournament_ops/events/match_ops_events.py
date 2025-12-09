"""
Match Operations Domain Events - Phase 7, Epic 7.4

Events published when match operations occur.

Architecture:
- Published by MatchOpsService
- Consumed by integrations (notifications, analytics, etc.)
- Event-driven integration pattern

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ..dtos.base import DTOBase


@dataclass
class MatchWentLiveEvent(DTOBase):
    """
    Published when a match is marked as LIVE by operator.
    
    Consumers:
    - NotificationService: Alert participants
    - AnalyticsService: Track live match metrics
    
    Reference: Phase 7, Epic 7.4 - Live Match Control
    """
    
    match_id: int
    tournament_id: int
    operator_user_id: int
    timestamp: datetime
    previous_state: str
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        return True


@dataclass
class MatchPausedEvent(DTOBase):
    """
    Published when a match is paused by operator.
    
    Consumers:
    - NotificationService: Alert participants of pause
    - AnalyticsService: Track pause frequency
    
    Reference: Phase 7, Epic 7.4 - Match Control
    """
    
    match_id: int
    tournament_id: int
    operator_user_id: int
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        return True


@dataclass
class MatchResumedEvent(DTOBase):
    """
    Published when a paused match is resumed by operator.
    
    Consumers:
    - NotificationService: Alert participants of resumption
    - AnalyticsService: Track match interruptions
    
    Reference: Phase 7, Epic 7.4 - Match Control
    """
    
    match_id: int
    tournament_id: int
    operator_user_id: int
    timestamp: datetime
    pause_duration_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        return True


@dataclass
class MatchForceCompletedEvent(DTOBase):
    """
    Published when a match is force-completed by operator.
    
    Consumers:
    - NotificationService: Alert participants
    - BracketService: Update tournament bracket
    - AnalyticsService: Track admin interventions
    
    Reference: Phase 7, Epic 7.4 - Admin Operations
    """
    
    match_id: int
    tournament_id: int
    operator_user_id: int
    timestamp: datetime
    reason: str
    result_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        if not self.reason:
            raise ValueError("reason is required")
        return True


@dataclass
class MatchOperatorNoteAddedEvent(DTOBase):
    """
    Published when an operator adds a moderator note to a match.
    
    Consumers:
    - NotificationService: Alert other staff
    - AuditService: Log communication
    
    Reference: Phase 7, Epic 7.4 - Staff Communication
    """
    
    match_id: int
    tournament_id: int
    author_user_id: int
    timestamp: datetime
    note_id: int
    note_preview: str  # First 100 chars
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.author_user_id <= 0:
            raise ValueError("author_user_id must be positive")
        if self.note_id <= 0:
            raise ValueError("note_id must be positive")
        return True


@dataclass
class MatchResultOverriddenEvent(DTOBase):
    """
    Published when an operator overrides a match result.
    
    Consumers:
    - NotificationService: Alert participants of change
    - BracketService: Update tournament bracket
    - AuditService: Critical audit trail
    - DisputeService: Auto-close related disputes
    
    Reference: Phase 7, Epic 7.4 - Result Override
    """
    
    match_id: int
    tournament_id: int
    operator_user_id: int
    timestamp: datetime
    old_result: Optional[Dict[str, Any]]
    new_result: Dict[str, Any]
    reason: str
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate event fields."""
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        if not self.new_result:
            raise ValueError("new_result is required")
        if not self.reason:
            raise ValueError("reason is required")
        return True
