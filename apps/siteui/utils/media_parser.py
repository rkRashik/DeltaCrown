from __future__ import annotations

import re
from urllib.parse import quote

import requests
from requests import RequestException


YOUTUBE_ID_REGEX = re.compile(
    r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?|live|shorts)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})",
    re.IGNORECASE,
)
TWITCH_VIDEO_REGEX = re.compile(r"twitch\.tv\/videos\/([0-9]+)", re.IGNORECASE)
TWITCH_CHANNEL_REGEX = re.compile(r"twitch\.tv\/([a-zA-Z0-9_]+)\/?$", re.IGNORECASE)
FACEBOOK_VIDEO_REGEX = re.compile(r"facebook\.com\/.*\/videos\/", re.IGNORECASE)
TWITCH_RESERVED_PATHS = {"videos", "directory", "p", "downloads", "settings"}


def _ensure_absolute_url(url: str) -> str:
    clean_url = str(url or "").strip()
    if not clean_url or clean_url == "None":
        return ""
    if clean_url.startswith("http://") or clean_url.startswith("https://"):
        return clean_url
    return f"https://{clean_url}"


def _fetch_youtube_title(source_url: str) -> str:
    if not source_url:
        return ""

    endpoint = "https://www.youtube.com/oembed"
    try:
        response = requests.get(
            endpoint,
            params={"url": source_url, "format": "json"},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("title") or "").strip()
    except (RequestException, ValueError, TypeError):
        # OEmbed failures should not block admin saves.
        return ""


def parse_media_url(url: str) -> dict[str, str]:
    """
    Parse a raw media URL into normalized provider metadata.

    Returns:
        {
            "provider": "",
            "video_id": "",
            "embed_url": "",
            "thumbnail_url": "",
            "title": "",
        }
    """
    parsed = {
        "provider": "",
        "video_id": "",
        "embed_url": "",
        "thumbnail_url": "",
        "title": "",
    }

    clean_url = _ensure_absolute_url(url)
    if not clean_url:
        return parsed

    youtube_match = YOUTUBE_ID_REGEX.search(clean_url)
    if youtube_match:
        video_id = youtube_match.group(1)
        parsed.update({
            "provider": "youtube",
            "video_id": video_id,
            "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "title": _fetch_youtube_title(clean_url),
        })
        return parsed

    if "player.twitch.tv" in clean_url:
        parsed.update({
            "provider": "twitch",
            "embed_url": clean_url,
        })
        return parsed

    twitch_video_match = TWITCH_VIDEO_REGEX.search(clean_url)
    if twitch_video_match:
        video_id = twitch_video_match.group(1)
        parsed.update({
            "provider": "twitch",
            "video_id": video_id,
            "embed_url": f"https://player.twitch.tv/?video={video_id}",
        })
        return parsed

    twitch_channel_match = TWITCH_CHANNEL_REGEX.search(clean_url)
    if twitch_channel_match:
        channel = twitch_channel_match.group(1)
        if channel.lower() not in TWITCH_RESERVED_PATHS:
            parsed.update({
                "provider": "twitch",
                "video_id": channel,
                "embed_url": f"https://player.twitch.tv/?channel={channel}",
            })
            return parsed

    if FACEBOOK_VIDEO_REGEX.search(clean_url):
        parsed.update({
            "provider": "facebook",
            "embed_url": (
                "https://www.facebook.com/plugins/video.php"
                f"?href={quote(clean_url, safe='')}&show_text=0&autoplay=1"
            ),
        })
        return parsed

    parsed.update({
        "provider": "other",
        "embed_url": clean_url,
    })
    return parsed
