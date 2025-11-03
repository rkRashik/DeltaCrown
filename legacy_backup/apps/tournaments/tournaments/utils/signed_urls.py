"""Signed URL helpers for evidence downloads and similar flows."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.urls import reverse
from django.utils import timezone


@dataclass(frozen=True)
class SignatureData:
    kind: str
    obj_id: int
    expires: int

    def payload(self) -> str:
        return f"{self.kind}:{self.obj_id}:{self.expires}"


def _secret() -> bytes:
    key = getattr(settings, "SIGNED_URL_SECRET", None) or settings.SECRET_KEY
    if not isinstance(key, bytes):
        key = key.encode("utf-8")
    return key


def _make_signature(data: SignatureData) -> str:
    digest = hmac.new(_secret(), data.payload().encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def _normalize_ttl(ttl_seconds: Optional[int]) -> int:
    try:
        ttl = int(ttl_seconds) if ttl_seconds is not None else 300
    except Exception:
        ttl = 300
    return max(ttl, 1)


def evidence_signed_url(evidence_id: int, ttl_seconds: Optional[int] = None, request=None) -> str:
    """Return a signed download URL for a match evidence attachment."""
    ttl = _normalize_ttl(ttl_seconds)
    expires = int(time.time()) + ttl
    data = SignatureData("evidence", int(evidence_id), expires)
    sig = _make_signature(data)
    path = reverse("tournaments:evidence_download", args=[evidence_id])
    query = f"exp={expires}&sig={sig}"
    if request is not None:
        base = request.build_absolute_uri(path)
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}{query}"
    return f"{path}?{query}"


def verify_signature(kind: str, obj_id: int, expires: int, signature: str, leeway: int = 30) -> bool:
    """Validate the provided signature and expiry timestamp."""
    try:
        expires = int(expires)
        obj_id = int(obj_id)
    except (TypeError, ValueError):
        return False

    if not signature:
        return False

    data = SignatureData(kind, obj_id, expires)
    expected = _make_signature(data)
    if not hmac.compare_digest(expected, str(signature)):
        return False

    now = int(timezone.now().timestamp())
    if expires + leeway < now:
        return False
    if expires - leeway > now + 7 * 24 * 60 * 60:
        return False
    return True
