"""
Feature flags for Team vNext adapter routing.

This module provides a settings-based feature flag system for controlling
routing between legacy (apps.teams) and vNext (apps.organizations) systems.

Design Principles:
- Zero-breaking: All defaults favor legacy routing (safe fallback)
- Settings-based: No database dependencies (no Waffle)
- Priority-based: Clear hierarchy for flag evaluation
- Emergency override: FORCE_LEGACY takes absolute priority

Routing Priority (evaluated in order):
1. TEAM_VNEXT_FORCE_LEGACY=True → Always legacy (emergency killswitch)
2. TEAM_VNEXT_ADAPTER_ENABLED=False → Legacy (feature disabled)
3. ROUTING_MODE="legacy_only" → Legacy (default safe mode)
4. ROUTING_MODE="vnext_only" → vNext (aggressive adoption)
5. ROUTING_MODE="auto" + team in allowlist → vNext
6. ROUTING_MODE="auto" + team not in allowlist → Legacy
7. Fallback: Legacy (if settings missing/invalid)

Performance:
- Zero queries (all settings cached by Django)
- <1ms typical decision time

Thread Safety:
- Read-only access to Django settings (thread-safe)
- No mutable shared state

Example Usage:
    from apps.organizations.adapters.flags import should_use_vnext_routing
    
    if should_use_vnext_routing(team_id=123):
        # Use vNext TeamService
        result = TeamService.get_team_url(team_id)
    else:
        # Use legacy apps.teams models
        result = legacy_get_team_url(team_id)

Settings Configuration (deltacrown/settings.py):
    # Emergency killswitch (takes absolute priority)
    TEAM_VNEXT_FORCE_LEGACY = False  # True = force all traffic to legacy
    
    # Feature flag (master switch)
    TEAM_VNEXT_ADAPTER_ENABLED = False  # False = legacy, True = consider routing_mode
    
    # Routing mode (only applies if ADAPTER_ENABLED=True)
    TEAM_VNEXT_ROUTING_MODE = "legacy_only"  # "legacy_only" | "vnext_only" | "auto"
    
    # Allowlist for auto mode (team IDs that can use vNext)
    TEAM_VNEXT_TEAM_ALLOWLIST = []  # e.g., [123, 456, 789]
"""

from django.conf import settings
from typing import Literal

# Type alias for routing mode
RoutingMode = Literal["legacy_only", "vnext_only", "auto"]


def get_routing_mode() -> RoutingMode:
    """
    Get the current routing mode from settings.
    
    Returns:
        RoutingMode: One of "legacy_only", "vnext_only", "auto"
        Defaults to "legacy_only" if setting is missing or invalid.
    
    Performance:
        - <1ms (settings cached by Django)
    
    Thread Safety:
        - Read-only access to Django settings (thread-safe)
    """
    mode = getattr(settings, "TEAM_VNEXT_ROUTING_MODE", "legacy_only")
    
    # Validate mode (defensive: invalid values default to legacy)
    valid_modes = {"legacy_only", "vnext_only", "auto"}
    if mode not in valid_modes:
        return "legacy_only"
    
    return mode


def is_adapter_enabled() -> bool:
    """
    Check if the vNext adapter is enabled globally.
    
    Returns:
        bool: True if adapter can route to vNext, False forces legacy.
        Defaults to False (legacy) if setting is missing.
    
    Performance:
        - <1ms (settings cached by Django)
    
    Thread Safety:
        - Read-only access to Django settings (thread-safe)
    """
    return getattr(settings, "TEAM_VNEXT_ADAPTER_ENABLED", False)


def is_force_legacy_enabled() -> bool:
    """
    Check if emergency legacy fallback is enabled.
    
    This is the highest priority flag. When True, ALL traffic goes to legacy
    regardless of other settings. Use this for emergency rollback.
    
    Returns:
        bool: True forces all traffic to legacy (emergency mode).
        Defaults to False (normal operation).
    
    Performance:
        - <1ms (settings cached by Django)
    
    Thread Safety:
        - Read-only access to Django settings (thread-safe)
    
    Usage:
        Set TEAM_VNEXT_FORCE_LEGACY=True in settings to immediately roll back
        all adapter traffic to legacy system. No code changes required.
    """
    return getattr(settings, "TEAM_VNEXT_FORCE_LEGACY", False)


