"""
Base utilities for DTOs.

Provides common helpers for all Data Transfer Objects in the TournamentOps domain.
"""

from dataclasses import asdict
from typing import Any, Dict


class DTOBase:
    """Base mixin for all DTOs, providing common helpers."""

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize DTO to a plain dict.

        Returns:
            Dictionary representation of the DTO.
        """
        return asdict(self)
