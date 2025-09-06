# apps/corelib/models/idempotency.py
from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class IdempotencyKey(models.Model):
    """
    Stores short-lived unique tokens to prevent duplicate POST submissions.
    Scope is a free-form string (e.g., "tournaments.registration.solo").
    We can GC old rows with a periodic job (or rely on created_at TTL logic in queries).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="idempotency_keys")
    scope = models.CharField(max_length=100, db_index=True)
    token = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "scope", "token"]),
        ]
        constraints = [
            # Avoid exact duplicates (user, scope, token)
            models.UniqueConstraint(fields=["user", "scope", "token"], name="uq_idem_user_scope_token"),
        ]

    @staticmethod
    def issue(user, scope: str) -> "IdempotencyKey":
        return IdempotencyKey.objects.create(user=user, scope=scope, token=secrets.token_urlsafe(24))

    @staticmethod
    def is_recently_used(user, scope: str, token: str, window_minutes: int = 10) -> bool:
        cutoff = timezone.now() - timedelta(minutes=window_minutes)
        return IdempotencyKey.objects.filter(
            user=user, scope=scope, token=token, created_at__gte=cutoff
        ).exists()
