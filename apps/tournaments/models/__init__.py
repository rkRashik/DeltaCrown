"""
Tournament models package.

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 4.1)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 3, 4)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-003, ADR-004)

Exports all tournament-related models for easy importing.
"""

from .tournament import (
    Game,
    Tournament,
    CustomField,
    TournamentVersion,
)
from .registration import (
    Registration,  # Full implementation (Module 1.3)
    Payment,       # Full implementation (Module 1.3)
)
from .bracket import (
    Bracket,       # Full implementation (Module 1.5)
    BracketNode,   # Full implementation (Module 1.5)
)
from .match import (
    Match,    # Full implementation (Module 1.4)
    Dispute,  # Full implementation (Module 1.4)
)
from .security import (
    AuditLog,  # Full implementation (Module 2.4)
)

__all__ = [
    'Game',
    'Tournament',
    'CustomField',
    'TournamentVersion',
    'Registration',
    'Payment',
    'Bracket',
    'BracketNode',
    'Match',
    'Dispute',
    'AuditLog',
]
