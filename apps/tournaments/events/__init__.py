"""
Tournament events module.

This stub allows the app to import and boot cleanly.
Actual event subscriptions will be added in Phase 3 (notifications/analytics).

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening (event system placeholder)
"""


def register_tournament_event_handlers():
    """
    Register tournament event handlers.
    
    This is a no-op stub for now to allow the app to boot.
    Future implementations will subscribe to events like:
    - tournament.created
    - tournament.started
    - registration.confirmed
    - match.completed
    - bracket.finalized
    """
    # No-op for now; keep import side-effects safe
    pass


# Alias for backwards compatibility
register = register_tournament_event_handlers
