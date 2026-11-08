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

from .policy import CLOUDINARY_PUBLIC_FIELDS, PUBLIC_FIELDS, storage_alias

log = logging.getLogger(__name__)

# Longest side in px; never upscaled, aspect ratio preserved. `large` exists because phones (390 css px at 2x)
# otherwise fall through to `hero`: on real game artwork 960 px is ~40% smaller than 1280 px (measured).
VARIANTS = {"icon": 128, "thumb": 320, "card": 640, "large": 960, "hero": 1280}

# Three separate questions, never conflated:
#   eligible   - this field may have derivatives at all (membership in POLICY, a subset of PUBLIC_FIELDS)
#   authorized - a given viewer may fetch it: the derivative route re-runs policy.can_download on the record,
#                exactly as the original route does
#   cacheable  - what the browser may keep. Nothing here is ever `public`.
# STABLE:     public-intended artwork whose record is rarely revoked: private 15-minute cache + ETag.
# REVALIDATE: visibility/privacy dependent (drafts, teams, profiles): private, no-cache + ETag, so the
#             authorization check runs on every request and a 304 costs no bytes.
STABLE, REVALIDATE = "stable", "revalidate"
POLICY = {
    **{("games.game", f): STABLE for f in ("icon", "logo", "banner", "card_image")},
    **{("ecommerce.brand", "logo"): STABLE, ("ecommerce.category", "image"): STABLE,
       ("ecommerce.product", "featured_image"): STABLE, ("ecommerce.product", "hover_image"): STABLE,
       ("ecommerce.productimage", "image"): STABLE},
    **{("organizations.organization", f): STABLE for f in ("logo", "banner", "badge")},
    **{("organizations.team", f): REVALIDATE for f in ("logo", "banner")},
    **{("tournaments.tournament", f): REVALIDATE for f in ("banner_image", "thumbnail_image")},
    **{("tournaments.tournamentsponsor", f): REVALIDATE for f in ("logo", "banner_image")},
    **{("user_profile.userprofile", f): REVALIDATE for f in ("avatar", "banner")},
}
ALLOWED = frozenset(POLICY)
assert ALLOWED <= PUBLIC_FIELDS  # fail closed: private/unclassified fields can never be added by accident
CACHE_CONTROL = {STABLE: "private, max-age=900, must-revalidate", REVALIDATE: "private, no-cache"}

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


def cache_control_for(label, field_name):
    return CACHE_CONTROL[POLICY[(label, field_name)]]


def cache_control(field):
    return cache_control_for(field.model._meta.concrete_model._meta.label_lower, field.name)


def version(name):
    return hashlib.sha256(("v1:" + name).encode()).hexdigest()[:12]


def storage_key(label, field_name, pk, ver, variant):
    return f"derivatives/v1/{label}/{field_name}/{pk}/{ver}/{variant}.webp"


def _identity(blob):
    return blob.instance._meta.concrete_model._meta.label_lower, blob.field.name, blob.instance.pk


def url(blob, variant):
    label, field_name, pk = _identity(blob)
    return reverse("governed_media_derivative", args=[label, field_name, str(pk), variant, version(blob.name)])


def variant_url(blob, variant):
    """Best URL for one variant, decided centrally: verified public CDN copy, else authorized derivative, else the original."""
    try:
        from . import cdn
        hit = cdn.url(blob, variant)
        if hit:
            return hit
        if active() and blob.instance.pk and allowed(blob.field):
            return url(blob, variant)
    except AttributeError:  # not a governed FieldFile: leave it exactly as it was
        pass
    return blob.url


def icon_url(blob):
    """Small fixed-size logo/icon (<= 128 px wide)."""
    return variant_url(blob, "icon")


def cdn_allowed(blob):
    """Hybrid-mode brand artwork published directly on the CDN (no Django route, so no derivative files)."""
    try:
        return (getattr(settings, "OWNLOBBY_CLOUDINARY_TRANSFORMS", False)
                and getattr(settings, "OWNLOBBY_MEDIA_MODE", "legacy") == "hybrid"
                and (blob.instance._meta.concrete_model._meta.label_lower, blob.field.name) in CLOUDINARY_PUBLIC_FIELDS)
    except AttributeError:
        return False


def cdn_url(blob, variant):
    """Cloudinary on-the-fly resize (no upscale, auto format/quality) of the already-public original."""
    original = blob.url
    marker = "/image/upload/"
    if marker not in original or "res.cloudinary.com" not in original:
        return original
    return original.replace(marker, f"{marker}c_limit,w_{VARIANTS[variant]},f_auto,q_auto/", 1)


def load(blob, max_pixels, max_bytes):
    """Decode a source image within the size/pixel caps: (None, PIL image) or (status, None). Never raises for bad input."""
    storage, name = blob.storage, blob.name
    if storage.size(name) > max_bytes:
        return "too_large", None
    with storage.open(name, "rb") as source:
        data = source.read(max_bytes + 1)
    if len(data) > max_bytes:
        return "too_large", None
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            image = Image.open(BytesIO(data))
            if image.format not in SOURCE_FORMATS or getattr(image, "n_frames", 1) > 1:
                return "unsupported", None  # unknown format or animated: keep the original only
            if image.width * image.height > max_pixels:
                return "too_large", None
            if image.format == "JPEG":
                image.draft("RGB", (VARIANTS["hero"], VARIANTS["hero"]))  # decode at reduced scale
            image.load()
        except (Image.DecompressionBombWarning, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
            return "unsupported", None
    return None, image


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
        status, image = load(blob, max_pixels, max_bytes)
        if status:
            return status
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
