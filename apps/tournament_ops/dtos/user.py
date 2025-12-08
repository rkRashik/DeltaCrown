"""
User profile DTOs.

Data Transfer Objects for user and profile-related data.
"""

from dataclasses import dataclass
from typing import Optional, List

from .base import DTOBase


@dataclass
class UserProfileDTO(DTOBase):
    """
    DTO for user profile data.

    Represents user contact information and game account identities without
    coupling to the Django User or UserProfile ORM models. Used by UserAdapter
    to return profile data to TournamentOps orchestration layer.

    Attributes:
        email: User's email address.
        email_verified: Whether the email has been verified.
        phone: Optional phone number.
        phone_verified: Whether the phone number has been verified.
        discord: Optional Discord username/tag.
        riot_id: Optional Riot Games account ID (for Valorant, LoL, etc.).
        steam_id: Optional Steam account ID.
        pubg_mobile_id: Optional PUBG Mobile account ID.
        age: Optional user age (for eligibility checks).
        region: Optional geographic region (for regional tournaments).
    """

    email: str
    email_verified: bool
    phone: Optional[str]
    phone_verified: bool
    discord: Optional[str]
    riot_id: Optional[str]
    steam_id: Optional[str]
    pubg_mobile_id: Optional[str]
    age: Optional[int]
    region: Optional[str]

    @classmethod
    def from_model(cls, model: any) -> "UserProfileDTO":
        """
        Create UserProfileDTO from a user/profile model.

        Args:
            model: User or UserProfile model instance or dict.

        Returns:
            UserProfileDTO instance.
        """
        return cls(
            email=getattr(model, "email", model.get("email") if hasattr(model, "get") else ""),
            email_verified=getattr(model, "email_verified", model.get("email_verified") if hasattr(model, "get") else False),
            phone=getattr(model, "phone", model.get("phone") if hasattr(model, "get") else None),
            phone_verified=getattr(model, "phone_verified", model.get("phone_verified") if hasattr(model, "get") else False),
            discord=getattr(model, "discord", model.get("discord") if hasattr(model, "get") else None),
            riot_id=getattr(model, "riot_id", model.get("riot_id") if hasattr(model, "get") else None),
            steam_id=getattr(model, "steam_id", model.get("steam_id") if hasattr(model, "get") else None),
            pubg_mobile_id=getattr(model, "pubg_mobile_id", model.get("pubg_mobile_id") if hasattr(model, "get") else None),
            age=getattr(model, "age", model.get("age") if hasattr(model, "get") else None),
            region=getattr(model, "region", model.get("region") if hasattr(model, "get") else None),
        )

    def validate(self) -> List[str]:
        """
        Validate user profile data.

        Ensures:
        - email is not empty
        - if email_verified is False, user may have restrictions
        - age is positive if present

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.email:
            errors.append("email cannot be empty")

        if self.age is not None and self.age <= 0:
            errors.append("age must be positive")

        return errors
