"""
User profile DTOs.

Data Transfer Objects for user and profile-related data.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

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
        game_ids: Dict mapping game slug to IGN (from GameProfile/passport).
        age: Optional user age (for eligibility checks).
        region: Optional geographic region (for regional tournaments).
    """

    email: str
    email_verified: bool
    phone: Optional[str]
    phone_verified: bool
    discord: Optional[str]
    game_ids: Dict[str, str] = field(default_factory=dict)
    age: Optional[int] = None
    region: Optional[str] = None

    @classmethod
    def from_model(cls, model) -> "UserProfileDTO":
        """
        Create UserProfileDTO from a user/profile model.

        Args:
            model: User or UserProfile model instance or dict.

        Returns:
            UserProfileDTO instance.
        """
        # Dict passthrough
        if isinstance(model, dict):
            return cls(
                email=model.get("email", ""),
                email_verified=model.get("email_verified", False),
                phone=model.get("phone"),
                phone_verified=model.get("phone_verified", False),
                discord=model.get("discord"),
                game_ids=model.get("game_ids", {}),
                age=model.get("age"),
                region=model.get("region"),
            )

        # ORM model — resolve user reference
        user = None
        if hasattr(model, 'user'):
            user = model.user  # UserProfile.user
        elif hasattr(model, 'pk') and hasattr(model, 'email'):
            user = model  # model IS the User instance

        # Email from auth.User
        email = ""
        if user:
            email = getattr(user, "email", "")
        elif hasattr(model, "email"):
            email = model.email or ""

        # Email verified — check allauth EmailAddress if available,
        # otherwise fall back to user.is_active
        email_verified = False
        if user:
            try:
                from allauth.account.models import EmailAddress
                email_verified = EmailAddress.objects.filter(
                    user=user, email=email, verified=True
                ).exists()
            except (ImportError, Exception):
                email_verified = getattr(user, "is_active", False)

        # Discord handle from SocialLink model
        discord = None
        if user:
            try:
                from apps.user_profile.models_main import SocialLink
                link = SocialLink.objects.filter(
                    user=user, platform='discord'
                ).first()
                if link:
                    discord = link.handle or link.url
            except Exception:
                pass

        # Age computed from date_of_birth
        age = None
        dob = getattr(model, "date_of_birth", None)
        if dob:
            try:
                from datetime import date
                today = date.today()
                age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
            except Exception:
                pass

        # Build game_ids from GameProfile records
        game_ids: Dict[str, str] = {}
        if user:
            try:
                from apps.user_profile.models_main import GameProfile
                for gp in GameProfile.objects.filter(user=user).select_related('game'):
                    if gp.game and gp.ign:
                        ign = gp.ign
                        if gp.discriminator:
                            ign = f"{ign}#{gp.discriminator}"
                        game_ids[gp.game.slug] = ign
            except Exception:
                pass

        return cls(
            email=email,
            email_verified=email_verified,
            phone=getattr(model, "phone", None) or None,
            phone_verified=getattr(model, "phone_verified", False),
            discord=discord,
            game_ids=game_ids,
            age=age,
            region=getattr(model, "region", None) or None,
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
