# apps/siteui/utils/embeds.py
import re
import urllib.parse

YOUTUBE_PATTERNS = [
    re.compile(r"youtu\.be/(?P<id>[\w-]{11})", re.I),
    re.compile(r"youtube\.com/(?:watch\?v=|live/|shorts/|embed/)(?P<id>[\w-]{11})", re.I),
]
FACEBOOK_RE = re.compile(r"(facebook\.com/[^/]+/(?:videos|live)/|fb\.watch/)", re.I)
TWITCH_RE = re.compile(r"twitch\.tv/(?P<kind>videos|[^/]+)/?(?P<slug>[^/?#]+)?", re.I)

def detect_platform(url: str) -> str:
    if not url:
        return ""
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"
    if "facebook.com" in u or "fb.watch" in u:
        return "Facebook"
    if "twitch.tv" in u:
        return "Twitch"
    return ""

def _youtube_id(url: str) -> str | None:
    if not url:
        return None
    for rx in YOUTUBE_PATTERNS:
        m = rx.search(url)
        if m:
            return m.group("id")
    # Fallback: try to read v= param
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        v = qs.get("v", [None])[0]
        if v and len(v) >= 10:
            return v
    except Exception:
        pass
    return None

def build_embed_url(url: str, *, host_for_twitch_parent: str | None = None) -> tuple[str, str]:
    """
    Returns (embed_url, platform). `platform` in {"YouTube","Facebook","Twitch",""}.
    - Twitch requires a `parent` query param; pass request.get_host() as host_for_twitch_parent.
    """
    platform = detect_platform(url)
    if platform == "YouTube":
        vid = _youtube_id(url)
        if vid:
            return f"https://www.youtube.com/embed/{vid}", platform
    elif platform == "Facebook":
        enc = urllib.parse.quote(url, safe="")
        # Show text off for a cleaner player
        return f"https://www.facebook.com/plugins/video.php?href={enc}&show_text=false", platform
    elif platform == "Twitch":
        # If URL points to a channel (…/twitch.tv/<channel>), use channel param
        # If it's a VOD (…/twitch.tv/videos/<id>), use video param
        m = TWITCH_RE.search(url or "")
        parent = host_for_twitch_parent.split(":")[0] if host_for_twitch_parent else "localhost"
        if m:
            kind = m.group("kind")
            slug = m.group("slug")
            base = "https://player.twitch.tv/"
            if kind == "videos" and slug:
                return f"{base}?video={slug}&parent={parent}", platform
            elif kind and kind != "videos":
                channel = kind  # when kind actually captured channel in regex
                return f"{base}?channel={channel}&parent={parent}", platform
        # Fallback: treat anything else as a channel path after domain
        try:
            path = urllib.parse.urlsplit(url).path.strip("/")
            channel = path.split("/", 1)[0]
            if channel:
                return f"https://player.twitch.tv/?channel={channel}&parent={parent}", platform
        except Exception:
            pass
    # Unknown provider or parse failed
    return url or "", platform
