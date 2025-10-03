"""
Django Admin Configuration for Tournament Models

 DEPRECATED: This file is deprecated as of Phase 2 Admin Reorganization (Oct 2025).
All admin classes have been moved to the modular apps/tournaments/admin/ structure.

This file now serves only as an import hub for backward compatibility.
It will be removed in a future version.

New Location Mapping:
- Tournament admin classes  apps/tournaments/admin/tournaments.py
- Registration admin classes  apps/tournaments/admin/registrations.py  
- Match admin  apps/tournaments/admin/matches.py
- Bracket admin  apps/tournaments/admin/brackets.py
- Dispute admin  apps/tournaments/admin/disputes.py
- Payment admin  apps/tournaments/admin/payments.py
- Attendance admin  apps/tournaments/admin/attendance.py

Please update your imports to use the new modular structure.
"""

import warnings

warnings.warn(
    "apps/tournaments/admin.py is deprecated. "
    "All admin classes have been moved to apps/tournaments/admin/ modules. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2
)

# Import all admin classes from modular structure for backward compatibility
from .admin.tournaments import (
    TournamentAdmin,
    TournamentScheduleAdmin,
    TournamentCapacityAdmin,
    TournamentFinanceAdmin,
    TournamentMediaAdmin,
    TournamentRulesAdmin,
    TournamentArchiveAdmin,
)  # noqa
from .admin.matches import MatchAdmin  # noqa
from .admin.brackets import BracketAdmin  # noqa
from .admin.disputes import MatchDisputeAdmin  # noqa
from .admin.attendance import MatchAttendanceAdmin  # noqa
from .admin.registrations import RegistrationAdmin, RegistrationRequestAdmin  # noqa

# Payment admin imports (with error handling for optional modules)
try:
    from .admin.payments import *  # noqa
except Exception:
    pass

__all__ = [
    'TournamentAdmin',
    'TournamentScheduleAdmin',
    'TournamentCapacityAdmin',
    'TournamentFinanceAdmin',
    'TournamentMediaAdmin',
    'TournamentRulesAdmin',
    'TournamentArchiveAdmin',
    'MatchAdmin',
    'BracketAdmin',
    'MatchDisputeAdmin',
    'MatchAttendanceAdmin',
    'RegistrationAdmin',
    'RegistrationRequestAdmin',
]
