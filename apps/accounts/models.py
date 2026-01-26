"""Custom user and email verification models for DeltaCrown."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models, transaction
from django.utils import timezone


class UserManager(DjangoUserManager):
    """Require email for every account and normalise during creation."""

    def _create_user(self, username, email, password, **extra_fields):  # type: ignore[override]
        if not email:
            raise ValueError("The email address must be provided")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_verified", False)
        return super()._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        user = super().create_superuser(username, email, password, **extra_fields)
        if not user.email_verified_at:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
        return user


class User(AbstractUser):
    """Project user model with mandatory unique email and verification flag."""

    email = models.EmailField("email address", unique=True)
    is_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta(AbstractUser.Meta):  # type: ignore[misc]
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        """Display username with public_id if UserProfile exists."""
        try:
            # Try to get UserProfile public_id
            profile = getattr(self, 'profile', None)
            if profile and hasattr(profile, 'public_id') and profile.public_id:
                return f"{self.username} ({profile.public_id})"
        except Exception:
            pass
        return self.username

    def mark_email_verified(self):
        if not self.is_verified:
            self.is_verified = True
            self.email_verified_at = timezone.now()
            self.is_active = True
            self.save(update_fields=["is_verified", "email_verified_at", "is_active"])

    @property
    def avatar(self):
        """Convenience accessor that proxies to the related UserProfile avatar field, if present."""
        try:
            prof = getattr(self, 'profile', None)
            return getattr(prof, 'avatar', None)
        except Exception:
            return None

    @property
    def banner(self):
        """Convenience accessor that proxies to the related UserProfile banner field, if present."""
        try:
            prof = getattr(self, 'profile', None)
            return getattr(prof, 'banner', None)
        except Exception:
            return None


class PendingSignup(models.Model):
    """Temporary record that stores credentials until email verification succeeds."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def create_user(self) -> User:
        user_model = get_user_model()
        with transaction.atomic():
            user, created = user_model.objects.get_or_create(
                email=self.email,
                defaults={
                    "username": self.username,
                    "is_active": True,
                    "is_verified": True,
                    "email_verified_at": timezone.now(),
                },
            )
            user.username = self.username
            user.is_active = True
            user.is_verified = True
            if not user.email_verified_at:
                user.email_verified_at = timezone.now()
            user.password = self.password_hash
            user.save(update_fields=["username", "password", "is_active", "is_verified", "email_verified_at"])
        return user

    def __str__(self) -> str:
        return f"PendingSignup<{self.email}>"


