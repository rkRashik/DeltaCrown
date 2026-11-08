"""Bounded WebP derivatives for explicitly allowlisted public artwork (OL-07).

Originals are never changed or removed. A derivative is stored next to its original, in the *same* storage
the field already uses (so a private origin stays private), under a key that includes the record and a
version derived from the original's storage name (a re-upload gets a new name, hence new URLs). Delivery is
`/files/derived/...`, which re-runs the same record authorization as the original route.

Nothing here runs on page requests: derivatives are created by the explicit `generate_image_derivatives`
command or right after a new upload, and templates only emit derivative URLs when OWNLOBBY_PUBLIC_DERIVATIVES
is on. A missing derivative falls back to the original (redirect), never a broken image.
"""
import hashlib
import logging
import warnings
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image

from .policy import PUBLIC_FIELDS, storage_alias

log = logging.getLogger(__name__)

# Longest side in px; never upscaled, aspect ratio preserved.
VARIANTS = {"icon": 128, "thumb": 320, "card": 640, "hero": 1280}
# Exact reviewed list. Everything else (private, unclassified, brand artwork on the CDN) is refused.
ALLOWED = frozenset({
    ("games.game", "icon"), ("games.game", "logo"), ("games.game", "banner"), ("games.game", "card_image"),
    ("tournaments.tournament", "banner_image"), ("tournaments.tournament", "thumbnail_image"),
})
assert ALLOWED <= PUBLIC_FIELDS

# Explicit backfill command limits (one image at a time, run deliberately).
MAX_SOURCE_BYTES = 12 * 1024 * 1024
DEFAULT_MAX_PIXELS = 24_000_000  # ~100 MB decoded RGBA: safe on a 512 MB instance
# Upload-time limits are much tighter because that work runs inside the upload request on a small shared CPU;
# larger sources are left for the backfill command (status `too_large`).
UPLOAD_MAX_BYTES = 6 * 1024 * 1024
UPLOAD_MAX_PIXELS = 4_000_000  # e.g. 2560x1560
SOURCE_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}


def active():
    """Template emission and upload-time generation switch (default off)."""
    from .fields import enabled
    return enabled() and bool(getattr(settings, "OWNLOBBY_PUBLIC_DERIVATIVES", False))


def allowed(field):
    label = field.model._meta.concrete_model._meta.label_lower
    if (label, field.name) not in ALLOWED:
        return False
    # Hybrid mode publishes some artwork directly on a CDN; derivatives never touch that origin.
    return not (getattr(settings, "OWNLOBBY_MEDIA_MODE", "legacy") == "hybrid" and storage_alias(field) == "public_media")


def version(name):
    return hashlib.sha256(("v1:" + name).encode()).hexdigest()[:12]


def storage_key(label, field_name, pk, ver, variant):
    return f"derivatives/v1/{label}/{field_name}/{pk}/{ver}/{variant}.webp"


def _identity(blob):
    return blob.instance._meta.concrete_model._meta.label_lower, blob.field.name, blob.instance.pk


def url(blob, variant):
    label, field_name, pk = _identity(blob)
    return reverse("governed_media_derivative", args=[label, field_name, str(pk), variant, version(blob.name)])


def icon_url(blob):
    """URL for a small fixed-size logo/icon (<= 128 px wide): the icon derivative when enabled, else the original."""
    if active() and blob.instance.pk and allowed(blob.field):
        return url(blob, "icon")
    return blob.url


def generate(blob, max_pixels=None, max_bytes=None):
    """Create any missing derivatives for one FieldFile. Returns a status string, never raises for bad input.

    generated | exists | missing | unsupported | too_large | not_allowed | error
    """
    max_pixels = max_pixels or getattr(settings, "MEDIA_DERIVATIVE_MAX_PIXELS", DEFAULT_MAX_PIXELS)
    max_bytes = max_bytes or MAX_SOURCE_BYTES
    try:
        if not blob or not blob.instance.pk or not allowed(blob.field):
            return "not_allowed"
        storage, name = blob.storage, blob.name
        label, field_name, pk = _identity(blob)
        ver = version(name)
        keys = {v: storage_key(label, field_name, pk, ver, v) for v in VARIANTS}
        if not storage.exists(name):
            return "missing"
        todo = [v for v in VARIANTS if not storage.exists(keys[v])]
        if not todo:
            return "exists"
        size = storage.size(name)
        if size > max_bytes:
            return "too_large"
        with storage.open(name, "rb") as source:
            data = source.read(max_bytes + 1)
        if len(data) > max_bytes:
            return "too_large"
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                image = Image.open(BytesIO(data))
                if image.format not in SOURCE_FORMATS or getattr(image, "n_frames", 1) > 1:
                    return "unsupported"  # unknown format or animated: keep the original only
                if image.width * image.height > max_pixels:
                    return "too_large"
                if image.format == "JPEG":
                    image.draft("RGB", (VARIANTS["hero"], VARIANTS["hero"]))  # decode at reduced scale
                image.load()
            except (Image.DecompressionBombWarning, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
                return "unsupported"
        del data
        alpha = "A" in image.getbands() or "transparency" in image.info
        image = image.convert("RGBA" if alpha else "RGB")
        for variant in sorted(VARIANTS, key=VARIANTS.get, reverse=True):  # each step shrinks the previous one
            edge = VARIANTS[variant]
            image.thumbnail((edge, edge), Image.LANCZOS)
            if variant not in todo:
                continue
            out = BytesIO()
            image.save(out, "WEBP", quality=80, method=4)
            saved = storage.save(keys[variant], ContentFile(out.getvalue()))
            if saved != keys[variant]:  # a concurrent run won: keep its file, drop ours
                storage.delete(saved)
        return "generated"
    except Exception as exc:  # category only: never log content, names or exception text
        log.warning("media derivative generation failed (%s)", type(exc).__name__)
        return "error"


def generate_for_instance(instance, field_names):
    """Upload-time hook: bounded (tight size/pixel caps), and failure must never affect the upload."""
    max_pixels = getattr(settings, "MEDIA_DERIVATIVE_UPLOAD_MAX_PIXELS", UPLOAD_MAX_PIXELS)
    for name in field_names:
        try:
            if generate(getattr(instance, name), max_pixels=max_pixels, max_bytes=UPLOAD_MAX_BYTES) == "too_large":
                log.info("media derivative deferred to the backfill command (source above upload-time limits)")
        except Exception as exc:
            log.warning("media derivative generation failed (%s)", type(exc).__name__)


def note_upload(instance, field):
    """Remember which allowlisted fields received a new file; consumed by the post_save receiver."""
    if active() and allowed(field):
        instance.__dict__.setdefault("_media_derivative_fields", set()).add(field.name)
