"""Helpers for per-user unread notification count caching."""

from django.apps import apps
from django.conf import settings
from django.core.cache import cache


def _cache_ttl_seconds() -> int:
    """Return bounded TTL for unread count cache."""
    try:
        ttl = int(getattr(settings, "NOTIFICATIONS_UNREAD_CACHE_TTL", 15))
    except (TypeError, ValueError):
        ttl = 15
    return max(0, ttl)


def _key_for_user_id(user_id: int) -> str:
    return f"notifications:unread_count:user:{user_id}"


def _normalize_user_id(user_or_id):
    if user_or_id is None:
        return None

    if isinstance(user_or_id, int):
        return user_or_id if user_or_id > 0 else None

    user_id = getattr(user_or_id, "id", None)
    if isinstance(user_id, int) and user_id > 0:
        return user_id
    return None


def get_unread_count_for_user(user, *, use_cache: bool = True) -> int:
    """Return unread notification count with optional short-lived cache."""
    if not user or not getattr(user, "is_authenticated", False):
        return 0

    user_id = _normalize_user_id(user)
    if not user_id:
        return 0

    ttl = _cache_ttl_seconds()
    cache_key = _key_for_user_id(user_id)

    if use_cache and ttl > 0:
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached is not None:
            try:
                return max(0, int(cached))
            except (TypeError, ValueError):
                pass

    Notification = apps.get_model("notifications", "Notification")
    count = Notification.objects.filter(recipient=user, is_read=False).count()
    count = max(0, int(count))

    if use_cache and ttl > 0:
        try:
            cache.set(cache_key, count, ttl)
        except Exception:
            pass

    return count


def invalidate_unread_count_for_user(user_or_id) -> None:
    """Clear cached unread count for a user."""
    user_id = _normalize_user_id(user_or_id)
    if not user_id:
        return

    try:
        cache.delete(_key_for_user_id(user_id))
    except Exception:
        pass
