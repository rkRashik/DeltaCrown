"""
Team Detail Context Builder

Provides schema-resilient context generation for team_detail.html template.
Implements the Team Detail Page Contract (docs/contracts/TEAM_DETAIL_PAGE_CONTRACT.md).
"""
from typing import Optional, Dict, Any, List
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import escape
from django.core.cache import cache

from apps.teams.models import Team  # Using legacy Team model (PHASE 5 migration not complete)
from apps.games.services import GameService


# Fallback URLs for missing images
FALLBACK_URLS = {
    'team_logo': '/static/img/teams/placeholder-logo.png',
    'team_banner': '/static/img/teams/placeholder-banner.png',
    'org_logo': '/static/img/orgs/placeholder-logo.png',
    'user_avatar': '/static/img/users/default-avatar.png',
    'stream_thumbnail': '/static/img/streams/placeholder-thumbnail.png',
}


def get_team_detail_context(
    *,
    team_slug: str,
    viewer: Optional[User] = None,
    request=None
) -> Dict[str, Any]:
    """
    Build complete context for team detail page.
    
    Returns all keys specified in Team Detail Page Contract with safe defaults.
    Never raises AttributeError for missing model fields.
    
    Args:
        team_slug: Team URL slug identifier
        viewer: Current user (None for anonymous)
        request: HTTP request object (optional, for URL building)
        
    Returns:
        dict: Complete context matching contract specification
        
    Raises:
        Team.DoesNotExist: If team_slug is invalid
    """
    # Fetch team with optimizations (guard against missing relationships)
    # Note: Legacy Team model has no organization FK, and game is CharField (not FK)
    try:
        team = Team.objects.select_related('ranking').get(slug=team_slug)
    except Team.DoesNotExist:
        raise
    
    # Check privacy and accessibility using schema-resilient logic
    can_view = _check_team_accessibility(team, viewer)
    is_authorized = can_view or _is_team_member_or_staff(team, viewer)
    
    # Determine viewer role
    viewer_role = _get_viewer_role(team, viewer)
    
    # Build permissions dict
    permissions = _build_permissions(team, viewer, viewer_role)
    
    # Privacy gate: restrict data for unauthorized viewers of private teams
    is_private_restricted = _is_private_team(team) and not is_authorized
    
    # Build context sections
    context = {
        'team': _build_team_context(team, is_private_restricted),
        'organization': _build_organization_context(team),
        'viewer': _build_viewer_context(viewer, viewer_role),
        'permissions': permissions,
        'ui': _build_ui_context(team, viewer_role),
        'roster': _build_roster_context(team, is_private_restricted),
        'stats': _build_stats_context(team, is_private_restricted),
        'streams': _build_streams_context(team, is_private_restricted),
        'partners': _build_partners_context(team, is_private_restricted),
        'merch': _build_merch_context(team, is_private_restricted),
        'pending_actions': _build_pending_actions_context(team, viewer, is_authorized),
        'page': _build_page_context(team, request),
        
        # Legacy compatibility flags (preserve existing template expectations)
        'enable_demo_remote': False,  # Disabled per PHASE 1A directive
    }
    
    return context


# ============================================================================
# TIER 1 BUILDERS (Critical identity fields)
# ============================================================================

