"""
Symmetric-encrypted model field using Fernet (AES-128-CBC + HMAC-SHA256).

Key selection (the stored format is plain Fernet and has not changed):
  * ``FIELD_ENCRYPTION_KEY`` (Fernet key) is the primary key and the only key used to encrypt.
    If it is unset, the primary key is derived from ``SECRET_KEY`` exactly as before, so existing
    deployments keep working unchanged.
  * ``FIELD_ENCRYPTION_LEGACY_SECRET_KEYS`` (old ``SECRET_KEY`` values) and
    ``FIELD_ENCRYPTION_LEGACY_KEYS`` (old Fernet keys) are decrypt-only. They exist so a signing-key
    or encryption-key rotation does not strand rows written under the old key. Remove them once
    ``reencrypt_oauth_tokens`` reports no legacy rows.

Safety properties:
  * Only configured keys are ever tried; ciphertext is never "decrypted" with an unrelated key.
  * A value that looks like Fernet ciphertext but cannot be decrypted is NOT returned as if it were
    a token and is NOT re-encrypted on the next save; it reads as an empty value and the stored
    ciphertext is written back untouched (recoverable after a rollback or key fix).
  * Pre-encryption plaintext rows still read as plaintext and are encrypted on the next save.
  * Errors and log lines never contain key material or token values.
"""

import base64
import binascii
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger(__name__)

# Fernet tokens: 1 version byte (0x80) + 8 timestamp + 16 IV + >=16 ciphertext + 32 HMAC.
_FERNET_VERSION = 0x80
_FERNET_MIN_BYTES = 73


def derive_key_from_secret(secret: str) -> bytes:
    """The historical derivation: SHA-256 of the Django SECRET_KEY, urlsafe-base64 encoded."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def _build_fernet(key, label: str) -> Fernet:
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError):
        # Never echo the value: it is key material.
        raise ImproperlyConfigured(
            f"{label} is not a valid Fernet key (32 url-safe base64-encoded bytes)."
        ) from None


def _as_list(name: str):
    value = getattr(settings, name, None) or []
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ImproperlyConfigured(f"{name} must be a list of strings.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ImproperlyConfigured(f"{name} must contain only non-empty strings.")
    return list(value)


def _fernets():
    """Return (primary Fernet, [decrypt-only Fernets]) from the current settings."""
    primary_key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if primary_key:
        primary = _build_fernet(primary_key, "FIELD_ENCRYPTION_KEY")
    else:
        primary = Fernet(derive_key_from_secret(settings.SECRET_KEY))
    legacy = [Fernet(derive_key_from_secret(secret)) for secret in _as_list("FIELD_ENCRYPTION_LEGACY_SECRET_KEYS")]
    legacy += [
        _build_fernet(key, "FIELD_ENCRYPTION_LEGACY_KEYS entry")
        for key in _as_list("FIELD_ENCRYPTION_LEGACY_KEYS")
    ]
    return primary, legacy


def _get_fernet() -> MultiFernet:
    """Encrypts with the primary key; decrypts with the primary key, then the legacy keys."""
    primary, legacy = _fernets()
    return MultiFernet([primary, *legacy])


def looks_like_fernet_token(value: str) -> bool:
    """True when ``value`` has the shape of a Fernet token (so a failed decrypt is not plaintext)."""
    try:
        raw = base64.urlsafe_b64decode(value.encode())
    except (binascii.Error, ValueError, UnicodeEncodeError):
        return False
    return len(raw) >= _FERNET_MIN_BYTES and raw[0] == _FERNET_VERSION


def classify_stored_value(value) -> str:
    """Status-only classification used by the maintenance command: never returns the value.

    One of: empty, primary, legacy, plaintext, undecryptable.
    """
    if value in (None, ""):
        return "empty"
    primary, legacy = _fernets()
    text = value if isinstance(value, str) else str(value)
    try:
        primary.decrypt(text.encode())
        return "primary"
    except InvalidToken:
        pass
    for fernet in legacy:
        try:
            fernet.decrypt(text.encode())
            return "legacy"
        except InvalidToken:
            continue
    return "undecryptable" if looks_like_fernet_token(text) else "plaintext"


class UndecryptableToken(str):
    """Empty value standing in for ciphertext that no configured key can decrypt.

    It is falsy so callers treat the credential as missing (and reconnect/refresh), while
    ``ciphertext`` lets the field write the original bytes back unchanged on save.
    """

    ciphertext = ""

    def __new__(cls, ciphertext: str):
        obj = super().__new__(cls, "")
        obj.ciphertext = ciphertext
        return obj

    def __repr__(self):  # never expose the stored ciphertext in logs/reprs
        return "<UndecryptableToken>"


class EncryptedTextField(models.TextField):
    """TextField that encrypts values at rest using Fernet (see module docstring)."""

    def get_prep_value(self, value):
        if isinstance(value, UndecryptableToken):
            return value.ciphertext  # write the stored bytes back untouched; never double-encrypt
        if value in (None, ""):
            return value
        return _get_fernet().encrypt(str(value).encode()).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode("utf-8")
        except InvalidToken:
            if looks_like_fernet_token(value):
                logger.warning(
                    "A %s value could not be decrypted with the configured keys; treating it as missing.",
                    self.__class__.__name__,
                )
                return UndecryptableToken(value)
            return value  # pre-encryption plaintext; encrypted on the next save
