# apps/siteui/templatetags/dc_avatar.py
from django import template

register = template.Library()

# Inline default avatar (data URI, works without any static files)
DEFAULT_AVATAR_DATA_URI = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
    "<circle cx='12' cy='8' r='3.5' fill='%2399A2AD'/>"
    "<path d='M4 19.5c1.8-3.2 5-5 8-5s6.2 1.8 8 5' fill='none' "
    "stroke='%2399A2AD' stroke-width='1.6' stroke-linecap='round'/>"
    "</svg>"
)

def _get(obj, name):
    try:
        v = getattr(obj, name)
    except Exception:
        return None
    if callable(v):
        try:
            v = v()
        except Exception:
            return None
    return v

@register.simple_tag
def user_avatar_url(user, default=None):
    """
    Returns a best-guess avatar URL for a user.
    Tries common fields on user and user.profile (including FileField .url).
    Never raises; always returns a usable string (data URI fallback by default).
    """
    if not getattr(user, "is_authenticated", False):
        return default or DEFAULT_AVATAR_DATA_URI

    candidates = []

    # Common user fields
    for name in ("avatar_url", "avatar", "photo", "image", "picture"):
        v = _get(user, name)
        if v:
            candidates.append(getattr(v, "url", v))

    # Profile object & common profile fields
    profile = _get(user, "profile")
    if profile:
        for name in ("avatar_url", "avatar", "photo", "image", "picture"):
            v = _get(profile, name)
            if v:
                candidates.append(getattr(v, "url", v))

    # Return the first non-empty string
    for c in candidates:
        if not c:
            continue
        url = getattr(c, "url", None)
        s = url if url else str(c)
        if s.strip():
            return s

    return default or DEFAULT_AVATAR_DATA_URI
