"""
Trophy Showcase Service - Unlocked Cosmetics Logic (P0)

Service functions for computing which cosmetics (borders/frames/badges) 
are unlocked based on user achievements.

Design:
- Borders unlocked via badge rarity (Common=Bronze, Rare=Silver, etc.)
- Frames unlocked via tournament participation/wins
- Badges shown from UserBadge (already earned)
"""
from typing import List, Dict, Any, Set
from django.db.models import Q, Count, QuerySet
from apps.user_profile.models.trophy_showcase import TrophyShowcaseConfig
from apps.user_profile.models_main import Badge, UserBadge


# ============================================================================
# BORDER UNLOCK LOGIC
# ============================================================================

def get_unlocked_borders(user) -> List[str]:
    """
    Get list of border styles user has unlocked.
    
    Unlock criteria:
    - NONE: Always available
    - BRONZE: Earn any Common badge
    - SILVER: Earn any Rare badge
    - GOLD: Earn any Epic badge
    - PLATINUM: Earn any Legendary badge
    - DIAMOND: Earn 10+ Legendary badges
    - MASTER: Win a major tournament (has 'tournament_champion' badge)
    
    Args:
        user: User object
    
    Returns:
        List of BorderStyle choices (e.g., ['none', 'bronze', 'silver', 'gold'])
    
    Examples:
        >>> borders = get_unlocked_borders(user)
        >>> 'gold' in borders
        True
    """
    unlocked = ['none']  # Always available
    
    # Get user's earned badges with rarity
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    
    rarities_earned = set()
    legendary_count = 0
    has_tournament_champion = False
    
    for user_badge in user_badges:
        badge = user_badge.badge
        rarities_earned.add(badge.rarity)
        
        if badge.rarity == Badge.Rarity.LEGENDARY:
            legendary_count += 1
        
        if badge.slug == 'tournament_champion':
            has_tournament_champion = True
    
    # Unlock borders based on rarities earned
    if Badge.Rarity.COMMON in rarities_earned:
        unlocked.append('bronze')
    
    if Badge.Rarity.RARE in rarities_earned:
        unlocked.append('silver')
    
    if Badge.Rarity.EPIC in rarities_earned:
        unlocked.append('gold')
    
    if Badge.Rarity.LEGENDARY in rarities_earned:
        unlocked.append('platinum')
    
    if legendary_count >= 10:
        unlocked.append('diamond')
    
    if has_tournament_champion:
        unlocked.append('master')
    
    return unlocked


def is_border_unlocked(user, border_style: str) -> bool:
    """
    Check if user has unlocked a specific border.
    
    Args:
        user: User object
        border_style: BorderStyle choice (e.g., 'gold')
    
    Returns:
        True if border is unlocked
    
    Examples:
        >>> is_border_unlocked(user, 'gold')
        True
        >>> is_border_unlocked(user, 'master')
        False
    """
    unlocked = get_unlocked_borders(user)
    return border_style in unlocked


# ============================================================================
# FRAME UNLOCK LOGIC
# ============================================================================

def get_unlocked_frames(user) -> List[str]:
    """
    Get list of frame styles user has unlocked.
    
    Unlock criteria:
    - NONE: Always available
    - COMPETITOR: Participate in any tournament (has 'tournament_participant' badge)
    - FINALIST: Reach tournament finals (has 'tournament_finalist' badge)
    - CHAMPION: Win a tournament (has 'tournament_champion' badge)
    - GRAND_CHAMPION: Win 3+ tournaments (has 3+ tournament-category badges)
    - LEGEND: Win 10+ tournaments (has 10+ tournament-category badges)
    
    Args:
        user: User object
    
    Returns:
        List of FrameStyle choices (e.g., ['none', 'competitor', 'champion'])
    
    Examples:
        >>> frames = get_unlocked_frames(user)
        >>> 'champion' in frames
        True
    """
    unlocked = ['none']  # Always available
    
    # Get user's earned tournament badges
    user_badges = (
        UserBadge.objects
        .filter(user=user, badge__category=Badge.Category.TOURNAMENT)
        .select_related('badge')
    )
    
    tournament_win_count = 0
    has_participant = False
    has_finalist = False
    has_champion = False
    
    for user_badge in user_badges:
        badge = user_badge.badge
        
        if badge.slug == 'tournament_participant':
            has_participant = True
        
        if badge.slug == 'tournament_finalist':
            has_finalist = True
        
        if badge.slug == 'tournament_champion':
            has_champion = True
        
        # Count tournament wins (badges with 'win' or 'champion' in name)
        if 'win' in badge.slug.lower() or 'champion' in badge.slug.lower():
            tournament_win_count += 1
    
    # Unlock frames based on tournament achievements
    if has_participant:
        unlocked.append('competitor')
    
    if has_finalist:
        unlocked.append('finalist')
    
    if has_champion:
        unlocked.append('champion')
    
    if tournament_win_count >= 3:
        unlocked.append('grand_champion')
    
    if tournament_win_count >= 10:
        unlocked.append('legend')
    
    return unlocked


def is_frame_unlocked(user, frame_style: str) -> bool:
    """
    Check if user has unlocked a specific frame.
    
    Args:
        user: User object
        frame_style: FrameStyle choice (e.g., 'champion')
    
    Returns:
        True if frame is unlocked
    
    Examples:
        >>> is_frame_unlocked(user, 'champion')
        True
        >>> is_frame_unlocked(user, 'legend')
        False
    """
    unlocked = get_unlocked_frames(user)
    return frame_style in unlocked


