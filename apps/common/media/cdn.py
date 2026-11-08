"""Public Cloudinary CDN delivery and bounded publication for a *strictly* approved set of artwork (OL-08).

Three separate questions, never conflated (see also derivatives.py):
  derivative eligibility  - derivatives.ALLOWED: the image may be resized
  viewer authorization    - policy.can_download on the record (Django routes)
  public CDN eligibility  - PUBLISHABLE below: permanent public Internet delivery is acceptable

A CDN copy cannot be revoked by flipping a database flag, so only artwork whose disclosure is acceptable even
after deactivation is listed: game, brand and category artwork. Everything with dynamic visibility (teams,
profiles, drafts, shop products, community media, KYC/evidence/payments) stays on the authorized Django route.

Delivery never replaces the stored original: a verified `PublishedMedia` row maps (record, field, source version)
to an immutable Cloudinary public id. A CDN URL is emitted only when the flag is on, the record is still publicly
visible, and the row matches the current original; in every other case callers fall back to their existing URL.
Nothing here runs a provider call on a page request.
"""
import hashlib
import logging
import time
from io import BytesIO

import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
import cloudinary.utils
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from PIL import Image

from . import derivatives
from .policy import can_download

log = logging.getLogger(__name__)

# Exact reviewed list; deliberately smaller than derivatives.ALLOWED and never inferred from PUBLIC_FIELDS.
PUBLISHABLE = frozenset({
    *{("games.game", f) for f in ("icon", "logo", "banner", "card_image")},
    ("ecommerce.brand", "logo"), ("ecommerce.category", "image"),
})
assert PUBLISHABLE <= derivatives.ALLOWED

NAMESPACE = "ownlobby-public/v1"  # never collides with legacy Cloudinary ids (those live under media/ or other folders)
TAG = "ownlobby-public-v1"
MASTER_EDGE = derivatives.VARIANTS["hero"]  # the published master is the 1280 px WebP; nothing larger is stored
ATTEMPTS, STOP_AFTER_ERRORS = 3, 3
HIT_TTL, MISS_TTL = 300, 60
_sleep = time.sleep  # patched in tests


def _label(field):
    return field.model._meta.concrete_model._meta.label_lower


def eligible(field):
    return (_label(field), field.name) in PUBLISHABLE


def configured():
    return bool(cloudinary.config().cloud_name)


def active():
    """Delivery switch (default off): needs governed media and a configured cloud name."""
    from .fields import enabled
    return bool(getattr(settings, "OWNLOBBY_PUBLIC_CDN", False)) and enabled() and configured()


def public_id(label, field_name, pk, ver):
    return f"{NAMESPACE}/{label}/{field_name}/{pk}/{ver}"


def _key(label, field_name, pk, ver):
    return "ownlobby:cdn:v1:" + hashlib.sha1(f"{label}/{field_name}/{pk}/{ver}".encode()).hexdigest()


def forget(label, field_name, pk, ver):
    try:
        cache.delete(_key(label, field_name, pk, ver))
    except Exception:  # cache outage must never break publication
        pass


def _mapping(label, field_name, pk, ver):
    """(public_id, cdn_version) of a ready mapping or None, cached briefly (one query per image otherwise)."""
    key = _key(label, field_name, pk, ver)
    try:
        hit = cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return hit or None
    from apps.common.models import PublishedMedia
    row = PublishedMedia.objects.filter(label=label, field_name=field_name, object_pk=str(pk), source_version=ver,
                                        status=PublishedMedia.READY).values_list("public_id", "cdn_version").first()
    try:
        cache.set(key, row or False, HIT_TTL if row else MISS_TTL)
    except Exception:
        pass
    return row


def build(pid, cdn_version, variant):
    """Optimized responsive URL. `c_limit` never upscales; the width set is the five curated variants only."""
    url, _ = cloudinary.utils.cloudinary_url(
        pid, secure=True, type="upload", resource_type="image", version=cdn_version,
        transformation=[{"crop": "limit", "width": derivatives.VARIANTS[variant], "fetch_format": "auto", "quality": "auto"}])
    return url


