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
from .bracket import Bracket
from .match import Match
from .tournament_settings import TournamentSettings
from .events import MatchEvent, MatchComment
from .dispute import MatchDispute
from .payment_verification import PaymentVerification

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
    "Bracket",
    "Match",
    "TournamentSettings",
    "MatchEvent",
    "MatchComment",
    "MatchDispute",
]
