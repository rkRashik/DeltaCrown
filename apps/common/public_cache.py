"""Best-effort caching for PUBLIC, reproducible listing data only.

Do NOT use for auth, sessions, throttling, payment, private user data or writes.
The builder must be safe to run on a cache miss or outage.
"""
from apps.siteui.cache_safe import safe_cache_get, safe_cache_set

_MISS = object()


def public_cache_get_or_set(key, builder, timeout):
    """A cache outage must not turn a public listing into a server error."""
    value = safe_cache_get(key, _MISS)
    if value is not _MISS:
        return value
    result = builder()  # Preserve real DB/application errors; never mask them.
    safe_cache_set(key, result, timeout)
    return result