def _build_team_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build team identity context (Tier 1 + Tier 2 if authorized)."""
    # Tier 1: Always present (even for private teams)
    team_data = {
        'name': getattr(team, 'name', 'Unknown Team'),
        'slug': getattr(team, 'slug', ''),
        'tag': getattr(team, 'tag', ''),
        'logo_url': _safe_image_url(getattr(team, 'logo', None), FALLBACK_URLS['team_logo']),
        'banner_url': _safe_image_url(getattr(team, 'banner', None), FALLBACK_URLS['team_banner']),
        'visibility': _get_team_visibility(team),
        'game': _safe_game_context(team),
    }
    
    # Tier 2+: Only if not restricted
    if not is_restricted:
        team_data.update({
            'tagline': getattr(team, 'tagline', ''),
            'avatar_url': team_data['logo_url'],  # Reuse logo as avatar
            'team_type': getattr(team, 'team_type', 'independent'),
            'theme': getattr(team, 'theme', 'CROWN'),
            'status': getattr(team, 'status', 'active'),
            'founded_date': _safe_date(getattr(team, 'founded_date', None)),
            'total_members': _safe_int(getattr(team, 'member_count', 0)),
            'total_wins': _safe_int(getattr(team, 'total_wins', 0)),
            'total_losses': _safe_int(getattr(team, 'total_losses', 0)),
            'crown_points': _safe_int(getattr(team, 'crown_points', 0)),
            'rank': _safe_int(getattr(team, 'rank', 0)),
            'social_links': _safe_dict(getattr(team, 'social_links', {})),
        })
    else:
        # Restricted: empty defaults for Tier 2+
        team_data.update({
            'tagline': '',
            'avatar_url': team_data['logo_url'],
            'team_type': 'independent',
            'theme': 'CROWN',
            'status': 'private',
            'founded_date': None,
            'total_members': 0,
            'total_wins': 0,
            'total_losses': 0,
            'crown_points': 0,
            'rank': 0,
            'social_links': {},
        })
    
    return team_data


def _build_organization_context(team: Team) -> Optional[Dict[str, Any]]:
    """Build organization context (nullable)."""
    # Legacy Team model has no organization FK - always return None
    try:
        if hasattr(team, 'organization'):
            org = team.organization
            if org is None:
                return None
            
            return {
                'name': getattr(org, 'name', ''),
                'slug': getattr(org, 'slug', ''),
                'logo_url': _safe_image_url(getattr(org, 'logo', None), FALLBACK_URLS['org_logo']),
                'url': f'/orgs/{getattr(org, "slug", "")}/' if getattr(org, 'slug', '') else '',
                'type': getattr(org, 'type', 'esports'),
            }
        return None
    except AttributeError:
        # No organization relationship exists
        return None


def _build_viewer_context(viewer: Optional[User], role: str) -> Dict[str, Any]:
    """Build viewer context (always present)."""
    if viewer and viewer.is_authenticated:
        return {
            'is_authenticated': True,
            'username': getattr(viewer, 'username', 'User'),
            'role': role,
            'avatar_url': _get_user_avatar(viewer),
        }
    else:
        return {
            'is_authenticated': False,
            'username': 'Anonymous',
            'role': 'PUBLIC',
            'avatar_url': FALLBACK_URLS['user_avatar'],
        }


def _build_permissions(team: Team, viewer: Optional[User], role: str) -> Dict[str, bool]:
    """Build permissions flags."""
    # Use schema-resilient visibility check
    can_view_private = _check_team_accessibility(team, viewer)
    
    return {
        'can_view_private': can_view_private,
        'can_edit_team': role in ('OWNER', 'STAFF'),
        'can_manage_roster': role in ('OWNER', 'STAFF'),
        'can_invite': role in ('OWNER', 'STAFF', 'MEMBER'),
        'can_view_operations': role in ('OWNER', 'STAFF', 'MEMBER'),
        'can_view_financial': role == 'OWNER',
    }


def _build_ui_context(team: Team, role: str) -> Dict[str, Any]:
    """Build UI configuration."""
    return {
        'theme': getattr(team, 'theme', 'CROWN'),
        'enable_demo_remote': False,  # Disabled per PHASE 1A directive
        'enable_streams': True,  # Feature flag (always enabled for now)
        'enable_merch': False,  # Future feature
        'skeleton_loading': False,  # Could be based on request parameter
    }


def _build_page_context(team: Team, request) -> Dict[str, Any]:
    """Build page metadata."""
    team_name = getattr(team, 'name', 'Unknown Team')
    banner_url = _safe_image_url(getattr(team, 'banner', None), FALLBACK_URLS['team_banner'])
    
    # Build canonical URL if request available
    canonical_url = ''
    if request:
        canonical_url = request.build_absolute_uri()
    
    return {
        'title': f'{team_name} | Team HQ | DeltaCrown',
        'description': getattr(team, 'tagline', f'Official page for {team_name}'),
        'og_image': banner_url,
        'canonical_url': canonical_url,
    }


# ============================================================================
# TIER 2 BUILDERS (Nice to have data)
# ============================================================================

def _build_roster_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build roster dict with items and count (empty if restricted)."""
    if is_restricted:
        return {'items': [], 'count': 0}
    
    # Try to fetch roster (guard against missing relationship)
    # Note: relationship is 'memberships' not 'members'
    try:
        # Fetch active memberships with user data AND their profiles for avatars
        # This prevents N+1 queries when accessing avatar URLs
        # Legacy TeamMembership has 'profile' FK (UserProfile), not 'user' FK (User)
        # UserProfile has 'user' FK to User model
        memberships = team.memberships.select_related(
            'profile',           # FK to UserProfile
            'profile__user'      # UserProfile.user → User
        ).filter(
            status='ACTIVE'
        ).order_by('-joined_at')[:20]  # Limit to 20
        
        roster_items = [
            {
                'username': getattr(member.profile.user, 'username', 'Unknown') if member.profile else 'Unknown',
                'display_name': getattr(member.profile.user, 'username', 'Unknown') if member.profile else 'Unknown',
                'avatar_url': _get_user_avatar(member.profile.user if member.profile else None),
                'role': getattr(member, 'role', 'PLAYER'),
                'player_role': getattr(member, 'player_role', ''),  # Game-specific role
                'status': getattr(member, 'status', 'ACTIVE'),
                'joined_date': _safe_date(getattr(member, 'joined_at', None)),  # Field is joined_at not joined_date
                'is_captain': getattr(member, 'is_tournament_captain', False),
            }
            for member in memberships
        ]
        
        return {
            'items': roster_items,
            'count': len(roster_items)
        }
    except AttributeError:
        # No memberships relationship or other schema issue
        return {'items': [], 'count': 0}


