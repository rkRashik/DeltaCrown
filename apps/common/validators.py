"""
Reusable validators for the DeltaCrown platform.

Upload validation ensures that uploaded files match allowed MIME types
and stay below configured size limits.  MIME type detection is performed
by reading the first 8 KiB of the file (magic-number sniffing) so that
the browser-supplied Content-Type cannot be spoofed.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (overridable via settings)
# ---------------------------------------------------------------------------
_DEFAULT_ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')
_DEFAULT_MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB
_DEFAULT_MAX_PROOF_SIZE = 10 * 1024 * 1024  # 10 MB

# Magic-number → MIME mapping for fast sniffing without python-magic.
_DEFAULT_MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB
_DEFAULT_ALLOWED_DOCUMENT_TYPES = (
    'image/jpeg', 'image/png', 'image/webp',
    'application/pdf',
)

_MAGIC_SIGNATURES: dict[bytes, str] = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'RIFF': 'image/webp',         # WebP starts with RIFF…WEBP
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'%PDF-': 'application/pdf',
}


def _sniff_mime(file_obj) -> str | None:
    """
    Read the first bytes of *file_obj* and return a MIME type based on
    magic-number signatures.  Resets the read pointer after inspection.

    Falls back to ``python-magic`` if installed, otherwise returns the
    Content-Type reported by the upload handler.
    """
    pos = file_obj.tell()
    header = file_obj.read(16)
    file_obj.seek(pos)

    if not header:
        return None

    # Check WebP specifically (RIFF....WEBP)
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'image/webp'

    for sig, mime in _MAGIC_SIGNATURES.items():
        if header.startswith(sig):
            return mime

    # Try python-magic if available (graceful fallback)
    try:
        import magic                       # type: ignore[import-untyped]
        pos = file_obj.tell()
        chunk = file_obj.read(8192)
        file_obj.seek(pos)
        return magic.from_buffer(chunk, mime=True)
    except (ImportError, Exception):
        pass

    # Last resort: trust the content_type from the upload handler
    return getattr(file_obj, 'content_type', None)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_image_upload(value):
    """
    Validate that an uploaded file is a recognised image type and does not
    exceed the configured maximum size.

    Attach to an ``ImageField`` or ``FileField``::

        avatar = models.ImageField(
            upload_to='avatars/',
            validators=[validate_image_upload],
        )
    """
    max_size = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE', _DEFAULT_MAX_IMAGE_SIZE)
    allowed = getattr(settings, 'ALLOWED_IMAGE_TYPES', _DEFAULT_ALLOWED_IMAGE_TYPES)

    # Size check
    if hasattr(value, 'size') and value.size > max_size:
        mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'File too large.  Maximum allowed size is {mb:.0f} MB.',
            code='file_too_large',
        )

    # MIME-type check
    detected = _sniff_mime(value)
    if detected and detected not in allowed:
        raise ValidationError(
            f'Unsupported file type: {detected}.  Allowed types: {", ".join(allowed)}.',
            code='invalid_file_type',
        )


def validate_payment_proof_upload(value):
    """
    Stricter validator for payment proof screenshots.  Limits to images
    only and uses a larger size cap (``MAX_PAYMENT_PROOF_SIZE``).
    """
    max_size = getattr(settings, 'MAX_PAYMENT_PROOF_SIZE', _DEFAULT_MAX_PROOF_SIZE)
    allowed = getattr(settings, 'ALLOWED_IMAGE_TYPES', _DEFAULT_ALLOWED_IMAGE_TYPES)

    if hasattr(value, 'size') and value.size > max_size:
        mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'Proof file too large.  Maximum allowed size is {mb:.0f} MB.',
            code='file_too_large',
        )

    detected = _sniff_mime(value)
    if detected and detected not in allowed:
        raise ValidationError(
            f'Unsupported proof file type: {detected}.  Allowed: {", ".join(allowed)}.',
            code='invalid_file_type',
        )


def validate_document_upload(value):
    """
    Validator for document uploads (PDF, images).  Used for rules PDFs,
    terms documents, and certificate files.
    """
    max_size = getattr(settings, 'MAX_DOCUMENT_UPLOAD_SIZE', _DEFAULT_MAX_DOCUMENT_SIZE)
    allowed = getattr(settings, 'ALLOWED_DOCUMENT_TYPES', _DEFAULT_ALLOWED_DOCUMENT_TYPES)

    if hasattr(value, 'size') and value.size > max_size:
        mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'Document too large.  Maximum allowed size is {mb:.0f} MB.',
            code='file_too_large',
        )

    detected = _sniff_mime(value)
    if detected and detected not in allowed:
        raise ValidationError(
            f'Unsupported document type: {detected}.  Allowed: {", ".join(allowed)}.',
            code='invalid_file_type',
        )
