"""
Fast-fail middleware for common bot vulnerability probes.

Goal: reduce CPU/DB/log pressure from high-volume scanner traffic on free-tier
instances by short-circuiting obviously invalid probe paths before template
rendering and context processors run.
"""

from __future__ import annotations

import re
from typing import Pattern

from django.conf import settings
from django.http import HttpResponseNotFound
from django.utils.deprecation import MiddlewareMixin


_PROBE_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"phpinfo", re.IGNORECASE),
    re.compile(r"(?:^|/)phpmyadmin(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)wp-admin(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)wp-login\.php(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)xmlrpc\.php(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)bitrix(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)vendor/phpunit(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)boaform(?:/|$)", re.IGNORECASE),
    re.compile(r"\.(?:php\d*|phtml|asp|aspx|jsp|cgi|pl|env)(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)\.(?:env|git|svn|hg)(?:/|$)", re.IGNORECASE),
)


def is_bot_probe_path(path: str) -> bool:
    normalized = (path or "").strip()
    if not normalized:
        return False

    # Ignore static/media probes because those paths are handled by dedicated middleware.
    if normalized.startswith("/static/") or normalized.startswith("/media/"):
        return False

    for pattern in _PROBE_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


class BotProbeShieldMiddleware(MiddlewareMixin):
    """Drop obvious scanner probe requests as cheap 404 responses."""

    def process_request(self, request):
        if not getattr(settings, "BOT_PROBE_SHIELD_ENABLED", True):
            return None

        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            return None

        if is_bot_probe_path(request.path):
            return HttpResponseNotFound("Not Found")

        return None
