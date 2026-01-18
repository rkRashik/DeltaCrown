"""
URL Validator Service - P0 Safety Foundation
Validates and sanitizes URLs for embeds (highlights, streams, affiliate links).

Security Features:
- Domain whitelisting (HTTPS only)
- Character whitelisting for video IDs
- Platform detection
- Safe embed URL construction

Usage:
    from apps.user_profile.services.url_validator import validate_highlight_url, validate_stream_url
    
    result = validate_highlight_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
    if result['valid']:
        embed_url = result['embed_url']
        platform = result['platform']
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional
from django.conf import settings


# Whitelisted domains (HTTPS only)
HIGHLIGHT_DOMAINS = {
    'youtube': ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com'],
    'twitch': ['twitch.tv', 'www.twitch.tv', 'clips.twitch.tv'],
    'medal': ['medal.tv', 'www.medal.tv'],
    'facebook': ['facebook.com', 'www.facebook.com', 'fb.watch'],
}

STREAM_DOMAINS = {
    'twitch': ['player.twitch.tv', 'www.twitch.tv'],
    'youtube': ['youtube.com', 'www.youtube.com'],
    'facebook': ['www.facebook.com', 'fb.watch'],
}

AFFILIATE_DOMAINS = {
    'amazon': ['amazon.com', 'www.amazon.com', 'amzn.to'],
    'logitech': ['logitech.com', 'www.logitech.com'],
    'razer': ['razer.com', 'www.razer.com'],
}

# Character whitelist for video IDs (alphanumeric, underscore, hyphen only)
VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

# Twitch parent parameter (hardcoded domain, never user-provided)
TWITCH_PARENT_DOMAIN = getattr(settings, 'SITE_DOMAIN', 'deltacrown.com')


def validate_highlight_url(url: str) -> Dict[str, any]:
    """
    Validate and parse highlight video URL (YouTube, Twitch, Medal.tv).
    
    Args:
        url: User-provided video URL
        
    Returns:
        {
            'valid': bool,
            'platform': str,  # 'youtube', 'twitch', 'medal'
            'video_id': str,  # Extracted video ID
            'embed_url': str,  # Safe iframe embed URL
            'error': str,     # Error message if invalid
        }
    
    Security:
        - HTTPS enforcement
        - Domain whitelist
        - Video ID character whitelist
        - XSS prevention via URL construction
    """
    if not url or not isinstance(url, str):
        return {'valid': False, 'error': 'URL is required'}
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return {'valid': False, 'error': 'Invalid URL format'}
    
    # Enforce HTTPS
    if parsed.scheme != 'https':
        return {'valid': False, 'error': 'Only HTTPS URLs are allowed'}
    
    domain = parsed.netloc.lower()
    
    # Detect platform
    platform = None
    for plat, domains in HIGHLIGHT_DOMAINS.items():
        if any(domain == d or domain.endswith(f'.{d}') for d in domains):
            platform = plat
            break
    
    if not platform:
        return {'valid': False, 'error': f'Domain not whitelisted: {domain}'}
    
    # Extract video ID based on platform
    video_id = None
    
    if platform == 'youtube':
        # YouTube formats:
        # - https://youtube.com/watch?v=VIDEO_ID
        # - https://youtu.be/VIDEO_ID
        # - https://youtube.com/shorts/VIDEO_ID
        if 'youtu.be' in domain:
            video_id = parsed.path.lstrip('/')
        elif '/watch' in parsed.path:
            query_params = parse_qs(parsed.query)
            video_id = query_params.get('v', [None])[0]
        elif '/shorts/' in parsed.path:
            video_id = parsed.path.split('/shorts/')[-1]
    
    elif platform == 'twitch':
        # Twitch formats:
        # - https://clips.twitch.tv/CLIP_ID
        # - https://twitch.tv/USERNAME/clip/CLIP_ID
        if 'clips.twitch.tv' in domain:
            video_id = parsed.path.lstrip('/')
        elif '/clip/' in parsed.path:
            video_id = parsed.path.split('/clip/')[-1]
    
    elif platform == 'medal':
        # Medal.tv formats:
        # - https://medal.tv/games/GAME/clips/CLIP_ID
        # - https://medal.tv/clip/CLIP_ID
        if '/clip/' in parsed.path or '/clips/' in parsed.path:
            video_id = parsed.path.split('/')[-1]
    
    elif platform == 'facebook':
        # Facebook video formats:
        # - https://www.facebook.com/watch/?v=VIDEO_ID
        # - https://www.facebook.com/username/videos/VIDEO_ID
        # - https://www.facebook.com/reel/VIDEO_ID
        # - https://www.facebook.com/share/v/VIDEO_ID/
        # - https://fb.watch/VIDEO_ID
        
        # Extract video ID from various formats
        if 'fb.watch' in domain:
            # fb.watch/ABC123xyz (short URL format)
            video_id = parsed.path.lstrip('/').rstrip('/')
        elif '/watch' in parsed.path:
            # /watch/?v=12345 or /watch?v=12345
            query_params = parse_qs(parsed.query)
            video_id = query_params.get('v', [None])[0]
        elif '/share/v/' in parsed.path:
            # /share/v/12345/
            parts = parsed.path.split('/share/v/')
            if len(parts) > 1:
                video_id = parts[1].rstrip('/')
        elif '/reel/' in parsed.path:
            # /reel/12345
            video_id = parsed.path.split('/reel/')[-1].rstrip('/')
        elif '/videos/' in parsed.path:
            # /username/videos/12345
            video_id = parsed.path.split('/videos/')[-1].rstrip('/')
        else:
            return {'valid': False, 'error': 'Facebook URL must be a video (watch, reel, share, or fb.watch)'}
    
    # Validate video ID
    if not video_id:
        return {'valid': False, 'error': 'Could not extract video ID'}
    
    # Character whitelist (prevent path traversal, SQL injection, XSS)
    if not VIDEO_ID_PATTERN.match(video_id):
        return {'valid': False, 'error': 'Video ID contains invalid characters'}
    
    # Construct safe embed URL (pass original URL for Facebook)
    embed_url = _construct_embed_url(platform, video_id, original_url=url)
    
    # Check if embed is not possible (e.g., Facebook group posts)
    if embed_url is None:
        return {
            'valid': True,
            'platform': platform,
            'video_id': video_id,
            'embed_url': None,
            'thumbnail_url': None,
            'fallback_reason': 'This content cannot be embedded. Open in new tab to view.',
            'original_url': url
        }
    
    return {
        'valid': True,
        'platform': platform,
        'video_id': video_id,
        'embed_url': embed_url,
        'thumbnail_url': _construct_thumbnail_url(platform, video_id),
    }


def validate_stream_url(url: str) -> Dict[str, any]:
    """
    Validate and parse stream URL (Twitch, YouTube, Facebook Gaming).
    
    Args:
        url: User-provided stream/channel URL
        
    Returns:
        {
            'valid': bool,
            'platform': str,  # 'twitch', 'youtube', 'facebook'
            'channel_id': str,  # Username or channel ID
            'embed_url': str,  # Safe iframe embed URL
            'error': str,     # Error message if invalid
        }
    
    Security:
        - HTTPS enforcement
        - Domain whitelist
        - Channel ID character whitelist
        - Twitch parent parameter hardcoded
    """
    if not url or not isinstance(url, str):
        return {'valid': False, 'error': 'URL is required'}
    
    try:
        parsed = urlparse(url)
    except Exception:
        return {'valid': False, 'error': 'Invalid URL format'}
    
    # Enforce HTTPS
    if parsed.scheme != 'https':
        return {'valid': False, 'error': 'Only HTTPS URLs are allowed'}
    
    domain = parsed.netloc.lower()
    
    # Detect platform
    platform = None
    for plat, domains in STREAM_DOMAINS.items():
        if any(domain == d or domain.endswith(f'.{d}') for d in domains):
            platform = plat
            break
    
    if not platform:
        return {'valid': False, 'error': f'Domain not whitelisted: {domain}'}
    
    # Extract channel ID based on platform
    channel_id = None
    
    if platform == 'twitch':
        # Twitch formats: https://twitch.tv/USERNAME
        channel_id = parsed.path.lstrip('/').split('/')[0]
    elif platform == 'youtube':
        # YouTube formats: https://youtube.com/channel/CHANNEL_ID or /c/USERNAME
        path_parts = parsed.path.lstrip('/').split('/')
        if 'channel' in path_parts:
            channel_id = path_parts[path_parts.index('channel') + 1]
        elif 'c' in path_parts:
            channel_id = path_parts[path_parts.index('c') + 1]
        elif '@' in parsed.path:
            channel_id = parsed.path.lstrip('/@')
    elif platform == 'facebook':
        # Facebook Gaming formats: https://fb.watch/USERNAME
        channel_id = parsed.path.lstrip('/').split('/')[0]
    
    # Validate channel ID
    if not channel_id:
        return {'valid': False, 'error': 'Could not extract channel ID'}
    
    # Character whitelist
    if not VIDEO_ID_PATTERN.match(channel_id):
        return {'valid': False, 'error': 'Channel ID contains invalid characters'}
    
    # Construct safe embed URL
    embed_url = _construct_stream_embed_url(platform, channel_id)
    
    return {
        'valid': True,
        'platform': platform,
        'channel_id': channel_id,
        'embed_url': embed_url,
    }


def validate_affiliate_url(url: str) -> Dict[str, any]:
    """
    Validate affiliate URL (Amazon, Logitech, Razer).
    
    Args:
        url: User-provided product URL
        
    Returns:
        {
            'valid': bool,
            'platform': str,  # 'amazon', 'logitech', 'razer'
            'safe_url': str,  # Sanitized URL (no open redirect)
            'error': str,     # Error message if invalid
        }
    
    Security:
        - HTTPS enforcement
        - Domain whitelist
        - Prevent open redirect
    """
    if not url or not isinstance(url, str):
        return {'valid': False, 'error': 'URL is required'}
    
    try:
        parsed = urlparse(url)
    except Exception:
        return {'valid': False, 'error': 'Invalid URL format'}
    
    # Enforce HTTPS
    if parsed.scheme != 'https':
        return {'valid': False, 'error': 'Only HTTPS URLs are allowed'}
    
    domain = parsed.netloc.lower()
    
    # Detect platform
    platform = None
    for plat, domains in AFFILIATE_DOMAINS.items():
        if any(domain == d or domain.endswith(f'.{d}') for d in domains):
            platform = plat
            break
    
    if not platform:
        return {'valid': False, 'error': f'Domain not whitelisted: {domain}'}
    
    # Return original URL (already validated)
    return {
        'valid': True,
        'platform': platform,
        'safe_url': url,  # Already HTTPS + whitelisted
    }


def _construct_embed_url(platform: str, video_id: str, original_url: str = None) -> str:
    """
    Construct safe iframe embed URL for highlights.
    
    YouTube: Use standard youtube.com/embed with safe params to prevent Error 153.
    Params added:
    - rel=0: Don't show related videos from other channels
    - modestbranding=1: Minimal YouTube branding
    - playsinline=1: Play inline on mobile (iOS requirement)
    - enablejsapi=1: Enable JavaScript API for better control
    
    Twitch: Use clips.twitch.tv/embed with MULTIPLE parent parameters for localhost dev.
    Parent params MUST include all possible local hostnames:
    - localhost
    - 127.0.0.1
    - And production domain
    
    Facebook: Use Facebook's official video plugin embed endpoint with the ORIGINAL URL.
    Facebook requires the exact original URL for proper embed permission checking.
    The plugin automatically handles:
    - Private video detection (shows appropriate error)
    - Deleted video detection
    - Permission/age-restricted content
    - Group posts (may not be embeddable - returns None with fallback reason)
    
    Returns:
        str or None: Embed URL if embeddable, None if not (e.g., private/group content)
    """
    if platform == 'youtube':
        # Use standard youtube.com/embed (more reliable than youtube-nocookie for embeds)
        # Add safe params to prevent Error 153 (configuration error)
        return f"https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&playsinline=1&enablejsapi=1"
    elif platform == 'twitch':
        # Twitch requires parent parameter - MUST include ALL possible hosts
        # For local development, include both localhost and 127.0.0.1
        # For production, also include the actual domain
        return f"https://clips.twitch.tv/embed?clip={video_id}&parent=localhost&parent=127.0.0.1&parent={TWITCH_PARENT_DOMAIN}"
    elif platform == 'medal':
        return f"https://medal.tv/clip/{video_id}?embed=true"
    elif platform == 'facebook':
        # Facebook Video Plugin - MUST use the original URL for proper permissions
        # Format: https://www.facebook.com/plugins/video.php?href=<encoded_url>
        from urllib.parse import quote_plus
        
        # Check if this is a group post (not embeddable)
        if original_url and '/groups/' in original_url:
            # Group posts typically can't be embedded due to privacy
            return None
        
        # Use original URL if available, otherwise reconstruct
        if original_url:
            canonical_url = original_url
        else:
            # Fallback: reconstruct URL (less reliable)
            canonical_url = f"https://www.facebook.com/watch/?v={video_id}"
        
        # URL encode the full URL (quote_plus for proper encoding)
        encoded_url = quote_plus(canonical_url)
        
        # Facebook's official embed plugin endpoint
        # show_text=0: Hide post text
        # autoplay=0: Don't autoplay (better UX)
        return f"https://www.facebook.com/plugins/video.php?href={encoded_url}&show_text=0&autoplay=0"
    return ""


def _construct_stream_embed_url(platform: str, channel_id: str) -> str:
    """
    Construct safe iframe embed URL for live streams.
    
    Facebook: Uses the same video plugin endpoint as highlights.
    Note: Facebook Gaming live streams may not always embed properly due to:
    - Privacy settings (public vs followers-only)
    - Age restrictions
    - Geographic restrictions
    The plugin will show appropriate errors when content cannot be embedded.
    """
    if platform == 'twitch':
        # Twitch live stream embed
        return f"https://player.twitch.tv/?channel={channel_id}&parent={TWITCH_PARENT_DOMAIN}"
    elif platform == 'youtube':
        # YouTube live stream embed - use youtube-nocookie for consistency
        return f"https://www.youtube-nocookie.com/embed/live_stream?channel={channel_id}"
    elif platform == 'facebook':
        # Facebook Gaming live stream embed via video plugin
        from urllib.parse import quote
        
        # Construct Facebook page/profile URL for live stream
        canonical_url = f"https://www.facebook.com/{channel_id}/live"
        encoded_url = quote(canonical_url, safe='')
        
        # Use video plugin endpoint (handles live streams + VODs)
        return f"https://www.facebook.com/plugins/video.php?href={encoded_url}&show_text=false&width=560"
    return ""


def _construct_thumbnail_url(platform: str, video_id: str) -> Optional[str]:
    """Construct thumbnail URL for video preview."""
    if platform == 'youtube':
        # Use hqdefault (480x360) for better quality
        # YouTube guarantees this exists for all videos
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    elif platform == 'twitch':
        # Twitch clip thumbnails require API call
        # Return None - UI will show platform placeholder
        return None
    elif platform == 'medal':
        # Medal.tv thumbnails require API call
        # Return None - UI will show platform placeholder
        return None
    elif platform == 'facebook':
        # Facebook thumbnails require Graph API with access token
        # Return None - UI will show platform placeholder
        return None
    return None
