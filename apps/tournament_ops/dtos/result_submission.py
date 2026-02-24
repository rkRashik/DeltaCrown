"""
Result Submission DTOs - Phase 6, Epic 6.1

Data Transfer Objects for match result submission workflow.

Architecture:
- Part of tournament_ops layer (no ORM imports)
- Used for cross-domain communication
- Validation methods for business rules
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import DTOBase


@dataclass
class MatchResultSubmissionDTO(DTOBase):
    """
    DTO for match result submissions.
    
    Represents a player/team-submitted match result with proof,
    pending opponent confirmation or auto-confirmation after 24h.
    
    Updated in Phase 7, Epic 7.1: Added tournament_id and stage_id for multi-tournament inbox support.
    """
    
    id: int
    match_id: int
    submitted_by_user_id: int
    submitted_by_team_id: Optional[int] = None
    raw_result_payload: Dict[str, Any] = field(default_factory=dict)
    proof_screenshot_url: Optional[str] = None
    status: str = 'pending'  # pending, confirmed, disputed, auto_confirmed, finalized, rejected
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    auto_confirm_deadline: Optional[datetime] = None
    confirmed_by_user_id: Optional[int] = None
    submitter_notes: str = ''
    organizer_notes: str = ''
    tournament_id: int = 0  # Phase 7, Epic 7.1: For multi-tournament filtering (default 0 for legacy compat)
    stage_id: Optional[int] = None  # Phase 7, Epic 7.1: For stage-specific queries
    auto_confirmed: bool = False  # Whether result was auto-confirmed after 24h deadline
    created_at: Optional[datetime] = None  # Legacy compat alias for submitted_at
    
    @classmethod
    def from_model(cls, model: Any) -> "MatchResultSubmissionDTO":
        """
        Convert MatchResultSubmission model to DTO.
        
        Args:
            model: MatchResultSubmission ORM instance
            
        Returns:
            MatchResultSubmissionDTO
        """
        return cls(
            id=model.id,
            match_id=model.match_id,
            tournament_id=model.tournament_id,
            stage_id=model.stage_id,
            submitted_by_user_id=model.submitted_by_user_id,
            submitted_by_team_id=model.submitted_by_team_id,
            raw_result_payload=model.raw_result_payload,
            proof_screenshot_url=model.proof_screenshot_url or None,
            status=model.status,
            submitted_at=model.submitted_at,
            confirmed_at=model.confirmed_at,
            finalized_at=model.finalized_at,
            auto_confirm_deadline=model.auto_confirm_deadline,
            confirmed_by_user_id=model.confirmed_by_user_id if model.confirmed_by_user else None,
            submitter_notes=model.submitter_notes,
            organizer_notes=model.organizer_notes,
        )
    
    def is_auto_confirm_expired(self) -> bool:
        """
        Check if 24-hour auto-confirm window has passed.
        
        Returns:
            True if current time > auto_confirm_deadline
        """
        from datetime import datetime
        return datetime.now() > self.auto_confirm_deadline
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate DTO fields.
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Status must be one of valid choices
        valid_statuses = ['pending', 'confirmed', 'disputed', 'auto_confirmed', 'finalized', 'rejected']
        if self.status not in valid_statuses:
            errors.append(f"Invalid status: {self.status}")
        
        # Match ID must be positive
        if self.match_id <= 0:
            errors.append("match_id must be positive")
        
        # User ID must be positive
        if self.submitted_by_user_id <= 0:
            errors.append("submitted_by_user_id must be positive")
        
        # Payload must not be empty
        if not self.raw_result_payload:
            errors.append("raw_result_payload cannot be empty")
        
        # If confirmed, must have confirmed_by and confirmed_at
        if self.status == 'confirmed':
            if not self.confirmed_by_user_id:
                errors.append("confirmed status requires confirmed_by_user_id")
            if not self.confirmed_at:
                errors.append("confirmed status requires confirmed_at")
        
        # If finalized, must have finalized_at
        if self.status == 'finalized':
            if not self.finalized_at:
                errors.append("finalized status requires finalized_at")
        
        return (len(errors) == 0, errors)


@dataclass
class ResultVerificationResultDTO(DTOBase):
    """
    Result of schema validation + scoring calculation.
    
    Used in Epic 6.4 (Result Verification Service) but defined
    now for Epic 6.1 schema validation integration.
    """
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    calculated_scores: Optional[Dict[str, Any]]  # {"winner_team_id": 5, "loser_team_id": 6, "winner_score": 13, "loser_score": 7}
    metadata: Dict[str, Any]  # {"game_slug": "valorant", "map": "Haven", "duration_seconds": 2400}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResultVerificationResultDTO":
        """
        Create DTO from dictionary.
        
        Args:
            data: Dictionary with verification result data
            
        Returns:
            ResultVerificationResultDTO
        """
        return cls(
            is_valid=data.get('is_valid', False),
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            calculated_scores=data.get('calculated_scores'),
            metadata=data.get('metadata', {}),
        )
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate DTO fields.
        
        Returns:
            (is_valid, errors)
        """
        validation_errors = []
        
        # If not valid, must have errors
        if not self.is_valid and len(self.errors) == 0:
            validation_errors.append("is_valid=False requires non-empty errors list")
        
        # If calculated_scores present, must have expected keys
        if self.calculated_scores:
            required_keys = ['winner_team_id', 'loser_team_id']
            for key in required_keys:
                if key not in self.calculated_scores:
                    validation_errors.append(f"calculated_scores missing required key: {key}")
        
        # errors and warnings must be lists
        if not isinstance(self.errors, list):
            validation_errors.append("errors must be a list")
        if not isinstance(self.warnings, list):
            validation_errors.append("warnings must be a list")
        
        # metadata must be dict
        if not isinstance(self.metadata, dict):
            validation_errors.append("metadata must be a dictionary")
        
        return (len(validation_errors) == 0, validation_errors)
    
    @staticmethod
    def create_valid(calculated_scores: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> "ResultVerificationResultDTO":
        """
        Factory method for creating a valid result.
        
        Args:
            calculated_scores: Optional score data
            metadata: Optional metadata
            
        Returns:
            ResultVerificationResultDTO with is_valid=True
        """
        return ResultVerificationResultDTO(
            is_valid=True,
            errors=[],
            warnings=[],
            calculated_scores=calculated_scores,
            metadata=metadata or {},
        )
    
    @staticmethod
    def create_invalid(errors: List[str], warnings: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> "ResultVerificationResultDTO":
        """
        Factory method for creating an invalid result.
        
        Args:
            errors: List of error messages
            warnings: Optional list of warnings
            metadata: Optional metadata
            
        Returns:
            ResultVerificationResultDTO with is_valid=False
        """
        return ResultVerificationResultDTO(
            is_valid=False,
            errors=errors,
            warnings=warnings or [],
            calculated_scores=None,
            metadata=metadata or {},
        )
