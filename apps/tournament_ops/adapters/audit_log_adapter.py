"""
Audit Log Adapter for Tournament Operations

Phase 7, Epic 7.5: Audit Log System
Provides data access layer for audit log queries with method-level ORM imports.

Architecture:
    - Protocol defines interface for audit log operations
    - Adapter implements protocol with method-level ORM imports only
    - Returns DTOs only, never raw ORM models
    - No business logic (that belongs in AuditLogService)
"""

from typing import Protocol, List, Optional, Dict, Any
from datetime import datetime
from apps.tournament_ops.dtos import (
    AuditLogDTO,
    AuditLogFilterDTO,
    AuditLogExportDTO,
)


class AuditLogAdapterProtocol(Protocol):
    """
    Protocol for audit log adapter.
    
    Defines interface for audit log data access operations.
    Implementations must use method-level ORM imports only.
    """
    
    def create_log_entry(
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
        user=None,
    ) -> AuditLogDTO:
        """Create audit log entry."""
        ...
    
    def get_log_by_id(self, log_id: int) -> Optional[AuditLogDTO]:
        """Get audit log entry by ID."""
        ...
    
    def list_logs(self, filters: AuditLogFilterDTO) -> List[AuditLogDTO]:
        """List audit logs with filtering and pagination."""
        ...
    
    def count_logs(self, filters: AuditLogFilterDTO) -> int:
        """Count audit logs matching filters (for pagination)."""
        ...
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """Get audit logs for specific user."""
        ...
    
    def get_tournament_logs(self, tournament_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """Get audit logs for specific tournament."""
        ...
    
    def get_match_logs(self, match_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """Get audit logs for specific match."""
        ...
    
    def get_action_logs(self, action: str, limit: int = 100) -> List[AuditLogDTO]:
        """Get audit logs for specific action type."""
        ...
    
    def export_logs(self, filters: AuditLogFilterDTO) -> List[AuditLogExportDTO]:
        """Export audit logs in CSV-friendly format."""
        ...


class AuditLogAdapter:
    """
    Audit log adapter implementation.
    
    Phase 7, Epic 7.5: Data access layer for audit log system.
    
    Architecture Notes:
        - Uses method-level ORM imports only (no module-level imports)
        - Returns DTOs only, never raw ORM models
        - No business logic (pure data access)
        - All methods are synchronous (no async)
    
    Example:
        >>> adapter = AuditLogAdapter()
        >>> log = adapter.create_log_entry(
        ...     user_id=5,
        ...     action="result_finalized",
        ...     tournament_id=10,
        ...     match_id=42
        ... )
        >>> logs = adapter.list_logs(AuditLogFilterDTO(tournament_id=10))
    """
    
    def create_log_entry(
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
            user_id: ID of user performing action (None for system actions)
            action: Action type (e.g., 'result_finalized')
            metadata: Additional action metadata
            ip_address: Client IP address
            user_agent: Client user agent string
            tournament_id: Tournament context (if applicable)
            match_id: Match context (if applicable)
            before_state: State before action
            after_state: State after action
            correlation_id: Request correlation ID
            
        Returns:
            AuditLogDTO for created log entry
            
        Raises:
            ValueError: If required fields missing or invalid
        """
        # Method-level ORM import
        from apps.tournaments.models import AuditLog
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Validate user_id if provided
        user = None
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValueError(f"User with id {user_id} does not exist")
        
        # Create log entry
        log_entry = AuditLog.objects.create(
            user=user,
            action=action,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            tournament_id=tournament_id,
            match_id=match_id,
            before_state=before_state,
            after_state=after_state,
            correlation_id=correlation_id,
        )
        
        # Convert to DTO
        return AuditLogDTO.from_model(log_entry)
    
    def get_log_by_id(self, log_id: int) -> Optional[AuditLogDTO]:
        """
        Get audit log entry by ID.
        
        Args:
            log_id: Audit log entry ID
            
        Returns:
            AuditLogDTO if found, None otherwise
        """
        # Method-level ORM import
        from apps.tournaments.models import AuditLog
        
        try:
            log_entry = AuditLog.objects.select_related('user').get(id=log_id)
            return AuditLogDTO.from_model(log_entry)
        except AuditLog.DoesNotExist:
            return None
    
    def list_logs(self, filters: AuditLogFilterDTO) -> List[AuditLogDTO]:
        """
        List audit logs with filtering and pagination.
        
        Args:
            filters: Filter parameters (user_id, action, tournament_id, etc.)
            
        Returns:
            List of AuditLogDTO instances matching filters
            
        Example:
            >>> filters = AuditLogFilterDTO(
            ...     tournament_id=10,
            ...     action_prefix="result_",
            ...     limit=50
            ... )
            >>> logs = adapter.list_logs(filters)
        """
        # Method-level ORM import
        from apps.tournaments.models import AuditLog
        
        # Start with all logs
        queryset = AuditLog.objects.select_related('user').all()
        
        # Apply filters
        if filters.user_id is not None:
            queryset = queryset.filter(user_id=filters.user_id)
        
        if filters.action is not None:
            queryset = queryset.filter(action=filters.action)
        
        if filters.action_prefix is not None:
            queryset = queryset.filter(action__startswith=filters.action_prefix)
        
        if filters.tournament_id is not None:
            queryset = queryset.filter(tournament_id=filters.tournament_id)
        
        if filters.match_id is not None:
            queryset = queryset.filter(match_id=filters.match_id)
        
        if filters.start_date is not None:
            queryset = queryset.filter(timestamp__gte=filters.start_date)
        
        if filters.end_date is not None:
            queryset = queryset.filter(timestamp__lte=filters.end_date)
        
        if filters.has_state_change is not None:
            if filters.has_state_change:
                # Only logs with both before and after state
                queryset = queryset.exclude(before_state__isnull=True).exclude(after_state__isnull=True)
            else:
                # Only logs without state tracking
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(before_state__isnull=True) | Q(after_state__isnull=True)
                )
        
        if filters.correlation_id is not None:
            queryset = queryset.filter(correlation_id=filters.correlation_id)
        
        # Apply ordering
        queryset = queryset.order_by(filters.order_by)
        
        # Apply pagination
        queryset = queryset[filters.offset:filters.offset + filters.limit]
        
        # Convert to DTOs
        return [AuditLogDTO.from_model(log) for log in queryset]
    
    def count_logs(self, filters: AuditLogFilterDTO) -> int:
        """
        Count audit logs matching filters.
        
        Args:
            filters: Filter parameters
            
        Returns:
            Total count of logs matching filters (for pagination)
        """
        # Method-level ORM import
        from apps.tournaments.models import AuditLog
        
        # Start with all logs
        queryset = AuditLog.objects.all()
        
        # Apply same filters as list_logs (without pagination)
        if filters.user_id is not None:
            queryset = queryset.filter(user_id=filters.user_id)
        
        if filters.action is not None:
            queryset = queryset.filter(action=filters.action)
        
        if filters.action_prefix is not None:
            queryset = queryset.filter(action__startswith=filters.action_prefix)
        
        if filters.tournament_id is not None:
            queryset = queryset.filter(tournament_id=filters.tournament_id)
        
        if filters.match_id is not None:
            queryset = queryset.filter(match_id=filters.match_id)
        
        if filters.start_date is not None:
            queryset = queryset.filter(timestamp__gte=filters.start_date)
        
        if filters.end_date is not None:
            queryset = queryset.filter(timestamp__lte=filters.end_date)
        
        if filters.has_state_change is not None:
            if filters.has_state_change:
                queryset = queryset.exclude(before_state__isnull=True).exclude(after_state__isnull=True)
            else:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(before_state__isnull=True) | Q(after_state__isnull=True)
                )
        
        if filters.correlation_id is not None:
            queryset = queryset.filter(correlation_id=filters.correlation_id)
        
        return queryset.count()
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit logs for specific user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List of AuditLogDTO instances for user's actions
        """
        filters = AuditLogFilterDTO(user_id=user_id, limit=limit)
        return self.list_logs(filters)
    
    def get_tournament_logs(self, tournament_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit logs for specific tournament.
        
        Args:
            tournament_id: Tournament ID to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List of AuditLogDTO instances for tournament
        """
        filters = AuditLogFilterDTO(tournament_id=tournament_id, limit=limit)
        return self.list_logs(filters)
    
    def get_match_logs(self, match_id: int, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit logs for specific match.
        
        Args:
            match_id: Match ID to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List of AuditLogDTO instances for match
        """
        filters = AuditLogFilterDTO(match_id=match_id, limit=limit)
        return self.list_logs(filters)
    
    def get_action_logs(self, action: str, limit: int = 100) -> List[AuditLogDTO]:
        """
        Get audit logs for specific action type.
        
        Args:
            action: Action type to filter by (e.g., 'result_finalized')
            limit: Maximum number of logs to return
            
        Returns:
            List of AuditLogDTO instances for action type
        """
        filters = AuditLogFilterDTO(action=action, limit=limit)
        return self.list_logs(filters)
    
    def export_logs(self, filters: AuditLogFilterDTO) -> List[AuditLogExportDTO]:
        """
        Export audit logs in CSV-friendly format.
        
        Args:
            filters: Filter parameters (same as list_logs)
            
        Returns:
            List of AuditLogExportDTO instances for CSV generation
            
        Note:
            This method returns export-optimized DTOs with flattened
            structure suitable for CSV/Excel generation.
        """
        # Get regular DTOs first
        logs = self.list_logs(filters)
        
        # Convert to export format
        return [AuditLogExportDTO.from_audit_log_dto(log) for log in logs]


# Export adapter
__all__ = ['AuditLogAdapter', 'AuditLogAdapterProtocol']
