"""
Eligibility DTOs.

Data Transfer Objects for eligibility check results.
"""

from dataclasses import dataclass
from typing import List

from .base import DTOBase


@dataclass
class EligibilityResultDTO(DTOBase):
    """
    DTO for eligibility check results.

    Returned by eligibility validation services to communicate whether a user
    or team is eligible for a tournament, along with detailed reasons if not.

    Attributes:
        is_eligible: True if eligible, False otherwise.
        reasons: List of human-readable reasons for ineligibility (empty if eligible).
    """

    is_eligible: bool
    reasons: List[str]

    @classmethod
    def from_model(cls, model: any) -> "EligibilityResultDTO":
        """
        Create EligibilityResultDTO from an eligibility check result.

        Args:
            model: Eligibility result object or dict.

        Returns:
            EligibilityResultDTO instance.
        """
        return cls(
            is_eligible=getattr(model, "is_eligible", model.get("is_eligible") if hasattr(model, "get") else False),
            reasons=getattr(model, "reasons", model.get("reasons") if hasattr(model, "get") else []),
        )

    def validate(self) -> List[str]:
        """
        Validate eligibility result consistency.

        Ensures that if is_eligible=True, reasons list is empty (no reasons
        for ineligibility when eligible).

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if self.is_eligible and self.reasons:
            errors.append("Eligible result should not have ineligibility reasons")

        if not self.is_eligible and not self.reasons:
            errors.append("Ineligible result must have at least one reason")

        return errors
