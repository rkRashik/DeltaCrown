from __future__ import annotations

import secrets
from datetime import timedelta
from typing import List, Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user that tracks email verification state."""

    is_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether the user has verified their email address."),
        verbose_name=_("email verified"),
    )

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    def mark_email_verified(self, *, commit: bool = True) -> None:
        """Mark the user as verified (and active) in a single helper."""

        changed_fields: List[str] = []
        if not self.is_verified:
            self.is_verified = True
            changed_fields.append("is_verified")
        if not self.is_active:
            self.is_active = True
            changed_fields.append("is_active")
        if commit and changed_fields:
            self.save(update_fields=changed_fields)


class EmailOTP(models.Model):
    """One-time verification codes used for email confirmation."""

    PURPOSE_SIGNUP = "signup"
    PURPOSE_CHOICES = ((PURPOSE_SIGNUP, "signup"),)

    CODE_LENGTH = 6
    DEFAULT_TTL_MINUTES = 10
    RESEND_COOLDOWN_SECONDS = 60
    MAX_ATTEMPTS = 5

    class RateLimitError(Exception):
        """Raised when a new OTP is requested too quickly."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=CODE_LENGTH)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default=PURPOSE_SIGNUP)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "purpose", "is_used", "created_at"])]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"EmailOTP<{self.user_id}:{self.code}>"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def attempts_remaining(self) -> int:
        return max(self.MAX_ATTEMPTS - self.attempts, 0)

    def register_attempt(self, *, success: bool) -> None:
        self.attempts += 1
        fields = ["attempts"]
        if success and not self.is_used:
            self.is_used = True
            fields.append("is_used")
        elif success and self.is_used:
            # ensure attempts persisted even if already used (rare)
            pass
        self.save(update_fields=fields)

    def verify(self, code: str) -> bool:
        if self.is_used or self.is_expired:
            return False
        success = secrets.compare_digest(self.code, str(code).strip())
        self.register_attempt(success=success)
        return success

    @classmethod
    def purge_expired(cls) -> int:
        """Remove expired unused OTPs to keep the table tidy."""

        return cls.objects.filter(is_used=False, expires_at__lt=timezone.now()).delete()[0]

    @classmethod
    def _ensure_cooldown(cls, *, user, purpose: str) -> None:
        cutoff = timezone.now() - timedelta(seconds=cls.RESEND_COOLDOWN_SECONDS)
        latest = (
            cls.objects.filter(user=user, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if latest and latest.created_at > cutoff:
            raise cls.RateLimitError("OTP recently sent; please wait before requesting a new one.")

    @classmethod
    def create_for_user(
        cls,
        user,
        *,
        purpose: str = PURPOSE_SIGNUP,
        ttl_minutes: Optional[int] = None,
        enforce_cooldown: bool = True,
    ):
        """Create a fresh OTP for the user, optionally enforcing resend cooldown."""

        ttl = ttl_minutes or cls.DEFAULT_TTL_MINUTES
        cls.purge_expired()
        if enforce_cooldown:
            cls._ensure_cooldown(user=user, purpose=purpose)
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        code = f"{secrets.randbelow(10**cls.CODE_LENGTH):0{cls.CODE_LENGTH}d}"
        now = timezone.now()
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=now + timedelta(minutes=ttl),
        )
