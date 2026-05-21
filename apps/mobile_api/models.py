"""Models owned by the mobile API."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class MobileDeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_device_tokens",
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    device_id = models.CharField(max_length=128, blank=True, db_index=True)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["platform", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.platform}:{self.device_id or self.pk}"
