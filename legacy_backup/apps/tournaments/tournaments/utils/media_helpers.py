"""
TournamentMedia Helper Functions
Helper utilities for accessing and managing tournament media fields.

Part of Phase 1 - Core Tournament Models
These helpers provide backward compatibility and centralized logic.
"""

from typing import Optional, List, Dict
from django.db.models import QuerySet
from apps.tournaments.models.tournament import Tournament


# ============================================================================
# CATEGORY 1: MEDIA ACCESS HELPERS
# Direct field access with fallback support
# ============================================================================

def get_banner(tournament: Tournament) -> Optional[object]:
    """
    Get tournament banner image field.
    
    Tries:
    1. media.banner (new)
    2. tournament.banner (old)
    3. None
    
    Returns:
        ImageField object or None
    """
    if hasattr(tournament, 'media') and tournament.media and tournament.media.banner:
        return tournament.media.banner
    if hasattr(tournament, 'banner') and tournament.banner:
        return tournament.banner
    return None


def get_thumbnail(tournament: Tournament) -> Optional[object]:
    """
    Get tournament thumbnail image field.
    
    Tries:
    1. media.thumbnail (new)
    2. tournament.thumbnail (old)
    3. None
    
    Returns:
        ImageField object or None
    """
    if hasattr(tournament, 'media') and tournament.media and tournament.media.thumbnail:
        return tournament.media.thumbnail
    if hasattr(tournament, 'thumbnail') and tournament.thumbnail:
        return tournament.thumbnail
    return None


def get_rules_pdf(tournament: Tournament) -> Optional[object]:
    """
    Get tournament rules PDF field.
    
    Tries:
    1. media.rules_pdf (new)
    2. tournament.rules_pdf (old)
    3. None
    
    Returns:
        FileField object or None
    """
    if hasattr(tournament, 'media') and tournament.media and tournament.media.rules_pdf:
        return tournament.media.rules_pdf
    if hasattr(tournament, 'rules_pdf') and tournament.rules_pdf:
        return tournament.rules_pdf
    return None


def get_social_media_image(tournament: Tournament) -> Optional[object]:
    """
    Get tournament social media image field.
    
    Tries:
    1. media.social_media_image (new)
    2. None (no fallback for new field)
    
    Returns:
        ImageField object or None
    """
    if hasattr(tournament, 'media') and tournament.media and tournament.media.social_media_image:
        return tournament.media.social_media_image
    return None


def get_promotional_images(tournament: Tournament) -> List[object]:
    """
    Get list of all promotional images.
    
    Returns:
        List of ImageField objects (may be empty)
    """
    images = []
    
    if hasattr(tournament, 'media') and tournament.media:
        if tournament.media.promotional_image_1:
            images.append(tournament.media.promotional_image_1)
        if tournament.media.promotional_image_2:
            images.append(tournament.media.promotional_image_2)
        if tournament.media.promotional_image_3:
            images.append(tournament.media.promotional_image_3)
    
    return images


# ============================================================================
# CATEGORY 2: URL HELPERS
# Get URLs for media files
# ============================================================================

def get_banner_url(tournament: Tournament) -> Optional[str]:
    """
    Get tournament banner URL.
    
    Returns:
        URL string or None
    """
    banner = get_banner(tournament)
    return banner.url if banner else None


def get_thumbnail_url(tournament: Tournament) -> Optional[str]:
    """
    Get tournament thumbnail URL.
    
    Returns:
        URL string or None
    """
    thumbnail = get_thumbnail(tournament)
    return thumbnail.url if thumbnail else None


def get_rules_pdf_url(tournament: Tournament) -> Optional[str]:
    """
    Get tournament rules PDF URL.
    
    Returns:
        URL string or None
    """
    rules = get_rules_pdf(tournament)
    return rules.url if rules else None


def get_social_media_url(tournament: Tournament) -> Optional[str]:
    """
    Get tournament social media image URL.
    
    Returns:
        URL string or None
    """
    social = get_social_media_image(tournament)
    return social.url if social else None


def get_promotional_image_urls(tournament: Tournament) -> List[str]:
    """
    Get list of all promotional image URLs.
    
    Returns:
        List of URL strings (may be empty)
    """
    images = get_promotional_images(tournament)
    return [img.url for img in images if img]


# ============================================================================
# CATEGORY 3: BOOLEAN CHECK HELPERS
# Check if media exists
# ============================================================================

def has_banner(tournament: Tournament) -> bool:
    """Check if tournament has a banner image"""
    return get_banner(tournament) is not None


def has_thumbnail(tournament: Tournament) -> bool:
    """Check if tournament has a thumbnail image"""
    return get_thumbnail(tournament) is not None


def has_rules_pdf(tournament: Tournament) -> bool:
    """Check if tournament has a rules PDF"""
    return get_rules_pdf(tournament) is not None


