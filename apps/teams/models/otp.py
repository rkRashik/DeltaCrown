# apps/teams/models/otp.py
"""
OTP-based verification for sensitive team operations.
Extends the existing EmailOTP system for team-specific operations.
"""
import secrets
from datetime import timedelta
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.accounts.models import EmailOTP


class TeamOTP(models.Model):
    """
    One-time password for sensitive team operations (e.g., leave team).
    Reuses EmailOTP patterns but for team-specific actions.
    """

    class Purpose(models.TextChoices):
        LEAVE_TEAM = "leave_team", "Leave Team"
        DELETE_TEAM = "delete_team", "Delete Team"
        TRANSFER_OWNERSHIP = "transfer_ownership", "Transfer Ownership"

    code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=32, choices=Purpose.choices, default=Purpose.LEAVE_TEAM
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_otps",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="team_otps",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "team", "purpose", "is_used"]),
            models.Index(fields=["code", "expires_at"]),
        ]

    EXPIRATION_MINUTES = 10
    MAX_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = timedelta(minutes=2)
    RATE_LIMIT_MAX = 3

    class RequestThrottled(Exception):
        def __init__(self, retry_after: int):
            self.retry_after = retry_after
            super().__init__("Too many OTP requests. Please wait before trying again.")

    @dataclass
    class VerificationResult:
        success: bool
        error_code: Optional[str] = None
        message: Optional[str] = None
        locked: bool = False

    @classmethod
    def issue(
        cls, user, team, purpose: str = Purpose.LEAVE_TEAM, minutes: int | None = None
    ) -> "TeamOTP":
        """
        Issue a new OTP code and send it via email.

        Args:
            user: User requesting the OTP
            team: Team the operation applies to
            purpose: Purpose of the OTP
            minutes: Expiration time in minutes (default: 10)

        Returns:
            TeamOTP instance

        Raises:
            RequestThrottled: If rate limit exceeded
        """
        now = timezone.now()
        window_start = now - cls.RATE_LIMIT_WINDOW

        # Check rate limit
        recent_count = cls.objects.filter(
            user=user, team=team, purpose=purpose, created_at__gte=window_start
        ).count()

        if recent_count >= cls.RATE_LIMIT_MAX:
            first_otp = (
                cls.objects.filter(
                    user=user, team=team, purpose=purpose, created_at__gte=window_start
                )
                .order_by("created_at")
                .first()
            )
            retry_after = int(
                (first_otp.created_at + cls.RATE_LIMIT_WINDOW - now).total_seconds()
            )
            raise cls.RequestThrottled(max(retry_after, 1))

        # Generate OTP code
        code = f"{secrets.randbelow(10**6):06d}"
        expiry = now + timedelta(minutes=minutes or cls.EXPIRATION_MINUTES)

        # Create OTP instance
        otp = cls.objects.create(
            user=user, team=team, code=code, purpose=purpose, expires_at=expiry
        )

        # Send email
        otp.send_email()

        return otp

    def send_email(self):
        """Send OTP code via email."""
        purpose_labels = {
            self.Purpose.LEAVE_TEAM: "Leave Team",
            self.Purpose.DELETE_TEAM: "Delete Team",
            self.Purpose.TRANSFER_OWNERSHIP: "Transfer Ownership",
        }

        subject = f"Team Operation Verification Code - {self.team.name}"
        context = {
            "code": self.code,
            "team_name": self.team.name,
            "purpose": purpose_labels.get(self.purpose, self.purpose),
            "expires_minutes": self.EXPIRATION_MINUTES,
            "user_name": self.user.get_full_name() or self.user.username,
        }

        html_message = render_to_string("teams/emails/team_otp.html", context)
        plain_message = render_to_string("teams/emails/team_otp.txt", context)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.user.email],
            html_message=html_message,
            fail_silently=False,
        )

    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at

    def verify_code(self, code: str) -> "TeamOTP.VerificationResult":
        """
        Verify the provided code.

        Args:
            code: Code to verify

        Returns:
            VerificationResult with success status and details
        """
        now = timezone.now()

        # Check if already used
        if self.is_used:
            return self.VerificationResult(
                success=False,
                error_code="OTP_ALREADY_USED",
                message="This verification code has already been used.",
            )

        # Check if expired
        if now > self.expires_at:
            return self.VerificationResult(
                success=False,
                error_code="OTP_EXPIRED",
                message="This verification code has expired. Please request a new one.",
            )

        # Increment attempts
        self.attempts += 1
        update_fields = ["attempts"]

        # Check if code matches
        success = code == self.code

        if success:
            self.is_used = True
            update_fields.append("is_used")

        # Check if locked after this attempt
        locked = self.attempts >= self.MAX_ATTEMPTS and not success

        self.save(update_fields=update_fields)

        if success:
            return self.VerificationResult(success=True)

        if locked:
            # Invalidate all pending OTPs for this user/team/purpose
            self.__class__.objects.filter(
                user=self.user, team=self.team, purpose=self.purpose, is_used=False
            ).update(is_used=True)

            return self.VerificationResult(
                success=False,
                error_code="OTP_LOCKED",
                message="Too many failed attempts. Please request a new verification code.",
                locked=True,
            )

        remaining = self.MAX_ATTEMPTS - self.attempts
        return self.VerificationResult(
            success=False,
            error_code="OTP_INVALID",
            message=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    def __str__(self) -> str:
        return f"OTP for {self.user.username} - {self.team.name} ({self.purpose})"
