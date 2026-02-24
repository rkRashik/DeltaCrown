"""
Base adapter interfaces and protocols.

Defines common patterns for all service adapters in the TournamentOps domain.
All cross-domain adapters should inherit from BaseAdapter and implement
relevant protocols.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.1
"""

from abc import ABC
from typing import Protocol, runtime_checkable, Dict, Any, Optional


class BaseAdapter(ABC):
    """
    Abstract base class for all service adapters.
    
    Service adapters provide a clean interface for cross-domain communication
    without direct model imports. All data transfer must use DTOs (to be defined
    in Phase 1, Epic 1.3/1.5).
    
    Adapters must:
    - Not import models from other apps
    - Return DTOs (not ORM models or raw dicts)
    - Be stateless and easily mockable
    - Provide clear error messages
    
    TODO: Replace Dict[str, Any] return types with proper DTOs once
          tournament_ops/dtos/ is implemented (Epic 1.3).
    """
    
    def __init__(self, *, context: Optional[Dict[str, Any]] = None):
        """
        Initialize adapter with optional execution context.
        
        Args:
            context: Optional context dictionary for request metadata,
                    transaction IDs, user context, etc.
        """
        self.context = context or {}


@runtime_checkable
class SupportsHealthCheck(Protocol):
    """
    Protocol for adapters that support health checks.
    
    Health checks verify that the adapter can communicate with its
    backing service/domain and return expected data.
    """
    
    def check_health(self) -> bool:
        """
        Check if adapter and its backing service are operational.
        
        Returns:
            bool: True if healthy, False otherwise.
        """
        ...
