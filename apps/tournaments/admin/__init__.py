# apps/tournaments/admin/__init__.py
"""
Aggregate Tournament-related admin registrations and re-export public names.
Ensure module side-effects happen at import time so ModelAdmins are registered.
"""

# Ensure side effects (registrations) run
from . import base as _base  # noqa: F401
from . import disputes as _disputes  # noqa: F401  # make sure MatchDispute is registered

# Explicit re-exports for stable imports
from .tournaments import (  # noqa: F401
    TournamentAdmin,
    action_generate_bracket,
    action_lock_bracket,
)
from .registrations import (  # noqa: F401
    RegistrationAdmin,
    action_verify_payment,
    action_reject_payment,
)
from .matches import (  # noqa: F401
    MatchAdmin,
    action_auto_schedule,
    action_clear_schedule,
)
from .disputes import (  # noqa: F401
    MatchDisputeAdmin,
)
from .exports import (  # noqa: F401
    export_tournaments_csv,
    export_disputes_csv,
    export_matches_csv,
)

__all__ = [
    # Admins
    "TournamentAdmin", "RegistrationAdmin", "MatchAdmin", "MatchDisputeAdmin",
    # Tournament actions
    "action_generate_bracket", "action_lock_bracket",
    # Registration actions
    "action_verify_payment", "action_reject_payment",
    # Match/tournament scheduling actions
    "action_auto_schedule", "action_clear_schedule",
    # CSV exports
    "export_tournaments_csv", "export_disputes_csv", "export_matches_csv",
]
