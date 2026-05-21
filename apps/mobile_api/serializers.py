"""Serializers for /api/mobile/v1/ chassis endpoints."""
from __future__ import annotations

from typing import Optional

from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    service = serializers.CharField()
    version = serializers.CharField()
    status = serializers.CharField()


def _completion_percentage(profile) -> int:
    if profile is None:
        return 0
    try:
        from apps.user_profile.services.completion_service import (
            SettingsCompletionService,
        )
        data = SettingsCompletionService.calculate(profile) or {}
        return max(0, min(100, int(data.get("percentage", 0))))
    except Exception:
        return 0


def serialize_mobile_profile(profile) -> dict:
    """Compact profile dict used by /me/. Safe for ``profile=None``."""
    country = getattr(profile, "country", None)
    country_code: Optional[str] = None
    if country:
        country_code = getattr(country, "code", None) or (str(country) or None)

    pct = _completion_percentage(profile)
    return {
        "display_name": getattr(profile, "display_name", None) or None,
        "public_id": getattr(profile, "public_id", None) or None,
        "country": country_code,
        "region": getattr(profile, "region", None) or None,
        "profile_completed": pct >= 100,
        "completion_percentage": pct,
    }


class MobileMeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    profile = serializers.SerializerMethodField()

    def get_profile(self, user) -> dict:
        return serialize_mobile_profile(getattr(user, "profile", None))