def _build_stats_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build stats from TeamRanking (Gate 4B - Option A: Ranking-only stats)."""
    if is_restricted:
        # Private team: hide all stats for non-members
        return {
            'crown_points': 0,
            'tier': 'UNRANKED',
            'global_rank': None,
            'regional_rank': None,
            'streak_count': 0,
            'is_hot_streak': False,
            'rank_change_24h': 0,
            'last_activity_date': None,
        }
    
    # Try to fetch TeamRanking (OneToOne relationship)
    try:
        ranking = team.ranking
        return {
            'crown_points': getattr(ranking, 'current_cp', 0),
            'tier': getattr(ranking, 'tier', 'UNRANKED'),
            'global_rank': getattr(ranking, 'global_rank', None),
            'regional_rank': getattr(ranking, 'regional_rank', None),
            'streak_count': getattr(ranking, 'streak_count', 0),
            'is_hot_streak': getattr(ranking, 'is_hot_streak', False),
            'rank_change_24h': getattr(ranking, 'rank_change_24h', 0),
            'last_activity_date': getattr(ranking, 'last_activity_date', None),
        }
    except AttributeError:
        # No ranking exists: return safe defaults
        return {
            'crown_points': 0,
            'tier': 'UNRANKED',
            'global_rank': None,
            'regional_rank': None,
            'streak_count': 0,
            'is_hot_streak': False,
            'rank_change_24h': 0,
            'last_activity_date': None,
        'streak': {'type': '', 'count': 0},  # Tier 3: defer calculation
    }


def _build_streams_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    Build streams/social links from team social media fields.
    
    Returns list of social media platforms with links.
    Privacy: Returns empty list for restricted (private + unauthorized) viewers.
    
    Note: Real "live stream" detection (Twitch API) is future work.
    For now, returns static social links from Team model.
    """
    if is_restricted:
        return []
    
    streams = []
    
    # Map legacy Team social fields to stream items
    social_platforms = [
        ('twitch', team.twitch, 'Twitch', 'https://static-cdn.jtvnw.net/jtv_user_pictures/twitch-logo.png'),
        ('twitter', team.twitter, 'Twitter/X', 'https://abs.twimg.com/icons/apple-touch-icon-192x192.png'),
        ('youtube', team.youtube, 'YouTube', 'https://www.youtube.com/s/desktop/logo.png'),
        ('instagram', team.instagram, 'Instagram', 'https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png'),
    ]
    
    for platform, url, platform_name, default_thumb in social_platforms:
        if url and url.strip():
            streams.append({
                'platform': platform,
                'url': url,
                'title': f"{team.name} on {platform_name}",
                'is_live': False,  # Future: Check Twitch API for live status
                'viewer_count': 0,
                'thumbnail_url': default_thumb,
            })
    
    return streams


