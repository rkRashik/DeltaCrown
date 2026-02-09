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

from apps.organizations.models import Team  # vNext Team model (Phase 2B migration)
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
    # Note: vNext Team model has organization FK (nullable), game_id FK (not CharField)
    # Phase 3A-A: Legacy TeamRanking removed. Ranking data now from apps/competition/
    try:
        team = Team.objects.select_related('organization', 'organization__ranking').get(slug=team_slug)
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
            'description': getattr(team, 'description', ''),
            'avatar_url': team_data['logo_url'],  # Reuse logo as avatar
            'team_type': getattr(team, 'team_type', 'independent'),
            'theme': getattr(team, 'theme', 'CROWN'),
            'primary_color': getattr(team, 'primary_color', '#3B82F6'),
            'accent_color': getattr(team, 'accent_color', '#10B981'),
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
            'description': '',
            'avatar_url': team_data['logo_url'],
            'team_type': 'independent',
            'theme': 'CROWN',
            'primary_color': '#3B82F6',
            'accent_color': '#10B981',
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
    # vNext Team model has organization FK (nullable)
    try:
        if hasattr(team, 'organization'):
            org = team.organization
            if org is None:
                return None
            
            # Empire Score from OrganizationRanking (Phase 4)
            ranking = getattr(org, 'ranking', None)
            empire_score = getattr(ranking, 'empire_score', 0) if ranking else 0
            global_rank = getattr(ranking, 'global_rank', None) if ranking else None
            
            return {
                'name': getattr(org, 'name', ''),
                'slug': getattr(org, 'slug', ''),
                'logo_url': _safe_image_url(getattr(org, 'logo', None), FALLBACK_URLS['org_logo']),
                'badge_url': _safe_image_url(getattr(org, 'badge', None), ''),
                'url': f'/orgs/{getattr(org, "slug", "")}/' if getattr(org, 'slug', '') else '',
                'hub_url': f'/orgs/{getattr(org, "slug", "")}/hub/' if getattr(org, 'slug', '') else '',
                'control_plane_url': f'/orgs/{getattr(org, "slug", "")}/control-plane/' if getattr(org, 'slug', '') else '',
                'type': getattr(org, 'type', 'esports'),
                'is_verified': getattr(org, 'is_verified', False),
                'enforce_brand': getattr(org, 'enforce_brand', False),
                'empire_score': empire_score,
                'global_rank': global_rank,
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
    """Build permissions flags using TeamMembership.get_permission_list() and Organization CEO check."""
    from apps.organizations.models import TeamMembership, Organization
    from apps.organizations.choices import MembershipStatus
    
    # Use schema-resilient visibility check
    can_view_private = _check_team_accessibility(team, viewer)
    
    # CRITICAL FIX: Check if viewer is Organization CEO (has all permissions)
    is_org_ceo = False
    if viewer and viewer.is_authenticated and team.organization_id:
        try:
            org = team.organization  # Already loaded via select_related — no extra query
            if org and org.ceo_id == viewer.id:
                is_org_ceo = True
        except Exception:
            pass
    
    # Organization CEO has all permissions even without explicit membership
    if is_org_ceo:
        return {
            'can_view_private': True,
            'can_edit_team': True,
            'can_manage_roster': True,
            'can_invite': True,
            'can_view_operations': True,
            'can_view_financial': True,
            'can_report_matches': True,
            'is_member': True,  # CEO is implicitly a member
        }
    
    # Get actual permissions from membership
    if viewer and viewer.is_authenticated:
        membership = TeamMembership.objects.filter(
            team=team,
            user=viewer,
            status=MembershipStatus.ACTIVE
        ).first()
        
        if membership:
            perms = membership.get_permission_list()
            has_all = 'ALL' in perms
            # Phase 3A-C: Report matches permission (OWNER or MANAGER only)
            can_report_matches = has_all or role in ('OWNER', 'MANAGER')
            return {
                'can_view_private': can_view_private,
                'can_edit_team': has_all or 'edit_team' in perms,
                'can_manage_roster': has_all or 'edit_roster' in perms,
                'can_invite': has_all or 'edit_roster' in perms,
                'can_view_operations': has_all or role in ('OWNER', 'MANAGER', 'COACH'),
                'can_view_financial': has_all or role == 'OWNER',
                'can_report_matches': can_report_matches,
                'is_member': True,
            }
    
    # Anonymous or non-member: no permissions
    return {
        'can_view_private': can_view_private,
        'can_edit_team': False,
        'can_manage_roster': False,
        'can_invite': False,
        'can_view_operations': False,
        'can_view_financial': False,
        'can_report_matches': False,
        'is_member': False,
    }


def _build_ui_context(team: Team, role: str) -> Dict[str, Any]:
    """Build UI configuration."""
    return {
        'theme': getattr(team, 'theme', 'CROWN'),
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
    # vNext TeamMembership has 'user' FK pointing to User model, related_name='vnext_memberships'
    try:
        from apps.organizations.choices import MembershipStatus
        
        # Fetch active memberships with user data (use vnext_memberships related name)
        memberships = team.vnext_memberships.select_related(
            'user', 'user__profile'  # vNext FK to User + profile for avatar
        ).filter(
            status=MembershipStatus.ACTIVE
        ).order_by('-joined_at')[:20]  # Limit to 20
        
        # Prefetch game passport data for all roster members
        game_passports = {}
        if team.game_id:
            try:
                from apps.user_profile.models import GameProfile
                user_ids = [m.user_id for m in memberships]
                passports = GameProfile.objects.filter(
                    user_id__in=user_ids,
                    game_id=team.game_id
                ).select_related('user')
                for gp in passports:
                    game_passports[gp.user_id] = {
                        'ign': getattr(gp, 'in_game_name', '') or getattr(gp, 'ign', '') or '',
                        'rank': getattr(gp, 'rank_name', '') or '',
                        'region': getattr(gp, 'region', '') or '',
                        'has_passport': True,
                    }
            except Exception:
                pass  # GameProfile not available or schema mismatch
        
        roster_items = []
        for member in memberships:
            user = member.user
            username = getattr(user, 'username', 'Unknown')
            profile = getattr(user, 'profile', None)
            display = member.display_name or ''
            if not display and profile:
                dn = getattr(profile, 'display_name', '') or getattr(profile, 'gamer_tag', '')
                if dn:
                    display = dn
            if not display:
                display = username

            # Resolve avatar: roster_image > profile avatar > default
            avatar_url = None
            if member.roster_image:
                avatar_url = member.roster_image.url
            else:
                avatar_url = _get_user_avatar(user)
            
            # Get game passport for this user
            passport_data = game_passports.get(user.id, {})

            roster_items.append({
                'username': username,
                'display_name': display,
                'avatar_url': avatar_url,
                # Owner privacy: hide OWNER role on public page if hide_ownership is set
                'role': ('PLAYER' if getattr(member, 'hide_ownership', False) and getattr(member, 'role', '') == 'OWNER' else getattr(member, 'role', 'PLAYER')),
                'roster_slot': getattr(member, 'roster_slot', '') or '',
                'player_role': getattr(member, 'player_role', ''),
                'status': getattr(member, 'status', 'ACTIVE'),
                'joined_date': _safe_date(getattr(member, 'joined_at', None)),
                'is_captain': getattr(member, 'is_tournament_captain', False),
                'user_profile_url': f'/u/{username}/',
                'user_id': user.id,
                'country': getattr(profile, 'country', '') if profile else '',
                'bio': (getattr(profile, 'bio', '') or '')[:120] if profile else '',
                'game_passport': passport_data,
                'hide_ownership': getattr(member, 'hide_ownership', False),
            })
        
        return {
            'items': roster_items,
            'count': len(roster_items)
        }
    except AttributeError:
        # No memberships relationship or other schema issue
        return {'items': [], 'count': 0}


def _get_default_stats() -> Dict[str, Any]:
    """Default stats when no ranking exists (Phase 3A-A safe fallback)."""
    return {
        'score': 0,
        'tier': 'UNRANKED',
        'rank': None,
        'percentile': 0.0,
        'global_score': 0,
        'global_tier': 'UNRANKED',
        'verified_match_count': 0,
        'confidence_level': 'PROVISIONAL',
        'breakdown': {},
    }


def _build_stats_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build stats from CompetitionService (Phase 10)."""
    if is_restricted:
        # Private team: hide stats for non-members
        return _get_default_stats()
    
    # Phase 10: Use CompetitionService for team rank
    if not getattr(settings, 'COMPETITION_APP_ENABLED', False):
        return _get_default_stats()
    
    try:
        from apps.competition.services import CompetitionService
        
        # Get team rank via service (supports both global and game-specific)
        game_id = None
        if hasattr(team, 'game_id') and team.game_id:
            game_id = team.game_id
        
        rank_data = CompetitionService.get_team_rank(team.id, game_id=game_id)
        
        if rank_data and rank_data.get('has_ranking'):
            return {
                'score': rank_data.get('score', 0),
                'tier': rank_data.get('tier', 'UNRANKED'),
                'rank': rank_data.get('rank'),
                'percentile': rank_data.get('percentile', 0.0),
                'global_score': rank_data.get('global_score', 0),
                'global_tier': rank_data.get('global_tier', 'UNRANKED'),
                'verified_match_count': rank_data.get('verified_match_count', 0),
                'confidence_level': rank_data.get('confidence_level', 'PROVISIONAL'),
                'breakdown': rank_data.get('breakdown', {}),
            }
        else:
            # No ranking yet
            return _get_default_stats()
    except Exception as e:
        # Competition service error - log and return defaults
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error fetching team rank for {team.slug}: {e}")
        return _get_default_stats()


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
    
    # Map vNext Team social fields to stream items (use _url suffix)
    social_platforms = [
        ('twitch', getattr(team, 'twitch_url', None), 'Twitch', 'https://static-cdn.jtvnw.net/jtv_user_pictures/twitch-logo.png'),
        ('twitter', getattr(team, 'twitter_url', None), 'Twitter/X', 'https://abs.twimg.com/icons/apple-touch-icon-192x192.png'),
        ('youtube', getattr(team, 'youtube_url', None), 'YouTube', 'https://www.youtube.com/s/desktop/logo.png'),
        ('instagram', getattr(team, 'instagram_url', None), 'Instagram', 'https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png'),
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
    
    NOTE Phase 3: TeamSponsor.team FK points to legacy teams.Team, not vNext Team.
    vNext Team objects do not have .sponsors relationship. Returns empty for now.
    """
    if is_restricted:
        return []
    
    # vNext Team has no sponsors relationship yet (Phase 3 migration needed)
    if not hasattr(team, 'sponsors'):
        return []
    
    # Legacy TeamSponsor model removed (Phase B cleanup).
    # Sponsors feature will be rebuilt on organizations models in a future phase.
    return []


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
    # vNext TeamMembership has 'user' FK (User), not 'profile' FK
    from apps.organizations.models import TeamMembership, TeamInvite
    from apps.organizations.choices import MembershipStatus
    
    # vNext: Query by user directly (not profile)
    is_member = TeamMembership.objects.filter(
        team=team,
        user=viewer,
        status=MembershipStatus.ACTIVE
    ).exists()
    
    # Check for pending invite (vNext TeamInvite.invited_user is User FK)
    pending_invite = TeamInvite.objects.filter(
        team=team,
        invited_user=viewer,
        status='PENDING'
    ).first()
    
    # vNext organizations app has no TeamJoinRequest model yet (Phase 3 work)
    # For now, always None (no join request functionality)
    pending_request = None
    
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
    # vNext Team uses 'game_id' FK (int), legacy used 'game' CharField (slug)
    game_id = getattr(team, 'game_id', None)
    game_slug = getattr(team, 'game', None)  # Fallback for legacy
    
    # If we have game_id (vNext), fetch by ID
    if game_id:
        # Fetch from database using GameService
        try:
            from apps.games.models import Game
            game = Game.objects.get(id=game_id)
            return {
                'id': game.id,
                'name': game.display_name,
                'slug': game.slug,
                'logo_url': game.logo.url if game.logo else None,
                'primary_color': game.primary_color,
            }
        except Game.DoesNotExist:
            # Fallback for invalid game_id
            return {
                'id': game_id,
                'name': f'Game #{game_id}',
                'slug': None,
                'logo_url': None,
                'primary_color': '#7c3aed',
            }
    
    # Legacy path: game is a CharField slug
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
    
    # Fallback for invalid slug
    return {
        'id': None,
        'name': 'Unknown Game',
        'slug': game_slug,
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
    """Determine viewer's role relative to team (returns truthful role)."""
    from apps.organizations.models import TeamMembership
    from apps.organizations.choices import MembershipStatus, MembershipRole
    
    if not viewer or not viewer.is_authenticated:
        return 'PUBLIC'
    
    # Query vNext TeamMembership with user FK
    try:
        membership = TeamMembership.objects.filter(
            team=team,
            user=viewer,
            status=MembershipStatus.ACTIVE
        ).first()
        
        if membership:
            # Return truthful role (no mapping to 'OWNER' for MANAGER)
            role = membership.role
            if role == MembershipRole.OWNER:
                return 'OWNER'
            elif role == MembershipRole.MANAGER:
                return 'MANAGER'
            elif role == MembershipRole.COACH:
                return 'COACH'
            elif role in (MembershipRole.PLAYER, MembershipRole.SUBSTITUTE):
                return 'PLAYER'
            else:
                return 'MEMBER'
    except Exception:
        pass
    
    return 'PUBLIC'


def _is_team_member_or_staff(team: Team, viewer: Optional[User]) -> bool:
    """Check if viewer is team member or staff."""
    if not viewer or not viewer.is_authenticated:
        return False
    
    role = _get_viewer_role(team, viewer)
    return role in ('OWNER', 'MANAGER', 'COACH', 'PLAYER', 'MEMBER')


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
    except Exception:
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