class EmailOTP(models.Model):
    """Time-bound one-time password for email verification flows."""

    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Signup"

    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=16, choices=Purpose.choices, default=Purpose.SIGNUP)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_otps",
        null=True,
        blank=True,
    )
    pending_signup = models.ForeignKey(
        "PendingSignup",
        on_delete=models.CASCADE,
        related_name="email_otps",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    EXPIRATION_MINUTES = 10
    MAX_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = timedelta(minutes=2)
    RATE_LIMIT_MAX = 3
    STALE_ACCOUNT_RETENTION = timedelta(hours=24)

    class RequestThrottled(Exception):
        def __init__(self, retry_after: int):
            self.retry_after = retry_after
            super().__init__("Too many OTP requests. Please wait before trying again.")

    @dataclass
    class VerificationResult:
        success: bool
        reason: str | None = None
        locked: bool = False
        user: User | None = None

    def clean(self):
        if bool(self.user_id) == bool(self.pending_signup_id):
            raise ValueError("EmailOTP must reference exactly one account target")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    @classmethod
    def issue(cls, user=None, *, pending_signup=None, purpose: str = Purpose.SIGNUP, minutes: int | None = None) -> "EmailOTP":
        if (user is None) == (pending_signup is None):
            raise ValueError("Provide either 'user' or 'pending_signup' when issuing an OTP")
        cls.prune_stale_unverified()
        now = timezone.now()
        window_start = now - cls.RATE_LIMIT_WINDOW
        filters = {"purpose": purpose, "created_at__gte": window_start}
        if user is not None:
            filters["user"] = user
        else:
            filters["pending_signup"] = pending_signup
        recent_qs = cls.objects.filter(**filters).order_by("created_at")
        if recent_qs.count() >= cls.RATE_LIMIT_MAX:
            first = recent_qs.first()
            retry_after = int((first.created_at + cls.RATE_LIMIT_WINDOW - now).total_seconds()) if first else int(cls.RATE_LIMIT_WINDOW.total_seconds())
            raise cls.RequestThrottled(max(retry_after, 1))

        code = f"{secrets.randbelow(10**6):06d}"
        expiry = now + timedelta(minutes=minutes or cls.EXPIRATION_MINUTES)
        return cls.objects.create(
            user=user,
            pending_signup=pending_signup,
            code=code,
            purpose=purpose,
            expires_at=expiry,
        )

    @classmethod
    def prune_stale_unverified(cls) -> int:
        cutoff = timezone.now() - cls.STALE_ACCOUNT_RETENTION
        deleted_total = 0

        pending_qs = PendingSignup.objects.filter(created_at__lt=cutoff)
        pending_ids = list(pending_qs.values_list("id", flat=True))
        if pending_ids:
            cls.objects.filter(pending_signup_id__in=pending_ids).delete()
        deleted_total += pending_qs.delete()[0]

        user_model = get_user_model()
        user_qs = user_model.objects.filter(is_verified=False, is_active=False, date_joined__lt=cutoff)
        user_ids = list(user_qs.values_list("id", flat=True))
        if user_ids:
            cls.objects.filter(user_id__in=user_ids).delete()
        deleted_total += user_qs.delete()[0]

        return deleted_total

    @classmethod
    def purge_user(cls, user) -> None:
        if isinstance(user, PendingSignup):
            cls.objects.filter(pending_signup=user).delete()
            user.delete()
            return
        cls.objects.filter(user=user).delete()
        user.delete()

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def verify_code(self, code: str) -> "EmailOTP.VerificationResult":
        now = timezone.now()
        if self.is_used:
            return self.VerificationResult(False, "Code has already been used.")
        if now > self.expires_at:
            return self.VerificationResult(False, "Code has expired.")

        self.attempts += 1
        update_fields = ["attempts"]
        success = code == self.code

        if success:
            self.is_used = True
            update_fields.append("is_used")

        locked = self.attempts >= self.MAX_ATTEMPTS and not success
        self.save(update_fields=update_fields)

        if success:
            created_user = None
            with transaction.atomic():
                if self.user:
                    self.user.mark_email_verified()
                    created_user = self.user
                elif self.pending_signup:
                    pending = self.pending_signup
                    created_user = pending.create_user()
                    EmailOTP.objects.filter(pending_signup=pending).exclude(pk=self.pk).update(is_used=True)
                    pending.delete()
                if created_user:
                    EmailOTP.objects.filter(user=created_user).exclude(pk=self.pk).update(is_used=True)
            return self.VerificationResult(True, user=created_user)

        if locked:
            if self.pending_signup:
                pending = self.pending_signup
                EmailOTP.objects.filter(pending_signup=pending).delete()
                pending.delete()
            elif self.user and not self.user.is_verified:
                self.purge_user(self.user)
            return self.VerificationResult(False, "Too many attempts. Account removed for safety.", locked=True)
        return self.VerificationResult(False, "Invalid code. Please try again.")

    def __str__(self) -> str:
        target = self.user or self.pending_signup
        identifier = getattr(target, "email", None) or self.user_id or self.pending_signup_id
        return f"OTP for {identifier} ({self.purpose})"


class AccountDeletionRequest(models.Model):
    """
    Account deletion request with cooling-off period.
    
    Workflow:
    1. User schedules deletion → status=SCHEDULED, scheduled_for=now+14days
    2. User is immediately logged out and blocked from access
    3. User can cancel before scheduled_for → status=CANCELED
    4. Management command runs after scheduled_for → status=COMPLETED + soft-delete user
    """
    
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled for deletion'
        CANCELED = 'CANCELED', 'Canceled by user'
        COMPLETED = 'COMPLETED', 'Deletion completed'
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deletion_request',
        help_text="User account to be deleted"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(
        help_text="Date when deletion will be finalized (requested_at + 14 days)"
    )
    canceled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(
        blank=True,
        help_text="Optional reason for deletion provided by user"
    )
    confirmation_phrase = models.CharField(
        max_length=100,
        blank=True,
        help_text="Confirmation phrase entered by user"
    )
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    last_user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"Deletion request for {self.user.username} ({self.status})"
    
    def clean(self):
        """Validate scheduled_for is after requested_at."""
        if self.scheduled_for and self.requested_at:
            if self.scheduled_for < self.requested_at:
                raise ValidationError("scheduled_for must be >= requested_at")
    
    def days_remaining(self):
        """Calculate days remaining until deletion."""
        if self.status != self.Status.SCHEDULED:
            return None
        delta = self.scheduled_for - timezone.now()
        return max(0, delta.days)
    
    def is_cancellable(self):
        """Check if deletion can still be canceled."""
        return self.status == self.Status.SCHEDULED and timezone.now() < self.scheduled_for