def has_social_media_image(tournament: Tournament) -> bool:
    """Check if tournament has a social media image"""
    return get_social_media_image(tournament) is not None


def has_promotional_images(tournament: Tournament) -> bool:
    """Check if tournament has any promotional images"""
    return len(get_promotional_images(tournament)) > 0


def has_complete_media_set(tournament: Tournament) -> bool:
    """
    Check if tournament has all recommended media (banner + thumbnail).
    
    Returns:
        True if has both banner and thumbnail
    """
    return has_banner(tournament) and has_thumbnail(tournament)


# ============================================================================
# CATEGORY 4: FILENAME HELPERS
# Get filenames for downloads
# ============================================================================

def get_banner_filename(tournament: Tournament) -> Optional[str]:
    """
    Get banner filename.
    
    Returns:
        Filename string or None
    """
    banner = get_banner(tournament)
    if banner and hasattr(banner, 'name'):
        import os
        return os.path.basename(banner.name)
    return None


def get_rules_filename(tournament: Tournament) -> Optional[str]:
    """
    Get rules PDF filename.
    
    Returns:
        Filename string or None
    """
    rules = get_rules_pdf(tournament)
    if rules and hasattr(rules, 'name'):
        import os
        return os.path.basename(rules.name)
    return None


# ============================================================================
# CATEGORY 5: AGGREGATE HELPERS
# Get all media in structured formats
# ============================================================================

def get_all_image_urls(tournament: Tournament) -> Dict[str, any]:
    """
    Get all tournament images in a structured format.
    
    Returns:
        Dict with keys: banner, thumbnail, social_media, promotional
    """
    return {
        'banner': get_banner_url(tournament),
        'thumbnail': get_thumbnail_url(tournament),
        'social_media': get_social_media_url(tournament),
        'promotional': get_promotional_image_urls(tournament)
    }


def get_promotional_images_count(tournament: Tournament) -> int:
    """
    Get count of promotional images.
    
    Returns:
        Integer count (0-3)
    """
    return len(get_promotional_images(tournament))


def get_media_summary(tournament: Tournament) -> Dict[str, any]:
    """
    Get summary of all media availability.
    
    Returns:
        Dict with boolean flags for each media type
    """
    return {
        'has_banner': has_banner(tournament),
        'has_thumbnail': has_thumbnail(tournament),
        'has_rules_pdf': has_rules_pdf(tournament),
        'has_social_media': has_social_media_image(tournament),
        'promotional_count': get_promotional_images_count(tournament),
        'has_promotional': has_promotional_images(tournament),
        'has_complete_set': has_complete_media_set(tournament)
    }


# ============================================================================
# CATEGORY 6: TEMPLATE CONTEXT HELPERS
# Generate complete context for templates
# ============================================================================

def get_media_context(tournament: Tournament) -> Dict[str, any]:
    """
    Get complete media context for templates.
    
    Returns:
        Dict with all media data, URLs, and boolean flags
    """
    return {
        # URLs
        'banner_url': get_banner_url(tournament),
        'thumbnail_url': get_thumbnail_url(tournament),
        'rules_pdf_url': get_rules_pdf_url(tournament),
        'social_media_url': get_social_media_url(tournament),
        'promotional_urls': get_promotional_image_urls(tournament),
        
        # Filenames
        'banner_filename': get_banner_filename(tournament),
        'rules_filename': get_rules_filename(tournament),
        
        # Boolean flags
        'has_banner': has_banner(tournament),
        'has_thumbnail': has_thumbnail(tournament),
        'has_rules_pdf': has_rules_pdf(tournament),
        'has_social_media': has_social_media_image(tournament),
        'has_promotional': has_promotional_images(tournament),
        'has_complete_set': has_complete_media_set(tournament),
        
        # Counts
        'promotional_count': get_promotional_images_count(tournament),
        
        # All images
        'all_images': get_all_image_urls(tournament)
    }


# ============================================================================
# CATEGORY 7: QUERY OPTIMIZATION HELPERS
# Optimize database queries for media
# ============================================================================

def optimize_queryset_for_media(queryset: QuerySet) -> QuerySet:
    """
    Optimize queryset to efficiently load media relationships.
    
    Adds select_related for media to reduce queries.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Optimized queryset with media prefetched
    """
    return queryset.select_related('media')


def get_tournaments_with_media(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have media records.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(media__isnull=False)


def get_tournaments_with_banner(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have banners.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(media__banner__isnull=False)


def get_tournaments_with_thumbnail(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have thumbnails.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(media__thumbnail__isnull=False)


def get_tournaments_with_complete_media(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have both banner and thumbnail.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    # For FileFields, we need to check that the field is not empty string
    # Using exclude with empty string to filter out blank files
    return queryset.filter(
        media__banner__isnull=False,
        media__thumbnail__isnull=False
    ).exclude(
        media__banner='',
    ).exclude(
        media__thumbnail=''
    )
