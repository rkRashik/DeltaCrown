"""
Match Operations DTOs - Phase 7, Epic 7.4

Data Transfer Objects for Match Operations Command Center (MOCC).

Architecture:
- Part of tournament_ops layer (no ORM imports)
- Used for cross-domain communication
- Validation methods for business rules

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import DTOBase


@dataclass
class MatchOperationLogDTO(DTOBase):
    """
    DTO for match operation audit log entry.
    
    Records a single operator action performed on a match.
    
    Reference: Phase 7, Epic 7.4 - MOCC Audit Trail
    """
    
    log_id: int
    match_id: int
    operator_user_id: int
    operator_username: str
    operation_type: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.log_id <= 0:
            raise ValueError("log_id must be positive")
        
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if self.operator_user_id <= 0:
            raise ValueError("operator_user_id must be positive")
        
        if not self.operation_type:
            raise ValueError("operation_type is required")
        
        valid_operations = [
            'LIVE', 'PAUSED', 'RESUMED', 'FORCE_COMPLETED',
            'NOTE_ADDED', 'OVERRIDE_RESULT', 'OVERRIDE_REFEREE'
        ]
        if self.operation_type not in valid_operations:
            raise ValueError(f"Invalid operation_type: {self.operation_type}")
        
        return True
    
    @classmethod
    def from_model(cls, model):
        """
        Create DTO from Django model instance.
        
        Args:
            model: MatchOperationLog model instance
            
        Returns:
            MatchOperationLogDTO
        """
        # Get operator username (user_id stored as integer)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            operator = User.objects.get(id=model.operator_user_id)
            operator_username = operator.username
        except User.DoesNotExist:
            operator_username = f"User#{model.operator_user_id}"
        
        return cls(
            log_id=model.id,
            match_id=model.match_id,
            operator_user_id=model.operator_user_id,
            operator_username=operator_username,
            operation_type=model.operation_type,
            payload=model.payload,
            created_at=model.created_at
        )


@dataclass
class MatchModeratorNoteDTO(DTOBase):
    """
    DTO for moderator note on a match.
    
    Represents a communication note added by staff/referee.
    
    Reference: Phase 7, Epic 7.4 - MOCC Communication
    """
    
    note_id: int
    match_id: int
    author_user_id: int
    author_username: str
    content: str
    created_at: datetime
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.note_id <= 0:
            raise ValueError("note_id must be positive")
        
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if self.author_user_id <= 0:
            raise ValueError("author_user_id must be positive")
        
        if not self.content or not self.content.strip():
            raise ValueError("content cannot be empty")
        
        return True
    
    @classmethod
    def from_model(cls, model):
        """
        Create DTO from Django model instance.
        
        Args:
            model: MatchModeratorNote model instance
            
        Returns:
            MatchModeratorNoteDTO
        """
        # Get author username
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            author = User.objects.get(id=model.author_user_id)
            author_username = author.username
        except User.DoesNotExist:
            author_username = f"User#{model.author_user_id}"
        
        return cls(
            note_id=model.id,
            match_id=model.match_id,
            author_user_id=model.author_user_id,
            author_username=author_username,
            content=model.content,
            created_at=model.created_at
        )


@dataclass
class MatchOpsActionResultDTO(DTOBase):
    """
    DTO for result of a match operation action.
    
    Used for API responses after performing operations.
    
    Reference: Phase 7, Epic 7.4 - API Response
    """
    
    success: bool
    message: str
    match_id: int
    new_state: Optional[str]
    operation_log: Optional[MatchOperationLogDTO]
    warnings: List[str]
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if not self.message:
            raise ValueError("message is required")
        
        if self.operation_log:
            self.operation_log.validate()
        
        return True


@dataclass
class MatchOpsPermissionDTO(DTOBase):
    """
    DTO for match operations permissions.
    
    Used to gate UI capabilities based on user's staff role.
    
    Reference: Phase 7, Epic 7.4 - Permission Gating
    """
    
    user_id: int
    tournament_id: int
    match_id: Optional[int]
    can_mark_live: bool
    can_pause: bool
    can_resume: bool
    can_force_complete: bool
    can_override_result: bool
    can_add_note: bool
    can_assign_referee: bool
    is_referee: bool
    is_admin: bool
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        
        return True


@dataclass
class MatchTimelineEventDTO(DTOBase):
    """
    DTO for a single event in match timeline.
    
    Aggregates different event types (results, disputes, operations, scheduling)
    into a unified timeline view.
    
    Reference: Phase 7, Epic 7.4 - Match Timeline
    """
    
    event_id: str  # Composite: "{type}_{id}"
    event_type: str  # "OPERATION", "RESULT_SUBMISSION", "DISPUTE", "SCHEDULING", "REFEREE_ASSIGNMENT"
    match_id: int
    timestamp: datetime
    actor_user_id: Optional[int]
    actor_username: Optional[str]
    description: str
    metadata: Optional[Dict[str, Any]]
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.event_id:
            raise ValueError("event_id is required")
        
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        valid_types = [
            'OPERATION', 'RESULT_SUBMISSION', 'DISPUTE',
            'SCHEDULING', 'REFEREE_ASSIGNMENT', 'STATE_CHANGE'
        ]
        if self.event_type not in valid_types:
            raise ValueError(f"Invalid event_type: {self.event_type}")
        
        if not self.description:
            raise ValueError("description is required")
        
        return True


@dataclass
class MatchOpsDashboardItemDTO(DTOBase):
    """
    DTO for a match in the operations dashboard.
    
    Combines match state, referee info, pending actions, and recent activity.
    
    Reference: Phase 7, Epic 7.4 - Operations Dashboard
    """
    
    match_id: int
    tournament_id: int
    tournament_name: str
    stage_id: int
    stage_name: str
    round_number: int
    match_number: int
    status: str
    scheduled_time: Optional[datetime]
    team1_name: Optional[str]
    team2_name: Optional[str]
    primary_referee_username: Optional[str]
    has_pending_result: bool
    has_unresolved_dispute: bool
    last_operation_type: Optional[str]
    last_operation_time: Optional[datetime]
    moderator_notes_count: int
    
    def validate(self) -> bool:
        """
        Validate DTO fields.
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.match_id <= 0:
            raise ValueError("match_id must be positive")
        
        if self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        
        if self.stage_id <= 0:
            raise ValueError("stage_id must be positive")
        
        return True
