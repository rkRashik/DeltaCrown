"""Shared media URL normalization helpers.

These helpers prefer valid local media files when available and normalize
known URL drift patterns to avoid broken image links.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from django.conf import settings


def _media_url_prefix() -> str:
    media_url = str(getattr(settings, "MEDIA_URL", "/media/") or "/media/")
    if not media_url.startswith("/"):
        media_url = "/" + media_url
    if not media_url.endswith("/"):
        media_url += "/"
    return media_url


def _clean_rel_path(value: str) -> str:
    rel = str(value or "").strip().replace("\\", "/").lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/") :]
    return rel


def _media_file_exists(rel_path: str) -> bool:
    rel = _clean_rel_path(rel_path)
    if not rel:
        return False

    media_root = str(getattr(settings, "MEDIA_ROOT", "") or "")
    if not media_root:
        return False

    root_abs = os.path.abspath(media_root)
    file_abs = os.path.abspath(os.path.join(root_abs, rel))
    try:
        if os.path.commonpath([root_abs, file_abs]) != root_abs:
            return False
    except Exception:
        return False

    return os.path.isfile(file_abs)


def _media_url_from_rel(rel_path: str) -> str:
    rel = _clean_rel_path(rel_path)
    if not rel:
        return ""
    return f"{_media_url_prefix()}{rel}"


def normalize_media_url(raw_url: str, file_name: str = "") -> str:
    """Normalize media URLs and prefer local file-backed URLs when available."""
    url = str(raw_url or "").strip()
    name = _clean_rel_path(file_name)

    # Prefer canonical local media URL when the backing file exists.
    if name and _media_file_exists(name):
        return _media_url_from_rel(name)

    if not url:
        return ""

    url = url.replace("\\", "/")
    url = url.replace("/media/media/", "/media/")
    url = url.replace("/image/upload/v1/media/media/", "/image/upload/v1/media/")
    url = url.replace("/image/upload/media/media/", "/image/upload/media/")

    parsed = urlparse(url)
    is_absolute = bool(parsed.scheme and parsed.netloc)

    if is_absolute:
        # Cloudinary path drift when file_name is stored without "media/" prefix.
        if "res.cloudinary.com" in parsed.netloc and name and not str(file_name or "").startswith("media/"):
            url = url.replace("/image/upload/v1/media/", "/image/upload/v1/", 1)
            url = url.replace("/image/upload/media/", "/image/upload/", 1)
        return url

    media_prefix = _media_url_prefix()

    if url.startswith("/"):
        if url.startswith(media_prefix):
            rel = _clean_rel_path(url[len(media_prefix) :])
            if rel and _media_file_exists(rel):
                return _media_url_from_rel(rel)
            if name and _media_file_exists(name):
                return _media_url_from_rel(name)
            return _media_url_from_rel(rel)
        return url

    rel = _clean_rel_path(url)
    if rel and _media_file_exists(rel):
        return _media_url_from_rel(rel)
    if name and _media_file_exists(name):
        return _media_url_from_rel(name)

    # Keep relative media-like values usable even if file is currently missing.
    return _media_url_from_rel(rel) if rel else ""


def field_file_url(file_field) -> str:
    """Safely resolve a FileField/ImageField to a normalized URL."""
    if not file_field:
        return ""

    try:
        return normalize_media_url(
            getattr(file_field, "url", "") or "",
            getattr(file_field, "name", "") or "",
        )
    except Exception:
        return ""