# ============================================================================
# BADGE UNLOCK LOGIC
# ============================================================================

def get_pinnable_badges(user) -> QuerySet:
    """
    Get all badges user can pin (earned badges).
    
    Args:
        user: User object
    
    Returns:
        QuerySet of UserBadge objects user has earned
    
    Examples:
        >>> badges = get_pinnable_badges(user)
        >>> badges.count()
        15
    """
    return (
        UserBadge.objects
        .filter(user=user)
        .select_related('badge')
        .order_by('-earned_at')
    )


def get_pinned_badges(user) -> List[UserBadge]:
    """
    Get user's currently pinned badges (from TrophyShowcaseConfig).
    
    Args:
        user: User object
    
    Returns:
        List of UserBadge objects in pinned order
    
    Examples:
        >>> pinned = get_pinned_badges(user)
        >>> len(pinned)
        3
        >>> pinned[0].badge.name
        'Tournament Champion'
    """
    try:
        showcase = TrophyShowcaseConfig.objects.get(user=user)
        return showcase.get_pinned_badges()
    except TrophyShowcaseConfig.DoesNotExist:
        return []


# ============================================================================
# SHOWCASE CONFIG HELPERS
# ============================================================================

def get_or_create_showcase(user) -> TrophyShowcaseConfig:
    """
    Get or create user's trophy showcase config.
    
    Args:
        user: User object
    
    Returns:
        TrophyShowcaseConfig object
    
    Examples:
        >>> showcase = get_or_create_showcase(user)
        >>> showcase.border
        'none'
    """
    showcase, created = TrophyShowcaseConfig.objects.get_or_create(
        user=user,
        defaults={
            'border': 'none',
            'frame': 'none',
            'pinned_badge_ids': []
        }
    )
    return showcase


def get_showcase_data(user) -> Dict[str, Any]:
    """
    Get complete showcase data (equipped + unlocked cosmetics).
    
    Args:
        user: User object
    
    Returns:
        Dict with equipped and unlocked cosmetics
    
    Examples:
        >>> data = get_showcase_data(user)
        >>> data['equipped']['border']
        'gold'
        >>> data['unlocked']['borders']
        ['none', 'bronze', 'silver', 'gold']
        >>> len(data['pinned_badges'])
        3
    """
    showcase = get_or_create_showcase(user)
    
    return {
        'equipped': {
            'border': showcase.border,
            'frame': showcase.frame,
        },
        'unlocked': {
            'borders': get_unlocked_borders(user),
            'frames': get_unlocked_frames(user),
        },
        'pinned_badges': [
            {
                'id': ub.id,
                'badge_name': ub.badge.name,
                'badge_icon': ub.badge.icon,
                'badge_rarity': ub.badge.rarity,
                'earned_at': ub.earned_at,
            }
            for ub in showcase.get_pinned_badges()
        ],
        'available_badges': get_pinnable_badges(user).count(),
    }


def equip_border(user, border_style: str) -> TrophyShowcaseConfig:
    """
    Equip a border (validates unlock status).
    
    Args:
        user: User object
        border_style: BorderStyle choice (e.g., 'gold')
    
    Returns:
        Updated TrophyShowcaseConfig
    
    Raises:
        ValueError: If border not unlocked
    
    Examples:
        >>> showcase = equip_border(user, 'gold')
        >>> showcase.border
        'gold'
    """
    if not is_border_unlocked(user, border_style):
        raise ValueError(f'Border "{border_style}" is not unlocked')
    
    showcase = get_or_create_showcase(user)
    showcase.border = border_style
    showcase.save()
    return showcase


def equip_frame(user, frame_style: str) -> TrophyShowcaseConfig:
    """
    Equip a frame (validates unlock status).
    
    Args:
        user: User object
        frame_style: FrameStyle choice (e.g., 'champion')
    
    Returns:
        Updated TrophyShowcaseConfig
    
    Raises:
        ValueError: If frame not unlocked
    
    Examples:
        >>> showcase = equip_frame(user, 'champion')
        >>> showcase.frame
        'champion'
    """
    if not is_frame_unlocked(user, frame_style):
        raise ValueError(f'Frame "{frame_style}" is not unlocked')
    
    showcase = get_or_create_showcase(user)
    showcase.frame = frame_style
    showcase.save()
    return showcase


def validate_showcase_config(user, showcase: TrophyShowcaseConfig) -> List[str]:
    """
    Validate showcase config against user's unlocks.
    
    Returns list of validation errors (empty if valid).
    
    Args:
        user: User object
        showcase: TrophyShowcaseConfig object
    
    Returns:
        List of error messages (empty if valid)
    
    Examples:
        >>> errors = validate_showcase_config(user, showcase)
        >>> errors
        ['Border "master" is not unlocked']
    """
    errors = []
    
    # Validate border
    if not is_border_unlocked(user, showcase.border):
        errors.append(f'Border "{showcase.border}" is not unlocked')
    
    # Validate frame
    if not is_frame_unlocked(user, showcase.frame):
        errors.append(f'Frame "{showcase.frame}" is not unlocked')
    
    # Validate pinned badges belong to user
    user_badge_ids = set(
        UserBadge.objects.filter(user=user).values_list('id', flat=True)
    )
    
    for badge_id in showcase.pinned_badge_ids:
        if badge_id not in user_badge_ids:
            errors.append(f'Badge ID {badge_id} does not belong to this user')
    
    return errors
