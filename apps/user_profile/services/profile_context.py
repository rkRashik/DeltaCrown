"""
Profile Context Service (UP-FE-MVP-01)

Safe context builder for profile views. Returns ONLY safe primitives/JSON
with NO raw ORM objects for public views.

Architecture:
- Uses ProfileVisibilityPolicy for field filtering
- Pulls from UserProfile, game_profiles JSON, UserProfileStats, UserActivity
- Owner-only: wallet balance, transactions, privacy settings, edit actions
- Public: display name, bio, games, stats, activity feed (filtered)

Example:
    >>> context = build_public_profile_context(request.user, 'johndoe', requested_sections=['stats', 'activity'])
    >>> return render(request, 'user_profile/v2/profile_public.html', context)
"""
from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
import logging

from apps.user_profile.models import UserProfile, UserProfileStats, UserActivity, PrivacySettings
from apps.user_profile.services.privacy_policy import ProfileVisibilityPolicy
from apps.user_profile.utils import get_user_profile_safe

User = get_user_model()
logger = logging.getLogger(__name__)


def build_public_profile_context(
    viewer: Optional[User],
    username: str,
    requested_sections: Optional[List[str]] = None,
    activity_page: int = 1,
    activity_per_page: int = 25
) -> Dict[str, Any]:
    """
    Build safe profile context dictionary with NO raw ORM objects.
    
    Args:
        viewer: User viewing the profile (None for anonymous)
        username: Username of profile to view
        requested_sections: List of sections to include (default: all)
            Options: 'basic', 'stats', 'activity', 'games', 'social', 'owner_only'
        activity_page: Page number for activity feed (default: 1)
        activity_per_page: Items per page for activity feed (default: 25)
        
    Returns:
        Dict with keys:
            - profile: Safe profile dict (display_name, bio, avatar, etc.)
            - stats: Stats dict (tournaments_played, matches_won, etc.) [if requested]
            - activity: Paginated activity feed [if requested]
            - games: List of game profile dicts [if requested]
            - social: Social links dict [if requested]
            - owner_data: Owner-only data (wallet, settings) [if is_owner]
            - is_owner: bool
            - can_view: bool
            - error: str [if profile not found or access denied]
            
    Example:
        >>> # Public view
        >>> context = build_public_profile_context(request.user, 'johndoe')
        >>> 
        >>> # Owner view with specific sections
        >>> context = build_public_profile_context(
        ...     request.user,
        ...     request.user.username,
        ...     requested_sections=['basic', 'stats', 'owner_only']
        ... )
    """
    # Set default sections if not specified
    if requested_sections is None:
        requested_sections = ['basic', 'stats', 'activity', 'games', 'social']
    
    # Find target user and profile
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return {
            'profile': None,
            'can_view': False,
            'is_owner': False,
            'error': f'User @{username} not found'
        }
    
    try:
        profile = get_user_profile_safe(target_user)
    except Exception as e:
        logger.error(f"Failed to load profile for {username}: {e}")
        return {
            'profile': None,
            'can_view': False,
            'is_owner': False,
            'error': 'Profile could not be loaded'
        }
    
    # Check if viewer can see this profile
    can_view = ProfileVisibilityPolicy.can_view_profile(viewer, profile)
    if not can_view:
        return {
            'profile': None,
            'can_view': False,
            'is_owner': False,
            'error': 'This profile is private'
        }
    
    # Determine if viewer is owner (ensure boolean result)
    is_owner = bool(viewer and viewer.is_authenticated and viewer.id == target_user.id)
    
    # Get visible fields based on viewer role
    visible_fields = ProfileVisibilityPolicy.get_visible_fields(viewer, profile)
    
    # Build context dictionary
    context = {
        'can_view': True,  # Always True if we reach this point (privacy check passed)
        'is_owner': is_owner,
        'error': None
    }
    
    # SECTION: Basic Profile Data
    if 'basic' in requested_sections:
        context['profile'] = _build_basic_profile_data(profile, target_user, visible_fields)
    
    # SECTION: Stats
    if 'stats' in requested_sections:
        context['stats'] = _build_stats_data(profile)
    
    # SECTION: Activity Feed
    if 'activity' in requested_sections:
        context['activity'] = _build_activity_feed(
            profile,
            is_owner,
            page=activity_page,
            per_page=activity_per_page
        )
    
    # SECTION: Game Profiles
    if 'games' in requested_sections:
        context['games'] = _build_game_profiles_data(profile)
    
    # SECTION: Social Links
    if 'social' in requested_sections:
        context['social'] = _build_social_links_data(profile, visible_fields)
    
    # SECTION: Owner-Only Data
    if 'owner_only' in requested_sections and is_owner:
        context['owner_data'] = _build_owner_data(target_user, profile)
    
    return context


