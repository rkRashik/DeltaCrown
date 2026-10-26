"""Media requests need their own bounded budget, separate from API actions."""
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class MediaReadThrottle(SimpleRateThrottle):
    scope = 'media_read'

    def get_rate(self):
        return getattr(settings, 'MEDIA_READ_RATE', '240/min')

    def get_cache_key(self, request, view):
        identity = f'user:{request.user.pk}' if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': identity}
