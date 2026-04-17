# apps/siteui/templatetags/dc_avatar.py
from urllib.parse import quote

from django import template

from apps.common.media_urls import field_file_url, normalize_media_url

register = template.Library()

# Esports-themed gradient colors for initials avatars
AVATAR_GRADIENTS = [
    ("00D9FF", "A100FF"),  # Cyan to Purple
    ("FF0080", "FF8C00"),  # Pink to Orange
    ("00FF88", "00D9FF"),  # Green to Cyan
    ("A100FF", "FF0080"),  # Purple to Pink
    ("FFD700", "FF6B00"),  # Gold to Orange
    ("00FFF0", "0099FF"),  # Turquoise to Blue
]

def _get_user_initials(user):
    """Generate 1-2 character initials from user's name or username."""
    # Try full name first
    full_name = getattr(user, 'get_full_name', lambda: '')()
    if full_name and full_name.strip():
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return parts[0][0].upper()
    
    # Fallback to username
    username = getattr(user, 'username', 'U')
    return username[0].upper() if username else 'U'

def _generate_initials_avatar(user):
    """Generate a modern esports-style SVG avatar with user initials."""
    initials = _get_user_initials(user)
    
    # Pick gradient based on user ID or username hash for consistency
    user_id = getattr(user, 'id', 0) or 0
    gradient_idx = user_id % len(AVATAR_GRADIENTS)
    color1, color2 = AVATAR_GRADIENTS[gradient_idx]
    
    # SVG with gradient background and centered initials
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
        <defs>
            <linearGradient id='grad{user_id}' x1='0%' y1='0%' x2='100%' y2='100%'>
                <stop offset='0%' style='stop-color:#{color1};stop-opacity:1'/>
                <stop offset='100%' style='stop-color:#{color2};stop-opacity:1'/>
            </linearGradient>
        </defs>
        <rect width='100' height='100' fill='url(#grad{user_id})'/>
        <text x='50' y='50' font-family='Arial,sans-serif' font-size='45' font-weight='700' 
              fill='white' text-anchor='middle' dominant-baseline='central'>{initials}</text>
    </svg>"""
    
    return f"data:image/svg+xml;utf8,{quote(svg)}"

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


def _append_candidate(candidates, value):
    if not value:
        return

    url = ""
    try:
        # FieldFile / ImageField values
        url = field_file_url(value)
    except Exception:
        url = ""

    if not url:
        try:
            url = normalize_media_url(str(value), "")
        except Exception:
            url = ""

    if url and url not in candidates:
        candidates.append(url)


def _avatar_candidates(user):
    candidates = []

    # Profile avatar is the primary source of truth.
    profile = _get(user, "profile")
    if profile:
        for name in ("avatar", "photo", "image", "picture", "avatar_url"):
            _append_candidate(candidates, _get(profile, name))

    # Fallback to user-level fields for compatibility.
    for name in ("avatar", "photo", "image", "picture", "avatar_url"):
        _append_candidate(candidates, _get(user, name))

    return candidates

@register.simple_tag
def user_avatar_url(user, default=None):
    """
    Returns avatar URL for a user, or generates modern esports-style initials avatar.
    - If user has uploaded avatar: returns avatar URL
    - If no avatar: returns colorful SVG with user initials (like Facebook/Discord)
    Never raises; always returns a usable string.
    """
    if not user:
        return default or DEFAULT_AVATAR_DATA_URI

    if getattr(user, "is_authenticated", False):
        for candidate in _avatar_candidates(user):
            if candidate:
                return candidate

    # No usable avatar found - generate modern initials avatar.
    return default or _generate_initials_avatar(user)

# Legacy constant for backward compatibility
DEFAULT_AVATAR_DATA_URI = _generate_initials_avatar(type('User', (), {'id': 0, 'username': 'U', 'is_authenticated': False})())
