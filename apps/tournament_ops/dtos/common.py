"""
Common/shared DTOs.

Generic Data Transfer Objects used across multiple adapters.
"""

from dataclasses import dataclass
from typing import List

from .base import DTOBase


@dataclass
class ValidationResult(DTOBase):
    """
    Generic validation result DTO.

    Returned by adapter methods that perform validation checks (e.g., team eligibility,
    user eligibility, identity verification). Provides a consistent structure for
    communicating success/failure and error details.

    Attributes:
        is_valid: True if validation passed, False otherwise.
        errors: List of error messages if validation failed (empty if valid).
    """

    is_valid: bool
    errors: List[str]
