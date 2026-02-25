"""
Audit Log Service for Tournament Operations

Phase 7, Epic 7.5: Audit Log System
Provides business logic for comprehensive audit trail with before/after state capture.

Service Layer:
    - AuditLogService: High-level audit log operations
    - @audit_action decorator: Automatic audit logging for service methods
    - Helper functions for common audit scenarios

Architecture:
    - No ORM imports (uses AuditLogAdapter only)
    - Returns DTOs only
    - Orchestrates adapter calls
    - Publishes domain events for audit log creation
"""

import functools
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from apps.tournament_ops.dtos import (
    AuditLogDTO,
    AuditLogFilterDTO,
    AuditLogExportDTO,
)

logger = logging.getLogger(__name__)


class AuditLogService:
    """
    Service for audit log operations.
    
    Phase 7, Epic 7.5: Comprehensive audit trail for organizer console.
    
    Responsibilities:
        - Create audit log entries with context
        - Query audit logs with filters
        - Export audit logs for compliance
        - Provide helper methods for common audit patterns
    
    Architecture:
        - Uses AuditLogAdapter for data access (no direct ORM)
        - Returns DTOs only
        - No business rules (audit is append-only)
        - Event-driven integration
    
    Example:
        >>> service = AuditLogService(audit_log_adapter)
        >>> log = service.log_action(
        ...     user_id=5,
        ...     action="result_finalized",
        ...     tournament_id=10,
        ...     match_id=42,
        ...     before_state={"status": "PENDING"},
        ...     after_state={"status": "FINALIZED"}
        ... )
    """
    
    def __init__(self, audit_log_adapter):
        """
        Initialize audit log service.
        
        Args:
            audit_log_adapter: AuditLogAdapter instance (injected dependency)
        """
        self.audit_log_adapter = audit_log_adapter
    
    def log_action(
        self,
        user_id: Optional[int] = None,
        action: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        tournament_id: Optional[int] = None,
        match_id: Optional[int] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        *,
        user=None,  # Legacy compat: accept user object, extract .id
    ) -> AuditLogDTO:
        # Legacy compat: accept user= kwarg (User or Mock object)
        if user is not None and user_id is None:
            user_id = getattr(user, 'id', None)
        """
        Create audit log entry.
        
        Args:
            user_id: User performing action (None for system actions)
            action: Action type (e.g., 'result_finalized')
            metadata: Additional action metadata
            ip_address: Client IP address
            user_agent: Client user agent string
            tournament_id: Tournament context
            match_id: Match context
            before_state: State before action
            after_state: State after action
            correlation_id: Request correlation ID
            
        Returns:
            AuditLogDTO for created log entry
            
        Example:
            >>> log = service.log_action(
            ...     user_id=5,
            ...     action="match_rescheduled",
            ...     tournament_id=10,
            ...     match_id=42,
            ...     before_state={"scheduled_time": "2025-12-10T10:00:00Z"},
            ...     after_state={"scheduled_time": "2025-12-10T14:00:00Z"},
            ...     metadata={"reason": "Participant request"}
            ... )
        """
        logger.info(
            f"Creating audit log: action={action}, user_id={user_id}, "
            f"tournament_id={tournament_id}, match_id={match_id}"
        )
        
        return self.audit_log_adapter.create_log_entry(
            user_id=user_id,
            action=action,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            tournament_id=tournament_id,
            match_id=match_id,
            before_state=before_state,
            after_state=after_state,
            correlation_id=correlation_id,
            user=user,  # Pass user object through for adapter compat
        )
    
    def get_log_by_id(self, log_id: int) -> Optional[AuditLogDTO]:
        """
        Get audit log entry by ID.
        
        Args:
            log_id: Audit log entry ID
            
        Returns:
            AuditLogDTO if found, None otherwise
        """
        return self.audit_log_adapter.get_log_by_id(log_id)
    
    def list_logs(self, filters: AuditLogFilterDTO) -> List[AuditLogDTO]:
        """
        List audit logs with filtering and pagination.
        
        Args:
            filters: Filter parameters
            
        Returns:
            List of AuditLogDTO instances
            
        Example:
            >>> filters = AuditLogFilterDTO(
            ...     tournament_id=10,
            ...     action_prefix="result_",
            ...     limit=50
            ... )
            >>> logs = service.list_logs(filters)
        """
        # Validate filters
        filters.validate()
        
        return self.audit_log_adapter.list_logs(filters)
    
    def count_logs(self, filters: AuditLogFilterDTO) -> int:
        """
        Count audit logs matching filters.
        
        Args:
            filters: Filter parameters
            
        Returns:
            Total count (for pagination)
        """
        filters.validate()
        return self.audit_log_adapter.count_logs(filters)
    
    def get_user_audit_trail(self, user_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit trail for specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of entries
            
        Returns:
            List of AuditLogDTO instances for user's actions
        """
        return self.audit_log_adapter.get_user_logs(user_id, limit)
    
    def get_tournament_audit_trail(self, tournament_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit trail for specific tournament.
        
        Args:
            tournament_id: Tournament ID
            limit: Maximum number of entries
            
        Returns:
            List of AuditLogDTO instances for tournament
        """
        return self.audit_log_adapter.get_tournament_logs(tournament_id, limit)
    
    def get_match_audit_trail(self, match_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit trail for specific match.
        
        Args:
            match_id: Match ID
            limit: Maximum number of entries
            
        Returns:
            List of AuditLogDTO instances for match
        """
        return self.audit_log_adapter.get_match_logs(match_id, limit)
    
    def get_action_audit_trail(self, action: str, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit trail for specific action type.
        
        Args:
            action: Action type (e.g., 'result_finalized')
            limit: Maximum number of entries
            
        Returns:
            List of AuditLogDTO instances for action
        """
        return self.audit_log_adapter.get_action_logs(action, limit)
    
    def export_logs_to_csv(self, filters: AuditLogFilterDTO) -> List[AuditLogExportDTO]:
        """
        Export audit logs in CSV-friendly format.
        
        Args:
            filters: Filter parameters
            
        Returns:
            List of AuditLogExportDTO instances for CSV generation
            
        Example:
            >>> filters = AuditLogFilterDTO(tournament_id=10)
            >>> export_data = service.export_logs_to_csv(filters)
            >>> # Convert to CSV using csv.DictWriter
            >>> import csv
            >>> with open('audit.csv', 'w') as f:
            ...     writer = csv.DictWriter(f, fieldnames=export_data[0].to_csv_row().keys())
            ...     writer.writeheader()
            ...     for row in export_data:
            ...         writer.writerow(row.to_csv_row())
        """
        filters.validate()
        return self.audit_log_adapter.export_logs(filters)
    
    def get_recent_activity(
        self,
        tournament_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[AuditLogDTO]:
        """
        Get recent activity for dashboard/feed display.
        
        Args:
            tournament_id: Filter by tournament (optional)
            user_id: Filter by user (optional)
            limit: Maximum entries (default 20)
            
        Returns:
            List of recent AuditLogDTO instances
        """
        filters = AuditLogFilterDTO(
            tournament_id=tournament_id,
            user_id=user_id,
            limit=limit,
            order_by='-timestamp'
        )
        return self.list_logs(filters)
    
    def get_state_changes(
        self,
        tournament_id: Optional[int] = None,
        match_id: Optional[int] = None,
        limit: int = 50
    ) -> List[AuditLogDTO]:
        """
        Get audit logs that track state changes (have before/after state).
        
        Args:
            tournament_id: Filter by tournament (optional)
            match_id: Filter by match (optional)
            limit: Maximum entries
            
        Returns:
            List of AuditLogDTO instances with state changes
        """
        filters = AuditLogFilterDTO(
            tournament_id=tournament_id,
            match_id=match_id,
            has_state_change=True,
            limit=limit,
            order_by='-timestamp'
        )
        return self.list_logs(filters)


# -----------------------------------------------------------------------------
# Audit Logging Decorator
# -----------------------------------------------------------------------------

def audit_action(
    action: str,
    capture_state: bool = False,
    tournament_id_arg: Optional[str] = None,
    match_id_arg: Optional[str] = None,
    user_id_arg: Optional[str] = None,
):
    """
    Decorator for automatic audit logging of service methods.
    
    Phase 7, Epic 7.5: Automatic audit trail for service operations.
    
    Args:
        action: Action type to log (e.g., 'result_finalized')
        capture_state: Whether to capture before/after state
        tournament_id_arg: Name of kwarg containing tournament_id
        match_id_arg: Name of kwarg containing match_id
        user_id_arg: Name of kwarg containing user_id (default: 'user_id')
    
    Returns:
        Decorator function
        
    Example:
        >>> class MyService:
        ...     @audit_action(
        ...         action='result_finalized',
        ...         capture_state=True,
        ...         tournament_id_arg='tournament_id',
        ...         match_id_arg='match_id'
        ...     )
        ...     def finalize_result(self, tournament_id, match_id, user_id):
        ...         # Service logic here
        ...         pass
    
    Note:
        This decorator assumes the service has an `audit_log_service` attribute.
        The decorated method should return a DTO or result object.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Extract context from kwargs
            tournament_id = kwargs.get(tournament_id_arg) if tournament_id_arg else None
            match_id = kwargs.get(match_id_arg) if match_id_arg else None
            user_id = kwargs.get(user_id_arg or 'user_id')
            
            # Capture state before operation if requested
            before_state = None
            if capture_state:
                # This is a simplified version; real implementation would
                # need to capture actual state from database
                before_state = {"captured_at": datetime.now().isoformat()}
            
            # Execute the decorated function
            result = func(self, *args, **kwargs)
            
            # Capture state after operation if requested
            after_state = None
            if capture_state:
                after_state = {"captured_at": datetime.now().isoformat()}
            
            # Log the action (if service has audit_log_service)
            if hasattr(self, 'audit_log_service'):
                try:
                    self.audit_log_service.log_action(
                        user_id=user_id,
                        action=action,
                        tournament_id=tournament_id,
                        match_id=match_id,
                        before_state=before_state,
                        after_state=after_state,
                        metadata={'function': func.__name__}
                    )
                except Exception as e:
                    # Log error but don't fail the operation
                    logger.error(f"Failed to create audit log: {e}", exc_info=True)
            
            return result
        
        return wrapper
    return decorator


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def log_result_finalized(
    audit_service: AuditLogService,
    user_id: int,
    tournament_id: int,
    match_id: int,
    submission_id: int,
    before_status: str,
    after_status: str
) -> AuditLogDTO:
    """
    Helper: Log result finalization.
    
    Args:
        audit_service: AuditLogService instance
        user_id: User who finalized result
        tournament_id: Tournament context
        match_id: Match context
        submission_id: Result submission ID
        before_status: Status before finalization
        after_status: Status after finalization
        
    Returns:
        AuditLogDTO for created log entry
    """
    return audit_service.log_action(
        user_id=user_id,
        action='result_finalized',
        tournament_id=tournament_id,
        match_id=match_id,
        before_state={'status': before_status},
        after_state={'status': after_status},
        metadata={'submission_id': submission_id}
    )


def log_match_rescheduled(
    audit_service: AuditLogService,
    user_id: int,
    tournament_id: int,
    match_id: int,
    old_time: Optional[datetime],
    new_time: datetime,
    reason: Optional[str] = None
) -> AuditLogDTO:
    """
    Helper: Log match rescheduling.
    
    Args:
        audit_service: AuditLogService instance
        user_id: User who rescheduled match
        tournament_id: Tournament context
        match_id: Match ID
        old_time: Previous scheduled time (if any)
        new_time: New scheduled time
        reason: Reason for rescheduling
        
    Returns:
        AuditLogDTO for created log entry
    """
    before_state = {'scheduled_time': old_time.isoformat()} if old_time else None
    after_state = {'scheduled_time': new_time.isoformat()}
    
    metadata = {}
    if reason:
        metadata['reason'] = reason
    
    return audit_service.log_action(
        user_id=user_id,
        action='match_rescheduled',
        tournament_id=tournament_id,
        match_id=match_id,
        before_state=before_state,
        after_state=after_state,
        metadata=metadata
    )


def log_staff_assigned(
    audit_service: AuditLogService,
    user_id: int,
    tournament_id: int,
    staff_user_id: int,
    role: str
) -> AuditLogDTO:
    """
    Helper: Log staff assignment to tournament.
    
    Args:
        audit_service: AuditLogService instance
        user_id: User who made the assignment
        tournament_id: Tournament context
        staff_user_id: Staff user being assigned
        role: Staff role (e.g., 'ADMIN', 'REFEREE')
        
    Returns:
        AuditLogDTO for created log entry
    """
    return audit_service.log_action(
        user_id=user_id,
        action='staff_assigned',
        tournament_id=tournament_id,
        metadata={
            'staff_user_id': staff_user_id,
            'role': role
        }
    )


def log_match_operation(
    audit_service: AuditLogService,
    user_id: int,
    tournament_id: int,
    match_id: int,
    operation: str,
    before_status: Optional[str] = None,
    after_status: Optional[str] = None,
    reason: Optional[str] = None
) -> AuditLogDTO:
    """
    Helper: Log match operation (live, pause, resume, force-complete).
    
    Args:
        audit_service: AuditLogService instance
        user_id: Operator user ID
        tournament_id: Tournament context
        match_id: Match ID
        operation: Operation type (LIVE, PAUSED, RESUMED, FORCE_COMPLETED)
        before_status: Match status before operation
        after_status: Match status after operation
        reason: Reason for operation
        
    Returns:
        AuditLogDTO for created log entry
    """
    before_state = {'status': before_status} if before_status else None
    after_state = {'status': after_status} if after_status else None
    
    metadata = {'operation': operation}
    if reason:
        metadata['reason'] = reason
    
    return audit_service.log_action(
        user_id=user_id,
        action=f'match_operation_{operation.lower()}',
        tournament_id=tournament_id,
        match_id=match_id,
        before_state=before_state,
        after_state=after_state,
        metadata=metadata
    )


# Export service and helpers
__all__ = [
    'AuditLogService',
    'audit_action',
    'log_result_finalized',
    'log_match_rescheduled',
    'log_staff_assigned',
    'log_match_operation',
]
