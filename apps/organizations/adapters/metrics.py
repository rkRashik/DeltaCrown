"""
Observability metrics for Team vNext adapter routing.

This module provides lightweight metrics collection for adapter routing decisions
and performance. Uses structured logging (no database dependencies).

Design Principles:
- Lightweight: Structured logging only (no heavy dependencies)
- Zero-blocking: Never throws exceptions (defensive try/except)
- Thread-safe: Uses Python logging (thread-safe by design)
- Production-ready: Includes duration, error codes, team_id context

Metrics Collected:
- routing_decision: Which path was chosen (legacy vs vNext) and why
- adapter_error: When adapter fails and falls back to legacy
- adapter_duration: How long adapter operations take

Future Enhancement:
- Can be extended to Prometheus counters if metrics infra added
- Can be extended to StatsD if needed
- Currently logging-based for maximum compatibility

Example Usage:
    from apps.organizations.adapters.metrics import (
        record_routing_decision,
        record_adapter_error,
    )
    
    # Record routing decision
    start_time = time.time()
    path = "vnext" if should_use_vnext_routing(team_id) else "legacy"
    duration_ms = (time.time() - start_time) * 1000
    record_routing_decision(
        team_id=123,
        path=path,
        reason="auto_allowlisted",
        duration_ms=duration_ms,
    )
    
    # Record adapter error
    try:
        result = adapter.get_team_url(team_id)
    except Exception as e:
        record_adapter_error(
            team_id=team_id,
            error_code="TEAM_NOT_FOUND",
            path="vnext",
            duration_ms=duration_ms,
        )
        raise

Performance:
- <1ms typical (logging is async in production)
- Non-blocking (never raises exceptions)

Thread Safety:
- Python logging module is thread-safe
- No mutable shared state
"""

import logging
import time
from typing import Literal

# Get logger for adapter metrics
logger = logging.getLogger("apps.organizations.adapters")

# Type alias for routing path
RoutingPath = Literal["legacy", "vnext"]


def record_routing_decision(
    team_id: int,
    path: RoutingPath,
    reason: str,
    duration_ms: float,
) -> None:
    """
    Record a routing decision (which path was chosen and why).
    
    This metric tracks:
    - Which teams are using vNext vs legacy
    - Why routing decisions were made
    - Performance of routing decision logic
    
    Args:
        team_id: Team ID that was routed
        path: Which path was chosen ("legacy" or "vnext")
        reason: Human-readable reason code (from flags.get_routing_reason)
        duration_ms: How long the routing decision took (milliseconds)
    
    Performance:
        - <1ms typical (async logging)
        - Never blocks
    
    Thread Safety:
        - Uses thread-safe logging module
    
    Example:
        >>> record_routing_decision(
        ...     team_id=123,
        ...     path="vnext",
        ...     reason="auto_allowlisted",
        ...     duration_ms=0.5,
        ... )
    """
    try:
        logger.info(
            "adapter.routing_decision",
            extra={
                "event_type": "routing_decision",
                "team_id": team_id,
                "path": path,
                "reason": reason,
                "duration_ms": round(duration_ms, 2),
            },
        )
    except Exception:
        # Defensive: Never let metrics break production code
        pass


def record_adapter_error(
    team_id: int,
    error_code: str,
    path: RoutingPath,
    duration_ms: float,
    exception_type: str | None = None,
) -> None:
    """
    Record an adapter error (when vNext path fails and falls back to legacy).
    
    This metric tracks:
    - How often vNext path fails
    - What error codes are most common
    - Performance impact of errors
    
    Args:
        team_id: Team ID that caused the error
        error_code: Stable error code (e.g., "TEAM_NOT_FOUND")
        path: Which path failed ("legacy" or "vnext")
        duration_ms: How long before error occurred (milliseconds)
        exception_type: Optional exception class name for debugging
    
    Performance:
        - <1ms typical (async logging)
        - Never blocks
    
    Thread Safety:
        - Uses thread-safe logging module
    
    Example:
        >>> record_adapter_error(
        ...     team_id=123,
        ...     error_code="TEAM_NOT_FOUND",
        ...     path="vnext",
        ...     duration_ms=5.3,
        ...     exception_type="NotFoundError",
        ... )
    """
    try:
        extra = {
            "event_type": "adapter_error",
            "team_id": team_id,
            "error_code": error_code,
            "path": path,
            "duration_ms": round(duration_ms, 2),
        }
        
        if exception_type:
            extra["exception_type"] = exception_type
        
        logger.warning(
            "adapter.error",
            extra=extra,
        )
    except Exception:
        # Defensive: Never let metrics break production code
        pass


def record_adapter_duration(
    operation: str,
    team_id: int,
    path: RoutingPath,
    duration_ms: float,
    success: bool = True,
) -> None:
    """
    Record adapter operation duration (performance monitoring).
    
    This metric tracks:
    - How fast different adapter operations are
    - Performance differences between legacy and vNext paths
    - Which operations are slowest
    
    Args:
        operation: Operation name (e.g., "get_team_url", "get_team_identity")
        team_id: Team ID for the operation
        path: Which path was used ("legacy" or "vnext")
        duration_ms: Total operation duration (milliseconds)
        success: Whether operation succeeded (True) or failed (False)
    
    Performance:
        - <1ms typical (async logging)
        - Never blocks
    
    Thread Safety:
        - Uses thread-safe logging module
    
    Example:
        >>> record_adapter_duration(
        ...     operation="get_team_url",
        ...     team_id=123,
        ...     path="vnext",
        ...     duration_ms=8.7,
        ...     success=True,
        ... )
    """
    try:
        logger.info(
            f"adapter.duration.{operation}",
            extra={
                "event_type": "adapter_duration",
                "operation": operation,
                "team_id": team_id,
                "path": path,
                "duration_ms": round(duration_ms, 2),
                "success": success,
            },
        )
    except Exception:
        # Defensive: Never let metrics break production code
        pass


class MetricsContext:
    """
    Context manager for automatic duration tracking.
    
    This class provides a convenient way to measure and record operation
    duration automatically using a with statement.
    
    Example:
        with MetricsContext("get_team_url", team_id=123, path="vnext") as ctx:
            result = adapter.get_team_url(team_id)
        # Duration automatically recorded on context exit
    """
    
    def __init__(
        self,
        operation: str,
        team_id: int,
        path: RoutingPath,
    ):
        """
        Initialize metrics context.
        
        Args:
            operation: Operation name
            team_id: Team ID for the operation
            path: Which path is being used
        """
        self.operation = operation
        self.team_id = team_id
        self.path = path
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Record duration on exit.
        
        Args:
            exc_type: Exception type (if error occurred)
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            
            record_adapter_duration(
                operation=self.operation,
                team_id=self.team_id,
                path=self.path,
                duration_ms=duration_ms,
                success=self.success,
            )
        
        # Don't suppress exceptions
        return False