def get_team_allowlist() -> list[int]:
    """
    Get the list of team IDs allowed to use vNext routing in auto mode.
    
    Returns:
        list[int]: Team IDs that can route to vNext in auto mode.
        Defaults to empty list if setting is missing.
    
    Performance:
        - <1ms (settings cached by Django)
    
    Thread Safety:
        - Read-only access to Django settings (thread-safe)
    
    Notes:
        - Only applies when ROUTING_MODE="auto"
        - Empty list means no teams use vNext (all legacy)
        - Used for gradual rollout (allowlist specific teams)
    """
    allowlist = getattr(settings, "TEAM_VNEXT_TEAM_ALLOWLIST", [])
    
    # Defensive: ensure it's a list
    if not isinstance(allowlist, list):
        return []
    
    return allowlist


def should_use_vnext_routing(team_id: int) -> bool:
    """
    Determine if a team should use vNext routing based on feature flags.
    
    This is the primary decision function used by TeamAdapter.
    
    Priority Evaluation (in order):
    1. If FORCE_LEGACY=True → return False (emergency override)
    2. If ADAPTER_ENABLED=False → return False (feature disabled)
    3. If ROUTING_MODE="legacy_only" → return False
    4. If ROUTING_MODE="vnext_only" → return True
    5. If ROUTING_MODE="auto":
       - If team_id in allowlist → return True
       - Else → return False
    6. Fallback: return False (conservative default)
    
    Args:
        team_id: Team ID to evaluate for routing
    
    Returns:
        bool: True = use vNext routing, False = use legacy routing
    
    Performance:
        - <1ms (all settings cached, no queries)
    
    Thread Safety:
        - Read-only access (thread-safe)
    
    Example:
        >>> should_use_vnext_routing(123)
        False  # Default (legacy-first safe)
        
        >>> # With ADAPTER_ENABLED=True, ROUTING_MODE="auto", ALLOWLIST=[123]
        >>> should_use_vnext_routing(123)
        True
        >>> should_use_vnext_routing(456)
        False
    """
    # Priority 1: Emergency override (absolute priority)
    if is_force_legacy_enabled():
        return False
    
    # Priority 2: Feature flag check
    if not is_adapter_enabled():
        return False
    
    # Priority 3-5: Routing mode
    mode = get_routing_mode()
    
    if mode == "legacy_only":
        return False
    
    if mode == "vnext_only":
        return True
    
    if mode == "auto":
        allowlist = get_team_allowlist()
        return team_id in allowlist
    
    # Priority 6: Fallback (conservative default)
    return False


def get_routing_reason(team_id: int) -> str:
    """
    Get a human-readable explanation for routing decision.
    
    Useful for logging, debugging, and observability metrics.
    
    Args:
        team_id: Team ID to evaluate
    
    Returns:
        str: Reason code for routing decision
    
    Possible Return Values:
        - "force_legacy": FORCE_LEGACY=True (emergency)
        - "adapter_disabled": ADAPTER_ENABLED=False
        - "mode_legacy_only": ROUTING_MODE="legacy_only"
        - "mode_vnext_only": ROUTING_MODE="vnext_only"
        - "auto_allowlisted": In auto mode and team in allowlist
        - "auto_not_allowlisted": In auto mode but team not in allowlist
        - "fallback_legacy": Invalid state, defaulted to legacy
    
    Performance:
        - <1ms (settings cached)
    
    Example:
        >>> get_routing_reason(123)
        'adapter_disabled'  # Default state
    """
    # Check priority 1: Force legacy
    if is_force_legacy_enabled():
        return "force_legacy"
    
    # Check priority 2: Adapter disabled
    if not is_adapter_enabled():
        return "adapter_disabled"
    
    # Check priority 3-5: Routing mode
    mode = get_routing_mode()
    
    if mode == "legacy_only":
        return "mode_legacy_only"
    
    if mode == "vnext_only":
        return "mode_vnext_only"
    
    if mode == "auto":
        allowlist = get_team_allowlist()
        if team_id in allowlist:
            return "auto_allowlisted"
        else:
            return "auto_not_allowlisted"
    
    # Fallback
    return "fallback_legacy"
