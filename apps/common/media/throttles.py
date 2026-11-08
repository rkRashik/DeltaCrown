"""Media requests need their own bounded budget, separate from API actions."""
from django.conf import settings
from django.core.cache.backends.locmem import LocMemCache
from rest_framework.throttling import SimpleRateThrottle


# Production uses a single Render/Daphne web instance. Keep media read throttle
# counters local and bounded, rather than depending on the shared Redis cache
# which can intermittently time out and turn /files/ image reads into HTTP 500.
# Never replace record authorization with a cache fallback. When the web tier
# is scaled beyond one process, move to a separately resilient shared budget.
_media_read_cache = LocMemCache(
    'ownlobby-media-read-budget',
    {'TIMEOUT': 120, 'OPTIONS': {'MAX_ENTRIES': 1024, 'CULL_FREQUENCY': 3}},
)


class MediaReadThrottle(SimpleRateThrottle):
    scope = 'media_read'
    cache = _media_read_cache

    def get_rate(self):
        return getattr(settings, 'MEDIA_READ_RATE', '240/min')

    def get_cache_key(self, request, view):
        identity = f'user:{request.user.pk}' if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': identity}


class DerivativeReadThrottle(MediaReadThrottle):
    """Resized derivatives are 10-300 KiB, cached and cheap, but one page view fetches 50-100 of them (and every
    one counts, including 304s). Sharing the 240/min budget meant two quick page views got HTTP 429 and broken
    images, so they get their own, larger budget. Originals keep the strict one."""
    scope = 'media_derivative'

    def get_rate(self):
        return getattr(settings, 'MEDIA_DERIVATIVE_READ_RATE', '1500/min')
