# apps/tournaments/admin/__init__.py
"""
Aggregate Tournament-related admin registrations and explicitly re-export
CSV actions so test imports like:
    from apps.tournaments.admin import export_tournaments_csv
keep working after we moved to a package.
"""

# Import side-effects first to ensure ModelAdmins are registered
from . import base as _base  # noqa: F401

# Explicit re-exports for tests and callers that import from the package path
from .base import (  # noqa: F401
    TournamentAdmin,
    RegistrationAdmin,
    MatchAdmin,
    # Admin actions
    action_verify_payment,
    action_reject_payment,
    action_generate_bracket,
    action_lock_bracket,
    # CSV exports
    export_tournaments_csv,
    export_disputes_csv,
    export_matches_csv,
)

__all__ = [
    "TournamentAdmin",
    "RegistrationAdmin",
    "MatchAdmin",
    "action_verify_payment",
    "action_reject_payment",
    "action_generate_bracket",
    "action_lock_bracket",
    "export_tournaments_csv",
    "export_disputes_csv",
    "export_matches_csv",
]
