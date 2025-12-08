"""
DTOs for TournamentOps cross-domain data exchange.

This package contains Data Transfer Objects used by service adapters to communicate
across domain boundaries without coupling to Django ORM models.
"""

from .game_identity import GamePlayerIdentityConfigDTO
from .team import TeamDTO
from .user import UserProfileDTO
from .common import ValidationResult
from .tournament import TournamentDTO
from .match import MatchDTO
from .registration import RegistrationDTO
from .eligibility import EligibilityResultDTO
from .payment import PaymentResultDTO
from .stage import StageDTO

__all__ = [
    "GamePlayerIdentityConfigDTO",
    "TeamDTO",
    "UserProfileDTO",
    "ValidationResult",
    "TournamentDTO",
    "MatchDTO",
    "RegistrationDTO",
    "EligibilityResultDTO",
    "PaymentResultDTO",
    "StageDTO",
]
