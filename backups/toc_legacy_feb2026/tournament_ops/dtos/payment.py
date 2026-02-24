"""
Payment DTOs.

Data Transfer Objects for payment transaction results.
"""

from dataclasses import dataclass
from typing import Optional, List

from .base import DTOBase


@dataclass
class PaymentResultDTO(DTOBase):
    """
    DTO for payment transaction results.

    Returned by payment orchestration services to communicate the outcome
    of payment operations (charges, refunds, etc.).

    Attributes:
        success: True if payment succeeded, False otherwise.
        transaction_id: Optional transaction ID from the payment processor.
        error: Optional error message if payment failed.
    """

    success: bool
    transaction_id: Optional[str]
    error: Optional[str]

    @classmethod
    def from_model(cls, model: any) -> "PaymentResultDTO":
        """
        Create PaymentResultDTO from a payment result object.

        Args:
            model: Payment result object or dict.

        Returns:
            PaymentResultDTO instance.
        """
        return cls(
            success=getattr(model, "success", model.get("success") if hasattr(model, "get") else False),
            transaction_id=getattr(model, "transaction_id", model.get("transaction_id") if hasattr(model, "get") else None),
            error=getattr(model, "error", model.get("error") if hasattr(model, "get") else None),
        )

    def validate(self) -> List[str]:
        """
        Validate payment result consistency.

        Ensures that success/transaction_id/error combinations are consistent:
        - If success=True, transaction_id should be present and error should be None
        - If success=False, error should be present and transaction_id may be None

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if self.success:
            if not self.transaction_id:
                errors.append("Successful payment must have transaction_id")
            if self.error:
                errors.append("Successful payment should not have error message")
        else:
            if not self.error:
                errors.append("Failed payment must have error message")

        return errors