def _build_basic_profile_data(
    profile: UserProfile,
    user: User,
    visible_fields: set
) -> Dict[str, Any]:
    """
    Build basic profile data dict (SAFE - no ORM objects).
    
    Args:
        profile: UserProfile model instance
        user: User model instance
        visible_fields: Set of fields visible to viewer
        
    Returns:
        Dict with basic profile fields (all primitives/JSON)
    """
    data = {
        'username': user.username,
        'display_name': profile.display_name,
        'public_id': profile.public_id,
        'uuid': str(profile.uuid),
        'slug': profile.slug or user.username,
        'bio': profile.bio if profile.bio else '',
        'created_at': profile.created_at.isoformat() if hasattr(profile, 'created_at') else None,
        'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
    }
    
    # Avatar and banner (URLs, not file objects)
    data['avatar_url'] = profile.avatar.url if profile.avatar else None
    data['banner_url'] = profile.banner.url if profile.banner else None
    
    # Location (if visible)
    if 'country' in visible_fields:
        data['country'] = profile.country
        data['region'] = profile.region if hasattr(profile, 'region') else None
    
    # Pronouns (if present)
    if 'pronouns' in visible_fields:
        data['pronouns'] = profile.pronouns if hasattr(profile, 'pronouns') else None
    
    # Level/XP (if visible)
    if 'level' in visible_fields:
        data['level'] = profile.level if hasattr(profile, 'level') else 1
        data['xp'] = profile.xp if hasattr(profile, 'xp') else 0
    
    return data


def _build_stats_data(profile: UserProfile) -> Dict[str, Any]:
    """
    Build stats data dict from UserProfileStats.
    
    Args:
        profile: UserProfile model instance
        
    Returns:
        Dict with stats (all primitives)
    """
    try:
        stats = UserProfileStats.objects.get(user_profile=profile)
        return {
            'tournaments_played': stats.tournaments_played,
            'tournaments_won': stats.tournaments_won,
            'tournaments_top3': stats.tournaments_top3,
            'matches_played': stats.matches_played,
            'matches_won': stats.matches_won,
            # Note: teams/followers computed separately, not in stats model
            'teams_joined': 0,  # Computed from team memberships if needed
            'current_team': None,
            'followers_count': 0,  # Computed from Follow model if needed
            'following_count': 0,
            'total_activity_count': 0,  # Can be computed from UserActivity count
            'last_activity_at': stats.last_match_at.isoformat() if stats.last_match_at else None,
        }
    except UserProfileStats.DoesNotExist:
        # Return zeros if stats don't exist yet
        return {
            'tournaments_played': 0,
            'tournaments_won': 0,
            'tournaments_top3': 0,
            'matches_played': 0,
            'matches_won': 0,
            'teams_joined': 0,
            'current_team': None,
            'followers_count': 0,
            'following_count': 0,
            'total_activity_count': 0,
            'last_activity_at': None,
        }


def _build_activity_feed(
    profile: UserProfile,
    is_owner: bool,
    page: int = 1,
    per_page: int = 25
) -> Dict[str, Any]:
    """
    Build paginated activity feed.
    
    Args:
        profile: UserProfile model instance
        is_owner: Whether viewer is profile owner
        page: Page number
        per_page: Items per page
        
    Returns:
        Dict with activity feed data (paginated)
    """
    # Query activity events for this profile
    # Owner sees all; public sees only public events
    if is_owner:
        activities = UserActivity.objects.filter(
            user=profile.user  # ForeignKey to User, not UserProfile
        ).order_by('-timestamp')  # Field is 'timestamp', not 'created_at'
    else:
        # Public: only show public-safe events (no PROFILE_UPDATED, etc.)
        public_event_types = [
            'tournament_registered',
            'tournament_completed',
            'match_completed',
            'achievement_earned',
            'badge_earned',
            'level_up',
        ]
        activities = UserActivity.objects.filter(
            user=profile.user,  # ForeignKey to User, not UserProfile
            event_type__in=public_event_types
        ).order_by('-timestamp')  # Field is 'timestamp', not 'created_at'
    
    # Paginate
    paginator = Paginator(activities, per_page)
    page_obj = paginator.get_page(page)
    
    # Convert to safe dicts (NO ORM objects)
    activity_list = []
    for activity in page_obj:
        activity_list.append({
            'id': activity.id,
            'event_type': activity.event_type,
            'event_data': activity.metadata or {},  # Field is 'metadata', not 'event_data'
            'created_at': activity.timestamp.isoformat(),  # Field is 'timestamp', not 'created_at'
        })
    
    return {
        'activities': activity_list,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }


