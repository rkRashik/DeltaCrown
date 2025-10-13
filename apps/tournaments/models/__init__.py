# apps/tournaments/models/__init__.py
"""
DeltaCrown — tournaments models public API.

This package exposes models, enums/constants, and helper functions while
keeping the import surface stable for the rest of the project.

Typical usage:
    from apps.tournaments.models import (
        Tournament, Registration, Bracket, Match,
        TournamentSettings, BracketVisibility,
        MatchEvent, MatchComment, MatchDispute,
        STATUS_CHOICES, PAYMENT_METHODS,
        tournament_banner_path, rules_pdf_path, rules_upload_path,
    )
"""

# Constants (kept for compatibility with forms/admin/tests)
from .constants import STATUS_CHOICES, PAYMENT_METHODS

# Helper functions used by File/Image fields
from .paths import tournament_banner_path, rules_pdf_path, rules_upload_path

# Enums
from .enums import BracketVisibility

# Models
from .tournament import Tournament
from .registration import Registration
from .registration_request import RegistrationRequest
from .bracket import Bracket
from .match import Match
from .tournament_settings import TournamentSettings
from .events import MatchEvent, MatchComment
from .dispute import MatchDispute
from .evidence import MatchDisputeEvidence
from .payment_verification import PaymentVerification

# Core refactored models (Phase 1)
from .core import TournamentSchedule, TournamentCapacity, TournamentFinance
from .tournament_media import TournamentMedia
from .tournament_rules import TournamentRules
from .tournament_archive import TournamentArchive

# Game configuration models (Dynamic Registration Form)
from .game_config import GameConfiguration
from .game_field_config import GameFieldConfiguration
from .player_role_config import PlayerRoleConfiguration

# Explicit public API (prevents accidental leaks and makes static analyzers happy)
__all__ = [
    # constants
    "STATUS_CHOICES",
    "PAYMENT_METHODS",
    # helpers
    "tournament_banner_path",
    "rules_pdf_path",
    "rules_upload_path",
    # enums
    "BracketVisibility",
    # models
    "Tournament",
    "Registration",
    "RegistrationRequest",
    "Bracket",
    "Match",
    "TournamentSettings",
    "MatchEvent",
    "MatchComment",
    "MatchDispute",
    "MatchDisputeEvidence",
    "PaymentVerification",
    # core refactored models (Phase 1)
    "TournamentSchedule",
    "TournamentCapacity",
    "TournamentFinance",
    "TournamentMedia",
    "TournamentRules",
    "TournamentArchive",
    # game configuration models
    "GameConfiguration",
    "GameFieldConfiguration",
    "PlayerRoleConfiguration",
]
