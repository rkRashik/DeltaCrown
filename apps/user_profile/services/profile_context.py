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
from django.utils import timezone
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


# ========================================================================
# UP-PHASE2E PART 2: REPUTATION SIGNALS COMPUTATION
# ========================================================================

def _compute_reputation_signals(profile_user: User) -> Dict[str, Any]:
    """
    Compute reputation metrics for profile display.
    
    Returns dictionary with:
    - endorsements_received_count: Total endorsements
    - top_endorsed_skills: Top 3 skills with counts
    - bounty_win_rate: Win percentage (0-100)
    - dispute_rate: Dispute percentage (0-100)
    - reputation_score: Weighted score (0-100)
    
    Formula for reputation_score:
    - Base: 50
    - Wins component: +30 * (wins / (wins + losses)) if matches > 0
    - Endorsements component: +15 * min(1.0, endorsements / 20)
    - Dispute penalty: -10 * (disputes / completed) if completed > 0
    - Floor: 0, Ceiling: 100
    """
    from apps.user_profile.models.endorsements import SkillEndorsement
    from apps.user_profile.models import Bounty, BountyStatus
    from django.db.models import Count, Q
    
    # Initialize with safe defaults
    reputation_data = {
        'endorsements_received_count': 0,
        'top_endorsed_skills': [],
        'bounty_win_rate': 0.0,
        'dispute_rate': 0.0,
        'reputation_score': 50,  # Neutral base score
        'bounty_stats': {
            'completed': 0,
            'won': 0,
            'lost': 0,
            'disputed': 0,
        }
    }
    
    # ========================================================================
    # ENDORSEMENTS
    # ========================================================================
    try:
        endorsements = SkillEndorsement.objects.filter(
            receiver=profile_user,
            is_flagged=False,
        )
        
        endorsements_count = endorsements.count()
        reputation_data['endorsements_received_count'] = endorsements_count
        
        if endorsements_count > 0:
            # Get top 3 skills
            skill_breakdown = endorsements.values('skill_name').annotate(
                count=Count('id')
            ).order_by('-count')[:3]
            
            reputation_data['top_endorsed_skills'] = [
                {
                    'skill': skill['skill_name'],
                    'skill_display': dict(SkillEndorsement._meta.get_field('skill_name').choices).get(
                        skill['skill_name'], skill['skill_name']
                    ),
                    'count': skill['count']
                }
                for skill in skill_breakdown
            ]
    except Exception as e:
        logger.error(f"Error computing endorsements for {profile_user.username}: {e}")
    
    # ========================================================================
    # BOUNTY STATISTICS
    # ========================================================================
    try:
        # Count completed bounties where user was participant
        completed_bounties = Bounty.objects.filter(
            Q(creator=profile_user) | Q(acceptor=profile_user),
            status=BountyStatus.COMPLETED
        )
        
        completed_count = completed_bounties.count()
        won_count = completed_bounties.filter(winner=profile_user).count()
        lost_count = completed_count - won_count
        
        # Count disputed bounties
        disputed_count = Bounty.objects.filter(
            Q(creator=profile_user) | Q(acceptor=profile_user),
            status=BountyStatus.DISPUTED
        ).count()
        
        reputation_data['bounty_stats'] = {
            'completed': completed_count,
            'won': won_count,
            'lost': lost_count,
            'disputed': disputed_count,
        }
        
        # Calculate win rate
        if completed_count > 0:
            reputation_data['bounty_win_rate'] = round((won_count / completed_count) * 100, 1)
        
        # Calculate dispute rate
        total_bounties = completed_count + disputed_count
        if total_bounties > 0:
            reputation_data['dispute_rate'] = round((disputed_count / total_bounties) * 100, 1)
    
    except Exception as e:
        logger.error(f"Error computing bounty stats for {profile_user.username}: {e}")
    
    # ========================================================================
    # REPUTATION SCORE (Weighted Formula)
    # ========================================================================
    try:
        score = 50  # Neutral base
        
        # Component 1: Win Rate (30 points max)
        # Only counts if user has played matches
        if reputation_data['bounty_stats']['completed'] > 0:
            win_rate_ratio = reputation_data['bounty_stats']['won'] / reputation_data['bounty_stats']['completed']
            score += int(30 * win_rate_ratio)
        
        # Component 2: Endorsements (15 points max)
        # Caps at 20 endorsements for full credit
        endorsement_ratio = min(1.0, endorsements_count / 20) if endorsements_count > 0 else 0
        score += int(15 * endorsement_ratio)
        
        # Component 3: Dispute Penalty (-10 points per 10% dispute rate)
        # Heavy penalty for high dispute rates
        if reputation_data['dispute_rate'] > 0:
            penalty = int((reputation_data['dispute_rate'] / 10) * 10)
            score -= min(penalty, 30)  # Cap penalty at -30
        
        # Floor and ceiling
        score = max(0, min(100, score))
        reputation_data['reputation_score'] = score
        
        # Reputation tier (for UI display)
        if score >= 90:
            reputation_data['reputation_tier'] = 'Legend'
            reputation_data['reputation_tier_color'] = 'gold'
        elif score >= 75:
            reputation_data['reputation_tier'] = 'Veteran'
            reputation_data['reputation_tier_color'] = 'purple'
        elif score >= 50:
            reputation_data['reputation_tier'] = 'Rising Star'
            reputation_data['reputation_tier_color'] = 'cyan'
        else:
            reputation_data['reputation_tier'] = 'Rookie'
            reputation_data['reputation_tier_color'] = 'gray'
    
    except Exception as e:
        logger.error(f"Error computing reputation score for {profile_user.username}: {e}")
        reputation_data['reputation_score'] = 50  # Failsafe
    
    return reputation_data