def _build_partners_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    Build partners list from TeamSponsor relationships.
    
    Returns list of active sponsors with logo, name, URL, and tier.
    Privacy: Returns empty list for restricted (private + unauthorized) viewers.
    """
    if is_restricted:
        return []
    
    # Query active sponsors (TeamSponsor.team points to teams.Team)
    from apps.teams.models.sponsorship import TeamSponsor
    
    sponsors = team.sponsors.filter(
        status='active',
        is_active=True
    ).order_by('-sponsor_tier', 'sponsor_name')[:10]  # Limit to top 10
    
    partners = []
    for sponsor in sponsors:
        partners.append({
            'name': sponsor.sponsor_name,
            'logo_url': _safe_image_url(sponsor.sponsor_logo.url if sponsor.sponsor_logo else None, 
                                        FALLBACK_URLS['org_logo']),
            'url': sponsor.sponsor_link or '#',
            'tier': sponsor.sponsor_tier or 'partner',
        })
    
    return partners


def _build_merch_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """Build merch list (Tier 3 - future feature)."""
    # Always empty for now
    return []


def _build_pending_actions_context(team: Team, viewer, is_authorized: bool) -> Dict[str, Any]:
    """
    Build pending actions awareness flags for authenticated viewers.
    
    Checks for pending invites and join requests for the viewing user.
    Returns dict with flags indicating available actions.
    
    Privacy: Returns all-false for anonymous or unauthorized viewers.
    """
    if not viewer or not viewer.is_authenticated or not is_authorized:
        return {
            'can_request_to_join': False,
            'has_pending_invite': False,
            'has_pending_request': False,
            'pending_invite_id': None,
            'pending_request_id': None,
        }
    
    # Check if user is already a member
    # Legacy TeamMembership has 'profile' FK (UserProfile), not 'user' FK
    from apps.teams.models import TeamMembership, TeamInvite, TeamJoinRequest
    
    # Get viewer's UserProfile
    viewer_profile = getattr(viewer, 'userprofile', None) if hasattr(viewer, 'userprofile') else None
    
    is_member = TeamMembership.objects.filter(
        team=team,
        profile=viewer_profile,
        status='ACTIVE'
    ).exists() if viewer_profile else False
    
    # Check for pending invite (TeamInvite.invited_user points to UserProfile, not User)
    pending_invite = TeamInvite.objects.filter(
        team=team,
        invited_user=viewer_profile,
        status='PENDING'
    ).first() if viewer_profile else None
    
    # Check for pending join request (TeamJoinRequest.applicant points to UserProfile)
    pending_request = TeamJoinRequest.objects.filter(
        team=team,
        applicant=viewer_profile,
        status='PENDING'
    ).first() if viewer_profile else None
    
    # User can request to join if: not a member, no pending invite, no pending request, team allows requests
    can_request = (
        not is_member and
        not pending_invite and
        not pending_request and
        getattr(team, 'allow_join_requests', True)  # Legacy Team field
    )
    
    return {
        'can_request_to_join': can_request,
        'has_pending_invite': pending_invite is not None,
        'has_pending_request': pending_request is not None,
        'pending_invite_id': pending_invite.id if pending_invite else None,
        'pending_request_id': pending_request.id if pending_request else None,
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _safe_image_url(value, fallback: str) -> str:
    """Safely extract image URL with fallback."""
    if not value:
        return fallback
    
    # Handle FileField/ImageField
    if hasattr(value, 'url'):
        try:
            return value.url
        except (ValueError, AttributeError):
            return fallback
    
    # Handle string URL
    if isinstance(value, str) and value.strip():
        return value.strip()
    
    return fallback


def _safe_game_context(team: Team) -> Dict[str, Any]:
    """Safely extract game context with GameService lookup and caching."""
    # Legacy Team uses 'game' CharField (slug), not 'game_id' FK
    game_slug = getattr(team, 'game', None)
    if not game_slug:
        return {
            'id': None,
            'name': 'Unknown Game',
            'slug': None,
            'logo_url': None,
            'primary_color': '#7c3aed',
        }
    
    # Try cache first (24-hour TTL)
    cache_key = f'game_context:{game_slug}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from database using GameService
    game = GameService.get_game(game_slug)
    
    if game:
        result = {
            'id': game.id,
            'name': game.display_name,
            'slug': game.slug,
            'logo_url': game.logo.url if game.logo else None,
            'primary_color': game.primary_color,
        }
        cache.set(cache_key, result, 86400)  # 24 hours
        return result
    
    # Fallback for invalid game_id
    return {
        'id': team.game_id,
        'name': f'Game #{team.game_id}',
        'slug': None,
        'logo_url': None,
        'primary_color': '#7c3aed',
    }


def _get_team_visibility(team: Team) -> str:
    """Get team visibility status."""
    return getattr(team, 'visibility', 'PUBLIC')


def _is_private_team(team: Team) -> bool:
    """Check if team is private."""
    return _get_team_visibility(team) == 'PRIVATE'


def _get_viewer_role(team: Team, viewer: Optional[User]) -> str:
    """Determine viewer's role relative to team."""
    # Legacy Team has no owner FK - ownership determined by TeamMembership with role='OWNER'
    if not viewer or not viewer.is_authenticated:
        return 'PUBLIC'
    
    # Check if viewer is in team staff/members
    # Legacy TeamMembership has 'profile' FK (UserProfile), not 'user' FK
    try:
        if hasattr(team, 'memberships'):  # Use 'memberships' not 'members'
            viewer_profile = getattr(viewer, 'userprofile', None) if hasattr(viewer, 'userprofile') else None
            if viewer_profile:
                member = team.memberships.filter(profile=viewer_profile).first()
                if member:
                    role = getattr(member, 'role', '').upper()
                    if 'OWNER' in role or 'ADMIN' in role:
                        return 'OWNER'
                    if 'STAFF' in role or 'COACH' in role or 'MANAGER' in role:
                        return 'STAFF'
                    return 'MEMBER'
    except AttributeError:
        pass
    
    return 'PUBLIC'