def _build_game_profiles_data(profile: UserProfile) -> List[Dict[str, Any]]:
    """
    Build game profiles list from game_profiles JSON field.
    
    Args:
        profile: UserProfile model instance
        
    Returns:
        List of game profile dicts
    """
    game_profiles = profile.game_profiles or {}
    
    # Convert to list of dicts
    profiles_list = []
    for game_slug, game_data in game_profiles.items():
        if isinstance(game_data, dict):
            profile_dict = {
                'game': game_slug,
                'ign': game_data.get('ign', ''),
                'role': game_data.get('role', ''),
                'rank': game_data.get('rank', ''),
                'platform': game_data.get('platform', ''),
                'metadata': game_data.get('metadata', {}),
            }
            profiles_list.append(profile_dict)
    
    return profiles_list


def _build_social_links_data(
    profile: UserProfile,
    visible_fields: set
) -> Dict[str, Any]:
    """
    Build social links dict from SocialLink model.
    
    Args:
        profile: UserProfile model instance
        visible_fields: Set of fields visible to viewer
        
    Returns:
        Dict with social links (all strings)
    """
    from apps.user_profile.models import SocialLink
    
    social = {}
    
    # Query SocialLink model for this user
    social_links = SocialLink.objects.filter(user=profile.user)
    
    # Build dict with platform as key and handle/url as value
    for link in social_links:
        # Extract username/handle from URL for cleaner display
        platform = link.platform
        
        # Use handle if available, otherwise extract from URL
        if link.handle:
            social[platform] = link.handle
        else:
            # Try to extract username from URL
            url = link.url
            if platform == 'twitch' and 'twitch.tv/' in url:
                social[platform] = url.split('twitch.tv/')[-1].strip('/')
            elif platform == 'youtube':
                if '@' in url:
                    social[platform] = url.split('@')[-1].split('/')[0]
                elif 'channel/' in url:
                    social[platform] = url.split('channel/')[-1].strip('/')
                else:
                    social[platform] = url
            elif platform == 'twitter' or platform == 'x':
                if 'twitter.com/' in url:
                    social['twitter'] = url.split('twitter.com/')[-1].strip('/')
                elif 'x.com/' in url:
                    social['twitter'] = url.split('x.com/')[-1].strip('/')
            elif platform == 'discord':
                social[platform] = link.url  # Discord uses invite links
            elif platform == 'instagram' and 'instagram.com/' in url:
                social[platform] = url.split('instagram.com/')[-1].strip('/')
            elif platform == 'tiktok':
                if '@' in url:
                    social[platform] = url.split('@')[-1].split('/')[0]
                else:
                    social[platform] = url.split('tiktok.com/')[-1].strip('/')
            elif platform == 'facebook' and 'facebook.com/' in url:
                social[platform] = url.split('facebook.com/')[-1].strip('/')
            else:
                social[platform] = link.url
    
    return social


def _build_owner_data(user: User, profile: UserProfile) -> Dict[str, Any]:
    """
    Build owner-only data (wallet, privacy settings, edit permissions).
    
    Args:
        user: User model instance (owner)
        profile: UserProfile model instance
        
    Returns:
        Dict with owner-only data
    """
    owner_data = {
        'can_edit': True,
        'email': user.email,
    }
    
    # Wallet balance (if available)
    try:
        from apps.economy.models import DeltaCrownWallet
        wallet = DeltaCrownWallet.objects.get(user=user)
        owner_data['wallet'] = {
            'balance': float(wallet.cached_balance) if wallet.cached_balance else 0.0,
            'lifetime_earnings': float(wallet.lifetime_earnings) if hasattr(wallet, 'lifetime_earnings') and wallet.lifetime_earnings else 0.0,
        }
    except Exception:
        owner_data['wallet'] = {
            'balance': 0.0,
            'lifetime_earnings': 0.0,
        }
    
    # Privacy settings
    try:
        privacy_settings = PrivacySettings.objects.get(user_profile=profile)
        owner_data['privacy_settings'] = {
            'profile_visibility': privacy_settings.profile_visibility if hasattr(privacy_settings, 'profile_visibility') else 'public',
            'show_email': privacy_settings.show_email,
            'show_phone': privacy_settings.show_phone,
            'show_real_name': privacy_settings.show_real_name,
            'allow_friend_requests': privacy_settings.allow_friend_requests,
            'show_online_status': privacy_settings.show_online_status if hasattr(privacy_settings, 'show_online_status') else True,
        }
    except PrivacySettings.DoesNotExist:
        owner_data['privacy_settings'] = {
            'profile_visibility': 'public',
            'show_email': False,
            'show_phone': False,
            'show_real_name': False,
            'allow_friend_requests': True,
            'show_online_status': True,
        }
    
    return owner_data
