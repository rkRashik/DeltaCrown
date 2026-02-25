"""
Dev-only middleware: proxy missing local media files to production (Cloudinary).

When running locally with FileSystemStorage, media uploaded on production
(which lives on Cloudinary) won't exist in the local `media/` folder.
This middleware intercepts 404 responses for `/media/…` requests and
redirects to the Cloudinary CDN so images render without manual syncing.

Activate by setting in your `.env`:
    CLOUDINARY_CLOUD_NAME=dmtlc11lt        # ← required for CDN redirect
    MEDIA_PROXY_URL=https://deltacrown.xyz  # ← optional origin fallback

Disabled automatically when CLOUDINARY_URL is set (i.e. in production)
or when DEBUG is False.
"""

import os

from django.conf import settings
from django.http import HttpResponseRedirect


class MediaProxyMiddleware:
    """Redirect missing /media/ files to Cloudinary CDN or production origin."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Pre-compute at startup so there's zero per-request overhead when disabled
        self.cloud_name = self._resolve_cloud_name()
        self.proxy_url = self._resolve_proxy_url()

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 404:
            return response
        if not request.path.startswith(settings.MEDIA_URL):
            return response
        if not (self.cloud_name or self.proxy_url):
            return response

        # Strip the leading MEDIA_URL to get the relative path stored in the DB.
        # Cloudinary-backed DBs store paths like "media/games/logos/X", so
        # request.path = "/media/media/games/logos/X" → relative = "media/games/logos/X".
        relative_path = request.path[len(settings.MEDIA_URL):]

        # Strategy 1: Cloudinary CDN (preferred, works for Cloudinary-backed DBs)
        if self.cloud_name:
            cdn = (
                f"https://res.cloudinary.com/{self.cloud_name}"
                f"/image/upload/{relative_path}"
            )
            return HttpResponseRedirect(cdn)

        # Strategy 2: Origin server fallback (works when production serves /media/)
        return HttpResponseRedirect(
            f"{self.proxy_url}{settings.MEDIA_URL}{relative_path}"
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_cloud_name():
        """Return the Cloudinary cloud name, or None."""
        # Never proxy in production
        if os.getenv("CLOUDINARY_URL"):
            return None
        if not getattr(settings, "DEBUG", False):
            return None
        return os.getenv("CLOUDINARY_CLOUD_NAME") or None

    @staticmethod
    def _resolve_proxy_url():
        """Return the production origin URL, or None to disable."""
        # Never proxy in production (Cloudinary handles it)
        if os.getenv("CLOUDINARY_URL"):
            return None
        # Only proxy in DEBUG mode
        if not getattr(settings, "DEBUG", False):
            return None
        # Read from env – defaults to production site
        url = os.getenv("MEDIA_PROXY_URL", "https://deltacrown.xyz")
        return url.rstrip("/")