# ========================================================================
# UP-PHASE-1A: Unified Profile Context Builder
# ========================================================================

def build_profile_context(request_user: Optional[User], profile_user: User) -> Dict[str, Any]:
    """
    Unified context builder for all profile views - consolidates all context logic.
    
    This is the SINGLE SOURCE OF TRUTH for profile context. Replaces scattered
    context-building logic in view functions.
    
    Architecture:
    - Detects owner vs visitor automatically
    - Applies privacy rules via ProfilePermissionChecker
    - Gates sensitive data (wallet owner-only)
    - Integrates ALL services: loadout, bounty, endorsement, trophy_showcase, etc.
    - Returns ONLY safe primitives (no raw ORM objects)
    
    Args:
        request_user: User viewing the profile (None for anonymous)
        profile_user: User whose profile is being viewed
        
    Returns:
        Complete context dict with 75+ keys:
        
        Core Profile:
        - profile: Basic profile data (username, bio, avatar, etc.)
        - user_profile: UserProfile model instance
        - profile_user: User model instance
        - is_owner: bool
        - can_view: bool
        - permissions: Dict of permission flags
        
        Stats & Metrics:
        - user_stats: Match/tournament stats
        - follower_count, following_count, is_following
        - bounty_stats: Bounty performance metrics
        
        Social & Teams:
        - user_teams: Active team memberships
        - social_links: External links (Twitch, Twitter, etc.)
        - endorsements: Peer recognition summary
        
        Game Data:
        - pinned_passports, unpinned_passports: Game profiles
        - hardware_gear: Loadout (mouse, keyboard, etc.)
        - game_configs: Per-game settings
        
        Content:
        - stream_config: Live stream embed (if active)
        - pinned_highlight, highlight_clips: Video highlights
        - trophy_showcase: Equipped/unlocked cosmetics
        - about_items: Facebook-style about section
        
        Challenges:
        - active_bounties: Open bounties (limited view)
        - completed_bounties: Recent completed bounties
        
        Owner-Only:
        - wallet: Balance and transactions (NEVER exposed to non-owners)
        - wallet_visible: bool gate for template conditionals
        
    Privacy Rules:
    - Wallet: Owner-only, no exceptions
    - Loadout: Respects is_public field on LoadoutItem
    - Match history: Controlled by privacy settings
    - Social links: Privacy-filtered
    - About items: Per-item visibility rules
    
    Example:
        >>> # Public profile view
        >>> context = build_profile_context(request.user, target_user)
        >>> return render(request, 'profile/public.html', context)
        >>>
        >>> # Owner viewing own profile
        >>> context = build_profile_context(request.user, request.user)
        >>> assert context['is_owner'] == True
        >>> assert context['wallet'] is not None
    """
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.services import (
        loadout_service,
        bounty_service,
        endorsement_service,
        trophy_showcase_service
    )
    from apps.user_profile.models import (
        UserProfile,
        UserProfileStats,
        ProfileShowcase,
        UserBadge,
        SocialLink,
        Follow,
        ProfileAboutItem,
        StreamConfig,
        HighlightClip,
        PinnedHighlight,
    )
    from apps.user_profile.utils import get_user_profile_safe
    from apps.teams.models import TeamMembership
    from apps.games.models import Game
    from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
    
    # Initialize context
    context = {}
    
    # Determine ownership
    is_owner = bool(request_user and request_user.is_authenticated and request_user.id == profile_user.id)
    context['is_owner'] = is_owner
    context['profile_user'] = profile_user
    
    # Get UserProfile model instance
    try:
        user_profile = get_user_profile_safe(profile_user)
        context['user_profile'] = user_profile
    except Exception as e:
        logger.error(f"Failed to load profile for {profile_user.username}: {e}")
        return {
            'can_view': False,
            'is_owner': is_owner,
            'error': 'Profile could not be loaded'
        }
    
    # Check visibility policy
    from apps.user_profile.services.privacy_policy import ProfilePermissionChecker
    permissions = ProfilePermissionChecker.get_profile_permissions(
        viewer=request_user if request_user and request_user.is_authenticated else None,
        target_user=profile_user
    )
    
    if not permissions.get('can_view_profile'):
        return {
            'can_view': False,
            'is_owner': is_owner,
            'error': 'This profile is private'
        }
    
    context['can_view'] = True
    context['permissions'] = permissions
    
    # ========================================================================
    # CORE PROFILE DATA
    # ========================================================================
    visible_fields = ProfileVisibilityPolicy.get_visible_fields(request_user, user_profile)
    context['profile'] = _build_basic_profile_data(user_profile, profile_user, visible_fields)
    
    # ========================================================================
    # STATS & METRICS
    # ========================================================================
    try:
        stats = UserProfileStats.objects.get(user_profile=user_profile)
        context['user_stats'] = {
            'total_matches': stats.total_matches,
            'total_wins': stats.total_wins,
            'win_rate': round((stats.total_wins / stats.total_matches * 100) if stats.total_matches > 0 else 0, 1),
            'tournaments_played': stats.tournaments_played,
            'tournaments_won': stats.tournaments_won,
            'total_kills': getattr(stats, 'total_kills', 0),
            'total_deaths': getattr(stats, 'total_deaths', 0),
            'kd_ratio': round((getattr(stats, 'total_kills', 0) / getattr(stats, 'total_deaths', 1)) if getattr(stats, 'total_deaths', 0) > 0 else 0, 2)
        }
    except UserProfileStats.DoesNotExist:
        context['user_stats'] = {
            'total_matches': 0,
            'total_wins': 0,
            'win_rate': 0,
            'tournaments_played': 0,
            'tournaments_won': 0,
            'total_kills': 0,
            'total_deaths': 0,
            'kd_ratio': 0
        }
    
    # Follower counts
    context['follower_count'] = Follow.objects.filter(following=profile_user).count()
    context['following_count'] = Follow.objects.filter(follower=profile_user).count()
    context['is_following'] = False
    if request_user and request_user.is_authenticated and request_user != profile_user:
        context['is_following'] = Follow.objects.filter(
            follower=request_user,
            following=profile_user
        ).exists()
    
    # ========================================================================
    # GAME PASSPORTS (Pinned/Unpinned)
    # ========================================================================
    try:
        all_passports = GamePassportService.get_all_passports(user=profile_user)
        
        # Attach team badge data to each passport
        for passport in all_passports:
            team_membership = TeamMembership.objects.filter(
                profile=user_profile,
                team__game=passport.game,
                status=TeamMembership.Status.ACTIVE
            ).select_related('team').first()
            
            passport.current_team = team_membership.team if team_membership else None
        
        pinned_passports = [p for p in all_passports if p.is_pinned]
        unpinned_passports = [p for p in all_passports if not p.is_pinned]
        
        context['pinned_passports'] = pinned_passports
        context['unpinned_passports'] = unpinned_passports
        context['MAX_PINNED_GAMES'] = 6
    except Exception as e:
        logger.warning(f"Failed to load game passports for {profile_user.username}: {e}")
        context['pinned_passports'] = []
        context['unpinned_passports'] = []
        context['MAX_PINNED_GAMES'] = 6
    
    # ========================================================================
    # TEAMS & TOURNAMENTS
    # ========================================================================
    user_teams = TeamMembership.objects.filter(
        profile=user_profile,
        status=TeamMembership.Status.ACTIVE
    ).select_related('team').order_by('-team__created_at')[:10]
    
    games_map = {g.slug: g.display_name for g in Game.objects.all()}
    
    context['user_teams'] = [
        {
            'id': tm.team.id,
            'slug': tm.team.slug,
            'name': tm.team.name,
            'tag': tm.team.tag,
            'game': games_map.get(tm.team.game, tm.team.game),
            'game_slug': tm.team.game,
            'role': tm.role,
            'logo_url': tm.team.logo.url if tm.team.logo else None,
            'is_captain': tm.role == 'CAPTAIN',
        }
        for tm in user_teams
    ]
    
    context['user_tournaments'] = []  # TODO: Implement when tournament app ready
    
    # ========================================================================
    # PROFILE SHOWCASE (About Section Config)
    # ========================================================================
    try:
        showcase = ProfileShowcase.objects.get(user_profile=user_profile)
        context['showcase'] = {
            'enabled_sections': showcase.get_enabled_sections(),
            'section_order': showcase.section_order or [],
            'featured_team_id': showcase.featured_team_id,
            'featured_team_role': showcase.featured_team_role,
            'featured_passport_id': showcase.featured_passport_id,
            'highlights': showcase.highlights or []
        }
    except ProfileShowcase.DoesNotExist:
        context['showcase'] = {
            'enabled_sections': ProfileShowcase.get_default_sections(),
            'section_order': [],
            'featured_team_id': None,
            'featured_team_role': '',
            'featured_passport_id': None,
            'highlights': []
        }
    
    # ========================================================================
    # ACHIEVEMENTS & BADGES
    # ========================================================================
    if permissions.get('can_view_achievements'):
        achievements = UserBadge.objects.filter(
            user=profile_user
        ).select_related('badge').order_by('-earned_at')[:12]
        context['achievements'] = [
            {
                'id': badge.id,
                'name': badge.badge.name,
                'description': badge.badge.description,
                'icon': badge.badge.icon,
                'awarded_at': badge.earned_at,
                'rarity': getattr(badge.badge, 'rarity', 'common')
            }
            for badge in achievements
        ]
    else:
        context['achievements'] = None
    
    # ========================================================================
    # SOCIAL LINKS
    # ========================================================================
    if permissions.get('can_view_social_links'):
        social_links = SocialLink.objects.filter(user=profile_user).order_by('platform')
        context['social_links'] = [
            {
                'platform': link.platform,
                'url': link.url,
                'handle': link.handle
            }
            for link in social_links
        ]
    else:
        context['social_links'] = None
    
    # ========================================================================
    # MATCH HISTORY
    # ========================================================================
    if permissions.get('can_view_match_history'):
        from apps.tournaments.models import Match, Registration
        from django.db.models import Q
        
        user_registration_ids = list(
            Registration.objects.filter(
                user=profile_user,
                is_deleted=False
            ).values_list('id', flat=True)
        )
        
        if user_registration_ids:
            matches = Match.objects.filter(
                Q(participant1_id__in=user_registration_ids) | Q(participant2_id__in=user_registration_ids),
                state__in=['completed', 'disputed'],
                is_deleted=False
            ).select_related('tournament').order_by('-scheduled_time')[:10]
            
            context['match_history'] = [
                {
                    'id': match.id,
                    'tournament_name': match.tournament.name if match.tournament else 'Unknown',
                    'game': match.tournament.game if match.tournament else None,
                    'participant1_name': match.participant1_name or 'Participant 1',
                    'participant2_name': match.participant2_name or 'Participant 2',
                    'participant1_score': match.participant1_score,
                    'participant2_score': match.participant2_score,
                    'winner_id': match.winner_id,
                    'scheduled_time': match.scheduled_time,
                    'state': match.state,
                    'is_user_winner': match.winner_id in user_registration_ids if match.winner_id else False
                }
                for match in matches
            ]
        else:
            context['match_history'] = []
    else:
        context['match_history'] = None
    
    # ========================================================================
    # ABOUT ITEMS (Facebook-style About Section)
    # ========================================================================
    is_follower = permissions.get('is_follower', False)
    about_items = ProfileAboutItem.objects.filter(
        user_profile=user_profile,
        is_active=True
    ).order_by('order_index', '-created_at')
    
    filtered_about_items = []
    for item in about_items:
        viewer_user = request_user if request_user and request_user.is_authenticated else None
        if item.can_be_viewed_by(viewer_user, is_follower):
            filtered_about_items.append({
                'id': item.id,
                'item_type': item.item_type,
                'display_text': item.display_text,
                'icon_emoji': item.icon_emoji,
                'visibility': item.visibility
            })
    
    context['about_items'] = filtered_about_items
    
    # ========================================================================
    # STREAM CONFIG (Live Stream Embed)
    # ========================================================================
    try:
        stream_config = StreamConfig.objects.select_related('user').get(
            user=profile_user,
            is_active=True
        )
        context['stream_config'] = {
            'platform': stream_config.platform,
            'embed_url': stream_config.embed_url,
            'title': stream_config.title or f"{profile_user.username}'s stream",
            'stream_url': stream_config.stream_url,
        }
    except StreamConfig.DoesNotExist:
        context['stream_config'] = None
    
    # ========================================================================
    # HIGHLIGHTS (Pinned + All Clips)
    # ========================================================================
    try:
        pinned = PinnedHighlight.objects.select_related('clip', 'clip__game').get(user=profile_user)
        context['pinned_highlight'] = {
            'id': pinned.clip.id,
            'title': pinned.clip.title,
            'embed_url': pinned.clip.embed_url,
            'thumbnail_url': pinned.clip.thumbnail_url,
            'platform': pinned.clip.platform,
            'game': pinned.clip.game.display_name if pinned.clip.game else None,
            'created_at': pinned.clip.created_at,
        }
    except PinnedHighlight.DoesNotExist:
        context['pinned_highlight'] = None
    
    highlights = HighlightClip.objects.filter(
        user=profile_user
    ).select_related('game').order_by('display_order', '-created_at')[:20]
    
    context['highlight_clips'] = [
        {
            'id': clip.id,
            'title': clip.title,
            'description': getattr(clip, 'description', ''),
            'embed_url': clip.embed_url,
            'thumbnail_url': clip.thumbnail_url,
            'platform': clip.platform,
            'video_id': clip.video_id,
            'game': clip.game.display_name if clip.game else None,
            'display_order': clip.display_order,
            'created_at': clip.created_at,
            'is_pinned': context['pinned_highlight'] and clip.id == context['pinned_highlight']['id'],
        }
        for clip in highlights
    ]
    context['can_add_more_clips'] = len(context['highlight_clips']) < 20
    
    # ========================================================================
    # LOADOUT (Hardware + Game Configs) - UP-PHASE-2C2
    # ========================================================================
    loadout_data = loadout_service.get_complete_loadout(
        user=profile_user,
        public_only=not is_owner
    )
    
    # Hardware gear organized by category
    context['hardware_gear'] = {
        'mouse': loadout_data['hardware'].get('MOUSE'),
        'keyboard': loadout_data['hardware'].get('KEYBOARD'),
        'headset': loadout_data['hardware'].get('HEADSET'),
        'monitor': loadout_data['hardware'].get('MONITOR'),
        'mousepad': loadout_data['hardware'].get('MOUSEPAD'),
    }
    context['has_loadout'] = loadout_service.has_loadout(profile_user)
    
    # Game configs with enhanced data for display
    context['game_configs'] = [
        {
            'id': config.id,
            'game': config.game.display_name,
            'game_slug': config.game.slug,
            'settings': config.settings,
            'notes': config.notes,
            'is_public': config.is_public,
            'updated_at': config.updated_at,
            'dpi': config.settings.get('dpi', 800),
            'sensitivity': config.settings.get('sensitivity', 0.5),
            'resolution': config.settings.get('resolution', '1920x1080'),
            'crosshair': config.settings.get('crosshair_code', ''),
            'effective_dpi': config.get_effective_dpi() if hasattr(config, 'get_effective_dpi') else (
                config.settings.get('dpi', 800) * config.settings.get('sensitivity', 0.5)
            ),
        }
        for config in loadout_data['game_configs']
    ]
    
    # Loadout context for templates
    context['loadout'] = {
        'gear': context['hardware_gear'],
        'game_configs': context['game_configs'],
        'search_tags': [],  # Optional for future search functionality
    }
    
    # ========================================================================
    # TROPHY SHOWCASE (Equipped + Unlocked Cosmetics) - UP-PHASE-2C2
    # ========================================================================
    showcase_data = trophy_showcase_service.get_showcase_data(profile_user)
    
    context['trophy_showcase'] = {
        'equipped_border': showcase_data['equipped']['border'],
        'equipped_frame': showcase_data['equipped']['frame'],
        'unlocked_borders': showcase_data['unlocked']['borders'],
        'unlocked_frames': showcase_data['unlocked']['frames'],
        'pinned_badges': showcase_data.get('pinned_badges', []),
    }
    
    # Showcase context for inventory tab
    context['showcase'] = {
        'equipped': {
            'border': showcase_data['equipped']['border'],
            'frame': showcase_data['equipped']['frame'],
            'badges': showcase_data.get('pinned_badges', [])[:3],  # Max 3 pinned badges
        },
        'unlocked': [
            *[{'type': 'border', 'item': item} for item in showcase_data['unlocked']['borders']],
            *[{'type': 'frame', 'item': item} for item in showcase_data['unlocked']['frames']],
        ],
        'pinned_badges': showcase_data.get('pinned_badges', []),
    }
    
    # ========================================================================
    # ENDORSEMENTS (Peer Recognition)
    # ========================================================================
    endorsements_summary = endorsement_service.get_endorsements_summary(profile_user)
    
    context['endorsements'] = {
        'total_count': endorsements_summary['total_count'],
        'by_skill': endorsements_summary['by_skill'],
        'top_skill': endorsements_summary.get('top_skill'),
        'recent_endorsements': [
            {
                'skill': e.skill_name,
                'skill_display': e.get_skill_name_display(),
                'endorser': e.endorser.username,
                'match_id': e.match_id,
                'created_at': e.created_at,
            }
            for e in endorsements_summary.get('recent_endorsements', [])[:5]
        ],
    }
    
    # ========================================================================
    # BOUNTIES (Peer Challenges) - UP-PHASE-2C2
    # ========================================================================
    from apps.user_profile.models import Bounty
    
    bounty_stats = bounty_service.get_user_bounty_stats(profile_user)
    context['bounty_stats'] = {
        'created_count': bounty_stats['created_count'],
        'accepted_count': bounty_stats['accepted_count'],
        'won_count': bounty_stats['won_count'],
        'lost_count': bounty_stats['lost_count'],
        'win_rate': bounty_stats['win_rate'],
        'total_earnings': bounty_stats['total_earnings'],
        'total_wagered': bounty_stats['total_wagered'],
    }
    
    # Open bounties (created by user, waiting for acceptor)
    open_bounties = Bounty.objects.filter(
        creator=profile_user,
        status='open'
    ).select_related('game').order_by('-created_at')[:5]
    
    # In-progress bounties (user is creator or acceptor, active match)
    in_progress_bounties = Bounty.objects.filter(
        models.Q(creator=profile_user) | models.Q(acceptor=profile_user),
        status__in=['accepted', 'in_progress', 'pending_result']
    ).select_related('game', 'creator', 'acceptor').order_by('-created_at')[:5]
    
    # Completed bounties (recently finished)
    completed_bounties = Bounty.objects.filter(
        models.Q(creator=profile_user) | models.Q(acceptor=profile_user),
        status='completed'
    ).select_related('game', 'creator', 'acceptor', 'winner').order_by('-completed_at')[:10]
    
    context['bounties'] = {
        'open': [
            {
                'id': bounty.id,
                'title': bounty.title,
                'description': bounty.description,
                'game': bounty.game.display_name if bounty.game else None,
                'game_slug': bounty.game.slug if bounty.game else None,
                'stake_amount': bounty.stake_amount,
                'status': bounty.status,
                'created_at': bounty.created_at,
                'expires_at': bounty.expires_at,
                'is_expired': bounty.expires_at and bounty.expires_at < timezone.now(),
                'mode': '1v1',  # Default, can be extracted from description/metadata
            }
            for bounty in open_bounties
        ],
        'in_progress': [
            {
                'id': bounty.id,
                'title': bounty.title,
                'game': bounty.game.display_name if bounty.game else None,
                'game_slug': bounty.game.slug if bounty.game else None,
                'stake_amount': bounty.stake_amount,
                'status': bounty.status,
                'status_display': bounty.get_status_display(),
                'creator': bounty.creator.username,
                'acceptor': bounty.acceptor.username if bounty.acceptor else None,
                'accepted_at': bounty.accepted_at,
                'mode': '1v1',
                'has_acceptance': hasattr(bounty, 'acceptance') and bounty.acceptance is not None,
                'has_proof': hasattr(bounty, 'proofs') and bounty.proofs.exists(),
            }
            for bounty in in_progress_bounties
        ],
        'completed': [
            {
                'id': bounty.id,
                'title': bounty.title,
                'game': bounty.game.display_name if bounty.game else None,
                'game_slug': bounty.game.slug if bounty.game else None,
                'stake_amount': bounty.stake_amount,
                'payout_amount': bounty.payout_amount,
                'winner': bounty.winner.username if bounty.winner else None,
                'winner_id': bounty.winner_id,
                'completed_at': bounty.completed_at,
                'was_winner': bounty.winner_id == profile_user.id if bounty.winner_id else False,
                'mode': '1v1',
            }
            for bounty in completed_bounties
        ],
        'stats': {
            'open_count': open_bounties.count() if hasattr(open_bounties, 'count') else len(open_bounties),
            'in_progress_count': in_progress_bounties.count() if hasattr(in_progress_bounties, 'count') else len(in_progress_bounties),
            'completed_count': completed_bounties.count() if hasattr(completed_bounties, 'count') else len(completed_bounties),
        }
    }
    
    # ========================================================================
    # POSTS (Community Integration) - UP-PHASE-2C2
    # ========================================================================
    try:
        from apps.community.models import Post
        
        # Get user's posts (limit 20)
        user_posts = Post.objects.filter(
            author=profile_user
        ).select_related('author').order_by('-created_at')[:20]
        
        context['posts'] = {
            'enabled': True,
            'items': [
                {
                    'id': post.id,
                    'content': post.content[:200] + ('...' if len(post.content) > 200 else ''),
                    'full_content': post.content,
                    'created_at': post.created_at,
                    'updated_at': post.updated_at,
                    'like_count': getattr(post, 'like_count', 0),
                    'comment_count': getattr(post, 'comment_count', 0),
                    'url': post.get_absolute_url() if hasattr(post, 'get_absolute_url') else None,
                }
                for post in user_posts
            ]
        }
    except (ImportError, AttributeError):
        # Community app not installed or Post model doesn't exist
        context['posts'] = {
            'enabled': False,
            'items': []
        }
    
    # ========================================================================
    # LIVE FEED (Tournament Match Detection)
    # ========================================================================
    try:
        from apps.tournaments.models import Match as TournamentMatch, Tournament
        from django.urls import reverse
        
        # Find any live match where user is a participant
        live_match = TournamentMatch.objects.filter(
            state=TournamentMatch.LIVE,
            is_deleted=False
        ).filter(
            models.Q(participant1_id=profile_user.id) | 
            models.Q(participant2_id=profile_user.id)
        ).select_related('tournament').first()
        
        if live_match:
            # Determine opponent
            if live_match.participant1_id == profile_user.id:
                opponent_name = live_match.participant2_name or "Opponent"
            else:
                opponent_name = live_match.participant1_name or "Opponent"
            
            # Build match URL
            try:
                match_url = reverse('tournaments:match_detail', kwargs={
                    'slug': live_match.tournament.slug,
                    'match_id': live_match.id
                })
            except Exception:
                match_url = None
            
            context['live_feed'] = {
                'is_live': True,
                'title': live_match.tournament.name if live_match.tournament else 'Live Match',
                'subtitle': f'Round {live_match.round_number} • vs {opponent_name}',
                'cta_label': 'Watch Match',
                'cta_url': match_url,
                'stream_url': live_match.stream_url if live_match.stream_url else None,
            }
        else:
            context['live_feed'] = {
                'is_live': False,
                'title': 'No live events',
                'subtitle': 'Check back during tournaments',
                'cta_label': None,
                'cta_url': None,
                'stream_url': None,
            }
    except Exception as e:
        logger.warning(f"Failed to detect live match for {profile_user.username}: {e}")
        context['live_feed'] = {
            'is_live': False,
            'title': 'No live events',
            'subtitle': 'Check back during tournaments',
            'cta_label': None,
            'cta_url': None,
            'stream_url': None,
        }
    
    # ========================================================================
    # WALLET (Owner-Only - NEVER Expose to Non-Owners)
    # ========================================================================
    if is_owner:
        try:
            wallet, _ = DeltaCrownWallet.objects.get_or_create(user=profile_user)
            context['wallet'] = wallet
            context['wallet_visible'] = True
            context['wallet_transactions'] = DeltaCrownTransaction.objects.filter(
                wallet=wallet
            ).select_related('transaction_type').order_by('-timestamp')[:10]
        except Exception as e:
            logger.warning(f"Failed to load wallet data for {profile_user.username}: {e}")
            context['wallet'] = None
            context['wallet_visible'] = False
            context['wallet_transactions'] = []
    else:
        context['wallet'] = None
        context['wallet_visible'] = False
        context['wallet_transactions'] = []
    
    # ========================================================================
    # NAVIGATION SECTIONS
    # ========================================================================
    nav_sections = [
        {'id': 'stats', 'label': 'Stats'},
        {'id': 'passports', 'label': 'Passports'},
        {'id': 'teams', 'label': 'Teams'},
        {'id': 'tournaments', 'label': 'Tournaments'},
    ]
    
    if is_owner:
        nav_sections.extend([
            {'id': 'economy', 'label': 'Economy'},
            {'id': 'shop', 'label': 'Shop'},
        ])
    
    nav_sections.extend([
        {'id': 'activity', 'label': 'Activity'},
        {'id': 'about', 'label': 'About'},
    ])
    
    if context.get('achievements'):
        nav_sections.insert(-2, {'id': 'achievements', 'label': 'Achievements'})
    
    context['nav_sections'] = nav_sections
    context['current_page'] = 'profile'
    
    # ========================================================================
    # UP-PHASE2D: INTERACTIVE OWNER FLOWS - All Games for Bounty Modal
    # ========================================================================
    if is_owner:
        from apps.core.models import Game
        context['games'] = Game.objects.filter(is_active=True).order_by('name')
    
    # ========================================================================
    # UP-PHASE2E PART 2: REPUTATION SIGNALS & ENDORSEMENTS
    # ========================================================================
    context['reputation'] = _compute_reputation_signals(profile_user)
    
    return context

