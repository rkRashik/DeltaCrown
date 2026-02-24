"""
Audit Log DTOs for Tournament Operations

Phase 7, Epic 7.5: Audit Log System
Provides data transfer objects for audit trail queries and filtering.

DTOs:
    - AuditLogDTO: Single audit log entry
    - AuditLogFilterDTO: Filter parameters for audit log queries
    - AuditLogExportDTO: Export format for CSV/Excel
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from .base import DTOBase


@dataclass
class AuditLogDTO(DTOBase):
    """
    Data transfer object for audit log entries.
    
    Phase 7, Epic 7.5: Comprehensive audit trail with before/after state.
    
    Fields:
        log_id: Unique identifier for the audit log entry
        user_id: ID of user who performed action (None for system actions)
        username: Username of actor (for display)
        action: Action type (e.g., 'result_finalized', 'match_rescheduled')
        timestamp: When the action occurred
        metadata: Action-specific data (arbitrary JSON)
        ip_address: IP address of user (if captured)
        user_agent: User agent string (if captured)
        tournament_id: Tournament context (if applicable)
        match_id: Match context (if applicable)
        before_state: State before action (for change tracking)
        after_state: State after action (for change tracking)
        correlation_id: Request correlation ID for distributed tracing
    
    Example:
        >>> log = AuditLogDTO(
        ...     log_id=123,
        ...     user_id=5,
        ...     username="admin",
        ...     action="result_finalized",
        ...     timestamp=datetime.now(),
        ...     tournament_id=10,
        ...     match_id=42,
        ...     before_state={"status": "PENDING"},
        ...     after_state={"status": "FINALIZED"},
        ...     metadata={"submission_id": 99}
        ... )
    """
    
    log_id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tournament_id: Optional[int] = None
    match_id: Optional[int] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    
    @classmethod
    def from_model(cls, audit_log) -> 'AuditLogDTO':
        """
        Create DTO from AuditLog ORM model.
        
        Args:
            audit_log: AuditLog model instance
            
        Returns:
            AuditLogDTO instance
            
        Note:
            This method is called from adapter layer only.
            Services and API layer never touch ORM models.
        """
        return cls(
            log_id=audit_log.id,
            user_id=audit_log.user_id,
            username=audit_log.user.username if audit_log.user else None,
            action=audit_log.action,
            timestamp=audit_log.timestamp,
            metadata=audit_log.metadata,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            tournament_id=audit_log.tournament_id,
            match_id=audit_log.match_id,
            before_state=audit_log.before_state,
            after_state=audit_log.after_state,
            correlation_id=audit_log.correlation_id
        )
    
    def validate(self):
        """
        Validate DTO fields.
        
        Raises:
            ValueError: If validation fails
        """
        if not self.action:
            raise ValueError("Action is required")
        
        if self.log_id is not None and self.log_id <= 0:
            raise ValueError("log_id must be positive")
        
        if self.user_id is not None and self.user_id <= 0:
            raise ValueError("user_id must be positive")
        
        if self.tournament_id is not None and self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive")
        
        if self.match_id is not None and self.match_id <= 0:
            raise ValueError("match_id must be positive")
    
    def has_state_change(self) -> bool:
        """Check if this log entry tracks a state change."""
        return self.before_state is not None and self.after_state is not None
    
    def get_changed_fields(self) -> List[str]:
        """
        Get list of fields that changed between before_state and after_state.
        
        Returns:
            List of field names that changed
        """
        if not self.has_state_change():
            return []
        
        changed = []
        before = self.before_state or {}
        after = self.after_state or {}
        
        # Find fields in after that differ from before
        for key, after_value in after.items():
            before_value = before.get(key)
            if before_value != after_value:
                changed.append(key)
        
        # Find fields removed (in before but not in after)
        for key in before.keys():
            if key not in after:
                changed.append(key)
        
        return list(set(changed))


@dataclass
class AuditLogFilterDTO(DTOBase):
    """
    Filter parameters for audit log queries.
    
    Phase 7, Epic 7.5: Organizer console audit log search/filter.
    
    Fields:
        user_id: Filter by user who performed action
        action: Filter by action type
        action_prefix: Filter by action prefix (e.g., 'result_' for all result actions)
        tournament_id: Filter by tournament context
        match_id: Filter by match context
        start_date: Filter by timestamp >= start_date
        end_date: Filter by timestamp <= end_date
        has_state_change: Filter for entries with before/after state
        correlation_id: Filter by correlation ID
        limit: Maximum number of results to return
        offset: Offset for pagination
        order_by: Field to order by (default: '-timestamp')
    
    Example:
        >>> filters = AuditLogFilterDTO(
        ...     tournament_id=10,
        ...     action_prefix="result_",
        ...     start_date=datetime(2025, 12, 1),
        ...     limit=50
        ... )
    """
    
    user_id: Optional[int] = None
    action: Optional[str] = None
    action_prefix: Optional[str] = None
    tournament_id: Optional[int] = None
    match_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    has_state_change: Optional[bool] = None
    correlation_id: Optional[str] = None
    limit: int = 100
    offset: int = 0
    order_by: str = '-timestamp'
    
    def validate(self):
        """
        Validate filter parameters.
        
        Raises:
            ValueError: If validation fails
        """
        if self.limit < 0:
            raise ValueError("limit must be non-negative")
        
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        
        if self.limit > 1000:
            raise ValueError("limit cannot exceed 1000")
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        
        valid_order_fields = ['timestamp', '-timestamp', 'action', '-action', 'user_id', '-user_id']
        if self.order_by not in valid_order_fields:
            raise ValueError(f"order_by must be one of {valid_order_fields}")


@dataclass
class AuditLogExportDTO(DTOBase):
    """
    Export format for audit log CSV/Excel generation.
    
    Phase 7, Epic 7.5: CSV export for compliance reporting.
    
    Fields:
        Same as AuditLogDTO but with flattened structure for CSV export.
        State changes are represented as separate columns.
    
    Example:
        >>> export = AuditLogExportDTO.from_audit_log_dto(audit_log_dto)
        >>> csv_row = export.to_csv_row()
    """
    
    log_id: int
    username: Optional[str]
    action: str
    timestamp: str  # ISO format string
    tournament_id: Optional[int]
    match_id: Optional[int]
    ip_address: Optional[str]
    metadata_json: str  # JSON string
    before_state_json: Optional[str]  # JSON string
    after_state_json: Optional[str]  # JSON string
    changed_fields: Optional[str]  # Comma-separated field names
    
    @classmethod
    def from_audit_log_dto(cls, dto: AuditLogDTO) -> 'AuditLogExportDTO':
        """
        Convert AuditLogDTO to export format.
        
        Args:
            dto: AuditLogDTO instance
            
        Returns:
            AuditLogExportDTO instance suitable for CSV export
        """
        import json
        
        metadata_json = json.dumps(dto.metadata) if dto.metadata else "{}"
        before_state_json = json.dumps(dto.before_state) if dto.before_state else None
        after_state_json = json.dumps(dto.after_state) if dto.after_state else None
        changed_fields = ", ".join(dto.get_changed_fields()) if dto.has_state_change() else None
        
        return cls(
            log_id=dto.log_id,
            username=dto.username or "SYSTEM",
            action=dto.action,
            timestamp=dto.timestamp.isoformat(),
            tournament_id=dto.tournament_id,
            match_id=dto.match_id,
            ip_address=dto.ip_address,
            metadata_json=metadata_json,
            before_state_json=before_state_json,
            after_state_json=after_state_json,
            changed_fields=changed_fields
        )
    
    def to_csv_row(self) -> Dict[str, Any]:
        """
        Convert to CSV row dictionary.
        
        Returns:
            Dictionary with CSV column names and values
        """
        return {
            'Log ID': self.log_id,
            'User': self.username,
            'Action': self.action,
            'Timestamp': self.timestamp,
            'Tournament ID': self.tournament_id or '',
            'Match ID': self.match_id or '',
            'IP Address': self.ip_address or '',
            'Metadata': self.metadata_json,
            'Before State': self.before_state_json or '',
            'After State': self.after_state_json or '',
            'Changed Fields': self.changed_fields or ''
        }
    
    def validate(self):
        """Validate export DTO fields."""
        if not self.action:
            raise ValueError("Action is required")
        
        if self.log_id <= 0:
            raise ValueError("log_id must be positive")


# Export all DTOs
__all__ = ['AuditLogDTO', 'AuditLogFilterDTO', 'AuditLogExportDTO']