def url(blob, variant):
    """CDN URL for a verified, currently public, unchanged original; otherwise None (caller falls back). Never raises."""
    try:
        if variant not in derivatives.VARIANTS or not active() or not blob or not blob.instance.pk or not eligible(blob.field):
            return None
        instance, name = blob.instance, blob.field.name
        if not can_download(AnonymousUser(), instance, name):  # deactivated/deleted records stop using the CDN copy
            return None
        label = _label(blob.field)
        row = _mapping(label, name, instance.pk, derivatives.version(blob.name))
        return build(row[0], row[1], variant) if row else None
    except AttributeError:
        return None  # not a governed FieldFile
    except Exception as exc:  # category only
        log.warning("cdn url failed (%s)", type(exc).__name__)
        return None


class Stop(Exception):
    """Operator-facing stop condition: the batch ends instead of continuing against a misbehaving provider."""


def _master(blob, max_pixels, max_bytes):
    status, image = derivatives.load(blob, max_pixels, max_bytes)
    if status:
        return status, None
    alpha = "A" in image.getbands() or "transparency" in image.info
    image = image.convert("RGBA" if alpha else "RGB")
    image.thumbnail((MASTER_EDGE, MASTER_EDGE), Image.LANCZOS)
    out = BytesIO()
    image.save(out, "WEBP", quality=85, method=4)  # re-encoded: no EXIF/metadata from the original is published
    return None, out.getvalue()


def _upload(pid, data):
    last = None
    for attempt in range(ATTEMPTS):
        try:
            return cloudinary.uploader.upload(
                BytesIO(data), public_id=pid, type="upload", resource_type="image", overwrite=False,
                unique_filename=False, use_filename=False, invalidate=False, tags=[TAG], access_mode="public")
        except cloudinary.exceptions.RateLimited:
            raise Stop("rate limited by the provider")
        except (cloudinary.exceptions.AuthorizationRequired, cloudinary.exceptions.NotAllowed):
            raise Stop("provider refused the credentials or the operation")
        except (cloudinary.exceptions.Error, OSError) as exc:
            last = exc
            if attempt + 1 < ATTEMPTS:
                _sleep(2 ** attempt)  # bounded backoff: 1 s, 2 s
    log.warning("cdn upload failed (%s)", type(last).__name__)
    return None


def publish(blob, max_pixels=None, max_bytes=None):
    """Publish one FieldFile. Status: uploaded | already_present | unsupported | skipped | failed. Raises Stop only."""
    from apps.common.models import PublishedMedia
    max_pixels = max_pixels or getattr(settings, "MEDIA_DERIVATIVE_MAX_PIXELS", derivatives.DEFAULT_MAX_PIXELS)
    max_bytes = max_bytes or derivatives.MAX_SOURCE_BYTES
    try:
        if not blob or not blob.instance.pk or not eligible(blob.field):
            return "skipped"
        instance, field = blob.instance, blob.field
        label, pk, ver = _label(field), instance.pk, derivatives.version(blob.name)
        if not can_download(AnonymousUser(), instance, field.name):
            return "skipped"  # inactive/deleted: never publish
        if PublishedMedia.objects.filter(label=label, field_name=field.name, object_pk=str(pk), source_version=ver,
                                         status=PublishedMedia.READY).exists():
            return "already_present"
        if not blob.storage.exists(blob.name):
            return "skipped"
        status, data = _master(blob, max_pixels, max_bytes)
        if status:
            return "skipped" if status == "too_large" else status
        pid = public_id(label, field.name, pk, ver)
        response = _upload(pid, data)
        if response is None:
            return "failed"
        if response.get("public_id") != pid or response.get("type") != "upload" or response.get("access_mode", "public") != "public":
            raise Stop("provider returned an unexpected asset identity or visibility")
        fresh = type(instance)._base_manager.filter(pk=pk).values_list(field.name, flat=True).first()
        if fresh != blob.name:
            raise Stop("source changed during publication")  # asset id is version-keyed, so it stays unused
        for needed in ("version", "width", "height", "bytes"):
            if not isinstance(response.get(needed), int):
                raise Stop("provider response could not be verified")
        PublishedMedia.objects.update_or_create(
            label=label, field_name=field.name, object_pk=str(pk), source_version=ver,
            defaults={"public_id": pid, "cdn_version": response["version"], "width": response["width"],
                      "height": response["height"], "size_bytes": response["bytes"], "status": PublishedMedia.READY})
        forget(label, field.name, pk, ver)
        return "already_present" if response.get("existing") else "uploaded"
    except Stop:
        raise
    except Exception as exc:  # category only: never log names, urls or provider text
        log.warning("cdn publication failed (%s)", type(exc).__name__)
        return "failed"
