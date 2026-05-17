"""Pre/post-save signals that track replaced/cleared game image fields.

When a Game or GameMapPool image field changes, the old Cloudinary file is
NOT auto-deleted. Instead we create a MediaCleanupCandidate row so the
cleanup service can delete it safely after the retention window has passed.

Safety rules enforced at tracking time:
  - Only track files from APPROVED_GAME_FOLDERS.
  - Never track files from BLOCKED_SUBSTRINGS paths.
  - Never track if the old file is still referenced by another DB row.
  - Never track empty file names.
"""

from __future__ import annotations

import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.games.models.game import Game
from apps.games.models.map_pool import GameMapPool
from apps.games.management.commands.audit_cloudinary_orphans import (
    APPROVED_GAME_FOLDERS,
    BLOCKED_SUBSTRINGS,
    _cloudinary_media_prefix,
)

logger = logging.getLogger(__name__)

_GAME_IMAGE_FIELDS = ("icon", "logo", "banner", "card_image")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_approved(file_name: str) -> bool:
    """Return True if file_name lives in an approved game-media folder."""
    if not file_name:
        return False
    name = file_name.strip().replace("\\", "/").lstrip("/")
    prefix = _cloudinary_media_prefix()
    if name.startswith(prefix):
        name = name[len(prefix):]
    name_lower = name.lower()
    return (
        any(name_lower.startswith(f) for f in APPROVED_GAME_FOLDERS)
        and not any(b in name_lower for b in BLOCKED_SUBSTRINGS)
    )


def _is_still_referenced(file_name: str, exclude_model: str, exclude_pk: int) -> bool:
    """Return True if the file_name is still referenced by any OTHER DB row."""
    from django.db.models import Q
    from apps.games.models.game import Game
    from apps.games.models.map_pool import GameMapPool

    # Normalise: check both with and without media/ prefix
    variants = {file_name}
    prefix = _cloudinary_media_prefix()
    if file_name.startswith(prefix):
        variants.add(file_name[len(prefix):])
    else:
        variants.add(prefix + file_name)

    # Check Game fields
    game_filter = Q()
    for f in _GAME_IMAGE_FIELDS:
        game_filter |= Q(**{f"{ f }__in": variants})
    if exclude_model == "games.Game":
        game_qs = Game.objects.filter(game_filter).exclude(pk=exclude_pk)
    else:
        game_qs = Game.objects.filter(game_filter)
    if game_qs.exists():
        return True

    # Check GameMapPool
    if exclude_model == "games.GameMapPool":
        mp_qs = GameMapPool.objects.filter(image__in=variants).exclude(pk=exclude_pk)
    else:
        mp_qs = GameMapPool.objects.filter(image__in=variants)
    return mp_qs.exists()


def _field_name(field_obj) -> str:
    return str(getattr(field_obj, "name", "") or "").strip()


def _storage_type() -> str:
    try:
        from django.core.files.storage import default_storage
        backend = type(default_storage).__name__
        return "cloudinary" if "Cloudinary" in backend else "local"
    except Exception:
        return "cloudinary"


def _create_candidate(
    file_name: str,
    source_model: str,
    source_pk: int,
    field_name: str,
    reason: str,
    metadata: dict,
) -> None:
    if not _is_approved(file_name):
        return
    if _is_still_referenced(file_name, source_model, source_pk):
        logger.debug(
            "media_cleanup: skipping candidate for %s — still referenced elsewhere",
            file_name,
        )
        return
    try:
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        candidate = MediaCleanupCandidate.create_for_field(
            file_name=file_name,
            source_model=source_model,
            source_object_id=source_pk,
            source_field=field_name,
            reason=reason,
            storage_type=_storage_type(),
            metadata=metadata,
        )
        if candidate:
            logger.info(
                "media_cleanup: created candidate id=%s for %s on %s.%s (reason=%s)",
                candidate.pk, file_name, source_model, field_name, reason,
            )
    except Exception:
        logger.exception("media_cleanup: failed to create candidate for %s", file_name)


# ---------------------------------------------------------------------------
# Game signals
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=Game, dispatch_uid="media_cleanup:game_pre_save")
def _game_pre_save(sender, instance: Game, **kwargs):
    """Snapshot old image field values before the Game row is written."""
    if not instance.pk:
        return
    try:
        old = Game.objects.only(*_GAME_IMAGE_FIELDS).get(pk=instance.pk)
    except Game.DoesNotExist:
        return
    for f in _GAME_IMAGE_FIELDS:
        setattr(instance, f"_old_{f}", _field_name(getattr(old, f, None)))


@receiver(post_save, sender=Game, dispatch_uid="media_cleanup:game_post_save")
def _game_post_save(sender, instance: Game, created: bool, **kwargs):
    """After save: queue cleanup for any image field whose value changed."""
    if created:
        return
    for f in _GAME_IMAGE_FIELDS:
        old_name = getattr(instance, f"_old_{f}", None)
        if old_name is None:
            continue
        new_name = _field_name(getattr(instance, f, None))
        if old_name == new_name or not old_name:
            continue
        reason = (
            "cleared" if not new_name else "replaced"
        )
        _create_candidate(
            file_name=old_name,
            source_model="games.Game",
            source_pk=instance.pk,
            field_name=f,
            reason=reason,
            metadata={
                "game_name": instance.name,
                "game_slug": instance.slug,
                "old_file": old_name,
                "new_file": new_name,
            },
        )


# ---------------------------------------------------------------------------
# GameMapPool signals
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=GameMapPool, dispatch_uid="media_cleanup:mappool_pre_save")
def _mappool_pre_save(sender, instance: GameMapPool, **kwargs):
    """Snapshot old image value before GameMapPool row is written."""
    if not instance.pk:
        return
    try:
        old = GameMapPool.objects.only("image").get(pk=instance.pk)
    except GameMapPool.DoesNotExist:
        return
    instance._old_image = _field_name(old.image)


@receiver(post_save, sender=GameMapPool, dispatch_uid="media_cleanup:mappool_post_save")
def _mappool_post_save(sender, instance: GameMapPool, created: bool, **kwargs):
    """After save: queue cleanup for a replaced/cleared map image."""
    if created:
        return
    old_name = getattr(instance, "_old_image", None)
    if old_name is None:
        return
    new_name = _field_name(instance.image)
    if old_name == new_name or not old_name:
        return
    reason = "cleared" if not new_name else "replaced"
    _create_candidate(
        file_name=old_name,
        source_model="games.GameMapPool",
        source_pk=instance.pk,
        field_name="image",
        reason=reason,
        metadata={
            "map_name": instance.map_name,
            "map_code": instance.map_code,
            "old_file": old_name,
            "new_file": new_name,
        },
    )
