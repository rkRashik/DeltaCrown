"""Signed URL helpers for tournament evidence downloads."""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac


def _build_signature(scope: str, identifier: int, expires_ts: int) -> str:
    payload = f"{scope}:{int(identifier)}:{int(expires_ts)}"
    return salted_hmac("tournaments.signed_urls", payload, secret=settings.SECRET_KEY).hexdigest()


def evidence_signed_url(evidence_id: int, ttl_seconds: int = 600, request=None) -> str:
    """Return a signed URL for downloading evidence files."""

    expires_ts = int((timezone.now() + timedelta(seconds=ttl_seconds)).timestamp())
    signature = _build_signature("evidence", evidence_id, expires_ts)
    path = reverse("tournaments:evidence_download", args=[evidence_id])
    url = f"{path}?exp={expires_ts}&sig={signature}"
    if request is not None and hasattr(request, "build_absolute_uri"):
        return request.build_absolute_uri(url)
    return url


def verify_signature(scope: str, identifier: int, expires_ts: int, signature: str) -> bool:
    """Validate a signature and ensure it hasn't expired."""

    if timezone.now().timestamp() > int(expires_ts):
        return False
    expected = _build_signature(scope, identifier, int(expires_ts))
    try:
        return secrets.compare_digest(expected, str(signature))
    except Exception:
        return False
