# apps/tournaments/models/__init__.py
"""
Public models API for the tournaments app.

Re-exports split model classes and constants so existing imports keep working:
    from apps.tournaments.models import Tournament, Registration, Bracket, Match,
                                      BracketVisibility, TournamentSettings,
                                      MatchEvent, MatchComment, MatchDispute,
                                      STATUS_CHOICES, PAYMENT_METHODS,
                                      tournament_banner_path, rules_pdf_path, rules_upload_path
"""

# Re-export legacy constants
from .constants import STATUS_CHOICES, PAYMENT_METHODS  # noqa: F401

# Re-export helper functions so existing imports continue to work
from .paths import tournament_banner_path, rules_pdf_path, rules_upload_path  # noqa: F401

# Re-export model classes (public API)
from .tournament import Tournament  # noqa: F401
from .registration import Registration  # noqa: F401
from .bracket import Bracket  # noqa: F401
from .match import Match  # noqa: F401
from .enums import BracketVisibility  # noqa: F401
from .tournament_settings import TournamentSettings  # noqa: F401
from .events import MatchEvent, MatchComment  # noqa: F401
from .dispute import MatchDispute  # noqa: F401