def _is_team_member_or_staff(team: Team, viewer: Optional[User]) -> bool:
    """Check if viewer is team member or staff."""
    if not viewer or not viewer.is_authenticated:
        return False
    
    role = _get_viewer_role(team, viewer)
    return role in ('OWNER', 'STAFF', 'MEMBER')


def _get_user_avatar(user: User) -> str:
    """Get user avatar URL with fallback."""
    try:
        if hasattr(user, 'profile') and user.profile:
            avatar = getattr(user.profile, 'avatar', None)
            return _safe_image_url(avatar, FALLBACK_URLS['user_avatar'])
    except AttributeError:
        pass
    
    return FALLBACK_URLS['user_avatar']


def _safe_int(value) -> int:
    """Safely convert to int."""
    try:
        return int(value) if value is not None else 0
    except (ValueError, TypeError):
        return 0


def _safe_date(value) -> Optional[str]:
    """Safely convert date to string."""
    if value is None:
        return None
    
    try:
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)
    except:
        return None


def _safe_dict(value) -> dict:
    """Safely ensure dict type."""
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value) -> list:
    """Safely ensure list type."""
    if isinstance(value, list):
        return value
    return []


def _check_team_accessibility(team: Team, viewer: Optional[User]) -> bool:
    """
    Check if viewer can access team details.
    
    Returns True for public/unlisted teams or if viewer is a team member/staff.
    Returns False for private teams with unauthorized viewers.
    """
    # If viewer is team member/staff, always allow
    if _is_team_member_or_staff(team, viewer):
        return True
    
    # Check privacy using real visibility field
    visibility = getattr(team, 'visibility', 'PUBLIC')
    if visibility == 'PRIVATE':
        return False  # Private team, viewer not authorized
    
    # Public or unlisted teams are accessible
    return True
