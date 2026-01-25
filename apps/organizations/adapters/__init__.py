"""
Service Adapters for Team & Organization vNext

This package provides compatibility adapters that route dependent applications
(tournaments, notifications, user_profile, etc.) to the correct backend during
the migration period (Phases 3-7).

Routing Strategy (P3-T2 with Feature Flags):
- Feature flags control routing behavior (FORCE_LEGACY, ADAPTER_ENABLED, ROUTING_MODE)
- If flags say vNext AND team_id exists in organizations.Team → route to TeamService
- Otherwise → route to legacy system (teams.Team) preserving existing behavior

Feature Flags:
- TEAM_VNEXT_FORCE_LEGACY: Emergency killswitch (forces all legacy)
- TEAM_VNEXT_ADAPTER_ENABLED: Master switch for adapter
- TEAM_VNEXT_ROUTING_MODE: "legacy_only" | "vnext_only" | "auto"
- TEAM_VNEXT_TEAM_ALLOWLIST: List of team IDs for auto mode

Zero Breaking Changes Guarantee:
- All legacy teams continue to work with zero modifications
- URL patterns remain stable (redirects preserve old notification links)
- Performance overhead: +1 query maximum for routing decision (0 queries when adapter disabled)
"""

from .team_adapter import TeamAdapter
from .flags import should_use_vnext_routing, get_routing_reason
from .metrics import record_routing_decision, record_adapter_error, MetricsContext

__all__ = [
    "TeamAdapter",
    "should_use_vnext_routing",
    "get_routing_reason",
    "record_routing_decision",
    "record_adapter_error",
    "MetricsContext",
]
