"""
Symmetric-encrypted model field using Fernet (AES-128-CBC + HMAC-SHA256).

Reads FIELD_ENCRYPTION_KEY from settings (base64-encoded 32-byte key).
Falls back to deriving a key from SECRET_KEY if FIELD_ENCRYPTION_KEY is not set.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key."""
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        # Derive a stable 32-byte key from SECRET_KEY
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """TextField that encrypts values at rest using Fernet."""

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        f = _get_fernet()
        return f.encrypt(value.encode()).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        f = _get_fernet()
        try:
            return f.decrypt(value.encode()).decode("utf-8")
        except InvalidToken:
            # Value is still plaintext (pre-migration data)
            return value
