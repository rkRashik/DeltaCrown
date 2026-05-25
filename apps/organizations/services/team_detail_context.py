"""
Team Detail Context Builder

Provides schema-resilient context generation for team_detail.html template.
Implements the Team Detail Page Contract (docs/contracts/TEAM_DETAIL_PAGE_CONTRACT.md).
"""
import hashlib
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import quote
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.html import escape
from django.utils import timezone
from django.core.cache import cache

from apps.organizations.models import Team  # vNext Team model (Phase 2B migration)
from apps.games.services import GameService

logger = logging.getLogger(__name__)


# Fallback URLs for missing images
FALLBACK_URLS = {
    'team_banner': '/static/img/teams/placeholder-banner.png',
    'stream_thumbnail': '/static/img/streams/placeholder-thumbnail.png',
}


def _build_initials(label: str, fallback: str = 'DC') -> str:
    value = (label or '').strip()
    if not value:
        return fallback

    parts = [part for part in value.split() if part]
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    else:
        compact = ''.join(ch for ch in value if ch.isalnum())
        initials = (compact[:2] or value[:2] or fallback).upper()

    return ''.join(ch for ch in initials if ch.isalnum())[:2] or fallback


def _fallback_avatar_bg(seed: str) -> str:
    palette = ['#1f2937', '#0f4c81', '#0b6e4f', '#7c2d12', '#5b21b6', '#065f46']
    digest = hashlib.sha256((seed or 'deltacrown').encode('utf-8')).hexdigest()
    return palette[int(digest[:2], 16) % len(palette)]


def _build_initials_avatar_data_uri(label: str, *, seed: Optional[str] = None, fallback: str = 'DC') -> str:
    initials = _build_initials(label, fallback=fallback)
    bg = _fallback_avatar_bg(seed or label)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
        f'<rect width="128" height="128" fill="{bg}"/>'
        f'<text x="50%" y="53%" text-anchor="middle" dominant-baseline="middle" '
        'fill="#ffffff" font-family="Arial, sans-serif" font-size="46" font-weight="700">'
        f'{initials}</text>'
        '</svg>'
    )
    return f'data:image/svg+xml;utf8,{quote(svg)}'


def _get_team_registration_ids(team: Team) -> List[int]:
    """Return tournament registration participant ids for a team."""
    try:
        from apps.tournaments.models import Registration
        return list(
            Registration.objects.filter(team_id=team.id, is_deleted=False)
            .values_list('id', flat=True)
        )
    except Exception as exc:
        logger.debug("Team registration lookup failed for %s: %s", team.slug, exc)
        return []


def _get_team_participant_ids(team: Team, registration_ids: Optional[List[int]] = None) -> set:
    participant_ids = {team.id}
    participant_ids.update(registration_ids or [])
    return {participant_id for participant_id in participant_ids if participant_id is not None}


def _build_team_participant_q(team: Team, registration_ids: Optional[List[int]] = None):
    from django.db.models import Q

    participant_ids = _get_team_participant_ids(team, registration_ids)
    return Q(participant1_id__in=participant_ids) | Q(participant2_id__in=participant_ids)


def _get_match_side_for_team(match, participant_ids: set) -> Optional[int]:
    if match.participant1_id in participant_ids:
        return 1
    if match.participant2_id in participant_ids:
        return 2
    return None


def _build_registration_team_name_map(participant_ids: set) -> Dict[int, str]:
    """Map registration participant ids to their current team names."""
    if not participant_ids:
        return {}

    try:
        from apps.tournaments.models import Registration
        rows = list(
            Registration.objects.filter(
                id__in=participant_ids,
                is_deleted=False,
                team_id__isnull=False,
            ).values_list('id', 'team_id')
        )
        team_ids = {team_id for _, team_id in rows if team_id}
        team_names = {
            team.id: team.name
            for team in Team.objects.filter(id__in=team_ids).only('id', 'name')
        }
        return {
            reg_id: team_names.get(team_id, '')
            for reg_id, team_id in rows
            if team_names.get(team_id)
        }
    except Exception as exc:
        logger.debug("Registration participant name lookup failed: %s", exc)
        return {}


def _resolve_participant_name(participant_id, fallback: str, registration_team_names: Dict[int, str], team_names=None) -> str:
    if participant_id in registration_team_names:
        return registration_team_names[participant_id]
    if team_names and participant_id in team_names:
        return team_names[participant_id]
    return fallback or (f'Team #{participant_id}' if participant_id else 'TBD')


def get_team_detail_context(
    *,
    team_slug: str,
    viewer: Optional[User] = None,
    request=None,
    team: Optional[Team] = None,
) -> Dict[str, Any]:
    """
    Build complete context for team detail page.
    
    Returns all keys specified in Team Detail Page Contract with safe defaults.
    Never raises AttributeError for missing model fields.
    
    Args:
        team_slug: Team URL slug identifier
        viewer: Current user (None for anonymous)
        request: HTTP request object (optional, for URL building)
        team: Pre-fetched Team instance (skips duplicate DB query if provided)
        
    Returns:
        dict: Complete context matching contract specification
        
    Raises:
        Team.DoesNotExist: If team_slug is invalid
    """
    # Use pre-fetched team from the view, or fetch if not provided
    if team is None:
        try:
            team = Team.objects.select_related(
                'organization', 'organization__ranking'
            ).get(slug=team_slug)
        except Team.DoesNotExist:
            raise
    
    # Compute viewer role once (avoids redundant TeamMembership queries)
    viewer_role = _get_viewer_role(team, viewer)
    is_authorized = viewer_role != 'PUBLIC'
    
    # Privacy gate: restrict data for unauthorized viewers of private teams
    is_private_restricted = _is_private_team(team) and not is_authorized
    
    # Build permissions from already-computed role (no extra query)
    permissions = _build_permissions(team, viewer, viewer_role)
    
    # ── Cached public context (team-specific, 60s TTL) ──
    # These sections are viewer-independent and expensive to compute.
    cache_variant = 'restricted' if is_private_restricted else 'full'
    cache_key = f'team_detail:{team.slug}:{cache_variant}'
    public_ctx = cache.get(cache_key)
    if public_ctx is None:
        public_ctx = {
            'team': _build_team_context(team, is_private_restricted),
            'organization': _build_organization_context(team),
            'roster': _build_roster_context(team, is_private_restricted),
            'stats': _build_stats_context(team, is_private_restricted),
            'leaderboard_stats': _build_leaderboard_stats_context(team, is_private_restricted),
            'streams': _build_streams_context(team, is_private_restricted),
            'partners': _build_partners_context(team, is_private_restricted),
            'merch': _build_merch_context(team, is_private_restricted),
            'journey': _build_journey_context(team, is_private_restricted),
            'announcements': _build_announcements_context(team, is_private_restricted),
            'upcoming_matches': _build_upcoming_matches_context(team, is_private_restricted),
            'trophy_cabinet': _build_trophy_cabinet_context(team, is_private_restricted),
            'media_highlights': _build_media_highlights_context(team, is_private_restricted),
            'challenges': _build_challenges_context(team, is_private_restricted),
            'match_history': _build_match_history_context(team, is_private_restricted),
            'operations_log': _build_operations_log_context(team, is_private_restricted),
            'recruitment': _build_recruitment_context(team, is_private_restricted),
            'sponsors': _build_sponsors_context(team, is_private_restricted),
        }
        cache.set(cache_key, public_ctx, 60)
    
    # ── Live viewer-specific context (cheap queries, never cached) ──
    context = {
        **public_ctx,
        'viewer': _build_viewer_context(viewer, viewer_role),
        'permissions': permissions,
        'ui': _build_ui_context(team, viewer_role),
        'pending_actions': _build_pending_actions_context(
            team, viewer, is_authorized, viewer_role=viewer_role,
        ),
        'follow': _build_follow_context(team, viewer),
        'page': _build_page_context(team, request),
        'training': _build_training_context(team, viewer, is_private_restricted),
        'competitive_actions': _build_competitive_actions_context(team, viewer),
    }
    
    return context


# ============================================================================
# TIER 1 BUILDERS (Critical identity fields)
# ============================================================================

def _build_team_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build team identity context (Tier 1 + Tier 2 if authorized)."""
    team_name = getattr(team, 'name', 'Unknown Team')
    team_logo_fallback = _build_initials_avatar_data_uri(
        team_name,
        seed=getattr(team, 'slug', '') or team_name,
        fallback='TM',
    )

    # Tier 1: Always present (even for private teams)
    team_data = {
        'name': team_name,
        'slug': getattr(team, 'slug', ''),
        'tag': getattr(team, 'tag', ''),
        'logo_url': _safe_image_url(getattr(team, 'logo', None), team_logo_fallback),
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
            'is_recruiting': getattr(team, 'is_recruiting', True),
            'roster_locked': getattr(team, 'roster_locked', False),
            'founded_date': _safe_date(getattr(team, 'founded_date', None)),
            'total_members': _safe_int(getattr(team, 'member_count', 0)),
            'total_wins': _safe_int(getattr(team, 'total_wins', 0)),
            'total_losses': _safe_int(getattr(team, 'total_losses', 0)),
            'crown_points': _safe_int(getattr(team, 'crown_points', 0)),
            'rank': _safe_int(getattr(team, 'rank', 0)),
            # P1: Header metadata fields
            'region': getattr(team, 'region', ''),
            'platform': getattr(team, 'platform', 'PC'),
            # P3: Identity tags
            'playstyle': getattr(team, 'playstyle', ''),
            'playpace': getattr(team, 'playpace', ''),
            'playfocus': getattr(team, 'playfocus', ''),
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
            'is_recruiting': False,
            'roster_locked': True,
            'founded_date': None,
            'total_members': 0,
            'total_wins': 0,
            'total_losses': 0,
            'crown_points': 0,
            'rank': 0,
            'region': '',
            'platform': '',
            'playstyle': '',
            'playpace': '',
            'playfocus': '',
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
            org_name = getattr(org, 'name', '')
            org_logo_fallback = _build_initials_avatar_data_uri(
                org_name or 'Organization',
                seed=getattr(org, 'slug', '') or org_name,
                fallback='OR',
            )
            
            return {
                'name': org_name,
                'slug': getattr(org, 'slug', ''),
                'logo_url': _safe_image_url(getattr(org, 'logo', None), org_logo_fallback),
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
            'avatar_url': _build_initials_avatar_data_uri('Anonymous', seed='anonymous', fallback='AN'),
        }


def _build_permissions(team: Team, viewer: Optional[User], role: str) -> Dict[str, bool]:
    """Build permissions flags using TeamMembership.get_permission_list() and Organization CEO check."""
    from apps.organizations.models import TeamMembership
    from apps.organizations.choices import MembershipStatus
    from apps.organizations.services.team_authority import can_manage_team_profile
    
    # Use schema-resilient visibility check
    can_view_private = _check_team_accessibility(team, viewer)
    
    can_report_matches = can_manage_team_profile(viewer, team)

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
            'can_report_matches': can_report_matches,
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
        'can_report_matches': can_report_matches,
        'is_member': False,
    }


def _build_competitive_actions_context(team: Team, viewer: Optional[User]) -> Dict[str, Any]:
    """Viewer-specific public challenge/Bounty CTA state for team detail."""
    context = {
        'can_challenge': False,
        'reason': 'Login required',
        'challenge_url': '',
        'has_open_bounty': False,
        'open_bounty_count': 0,
        'bounty_url': '/dashboard/competitive/#bounty',
        'managed_team_count': 0,
    }
    if not viewer or not viewer.is_authenticated:
        return context

    try:
        from django.db.models import Q
        from apps.organizations.models import TeamMembership
        from apps.organizations.choices import MembershipStatus

        managed = list(
            TeamMembership.objects
            .filter(user=viewer, status=MembershipStatus.ACTIVE)
            .filter(Q(role__in=['OWNER', 'MANAGER']) | Q(is_tournament_captain=True))
            .exclude(team=team)
            .select_related('team')
            .only('id', 'team_id', 'role', 'is_tournament_captain', 'team__id')
        )
        context['managed_team_count'] = len(managed)
        if managed:
            context['can_challenge'] = True
            context['reason'] = ''
            context['challenge_url'] = (
                f"/dashboard/competitive/?target_team_id={team.pk}"
                f"&target_team_slug={quote(getattr(team, 'slug', '') or '')}"
                f"&target_team_name={quote(getattr(team, 'name', '') or '')}#showdown"
            )
        else:
            context['reason'] = 'Captain or manager authority on another team required'
    except Exception:
        context['reason'] = 'Challenge eligibility could not be verified'

    try:
        from apps.competition.models import Bounty
        open_count = Bounty.objects.filter(
            issuer_team=team,
            is_hitlist=True,
            status='ACTIVE',
            is_public=True,
        ).count()
        context['open_bounty_count'] = open_count
        context['has_open_bounty'] = open_count > 0
        if open_count:
            context['bounty_url'] = '/dashboard/competitive/#bounty'
    except Exception:
        pass

    return context


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

def _get_starting_lineup_size(team: Team) -> int:
    """Get the starting lineup size for a team's game from GameRosterConfig."""
    try:
        from apps.games.models.roster_config import GameRosterConfig
        config = GameRosterConfig.objects.get(game_id=team.game_id)
        return config.min_team_size or 5
    except Exception:
        return 5


def _safe_game_profile_summary(game_profile) -> Dict[str, Any]:
    """Public-safe Game Passport fields for roster display."""
    if not game_profile:
        return {}

    return {
        'game_id': getattr(game_profile, 'game_id', None),
        'ign': getattr(game_profile, 'in_game_name', '') or getattr(game_profile, 'ign', '') or '',
        'in_game_name': getattr(game_profile, 'in_game_name', '') or getattr(game_profile, 'ign', '') or '',
        'rank': getattr(game_profile, 'rank_name', '') or '',
        'rank_name': getattr(game_profile, 'rank_name', '') or '',
        'platform': getattr(game_profile, 'platform', '') or '',
        'region': getattr(game_profile, 'region', '') or '',
        'main_role': getattr(game_profile, 'main_role', '') or '',
        'verification_status': getattr(game_profile, 'verification_status', '') or '',
        'has_passport': True,
    }


def _build_roster_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """Build roster dict with items and count (empty if restricted)."""
    if is_restricted:
        return {'items': [], 'count': 0}
    
    # Try to fetch roster (guard against missing relationship)
    # vNext TeamMembership has 'user' FK pointing to User model, related_name='vnext_memberships'
    try:
        from apps.organizations.choices import MembershipStatus
        
        # Fetch active memberships with user data (use vnext_memberships related name)
        # Order: captain first, then starters, then substitutes, then rest
        from django.db.models import Case, When, Value, IntegerField
        memberships = team.vnext_memberships.select_related(
            'user', 'user__profile'  # vNext FK to User + profile for avatar
        ).filter(
            status=MembershipStatus.ACTIVE
        ).annotate(
            _sort_order=Case(
                When(is_tournament_captain=True, then=Value(0)),
                When(roster_slot='STARTER', then=Value(1)),
                When(roster_slot='SUBSTITUTE', then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('_sort_order', 'joined_at')[:20]  # Limit to 20
        
        # Prefetch game passport data for all roster members
        game_passports = {}
        if team.game_id:
            try:
                from apps.user_profile.models import GameProfile
                user_ids = [m.user_id for m in memberships]
                passports = GameProfile.objects.filter(
                    user_id__in=user_ids,
                    game_id=team.game_id,
                    status=GameProfile.STATUS_ACTIVE,
                    visibility__in=[
                        GameProfile.VISIBILITY_PUBLIC,
                        GameProfile.VISIBILITY_PROTECTED,
                    ],
                ).only(
                    'user_id', 'game_id', 'ign', 'in_game_name', 'rank_name',
                    'platform', 'region', 'main_role', 'verification_status',
                )
                for gp in passports:
                    game_passports[gp.user_id] = _safe_game_profile_summary(gp)
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
                'user_profile_url': f'/@{username}/',
                'user_id': user.id,
                'country': getattr(profile, 'country', '') if profile else '',
                'bio': (getattr(profile, 'bio', '') or '')[:120] if profile else '',
                'game_passport': passport_data,
                'hide_ownership': getattr(member, 'hide_ownership', False),
            })
        
        return {
            'items': roster_items,
            'count': len(roster_items),
            'starting_lineup_size': _get_starting_lineup_size(team),
        }
    except AttributeError:
        # No memberships relationship or other schema issue
        return {'items': [], 'count': 0, 'starting_lineup_size': 5}


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


def _build_leaderboard_stats_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """
    Build leaderboard stats from TeamStats, TeamRanking, and TeamAnalyticsSnapshot.

    Wires real data from leaderboards app for P2 (Streak & Rank) and P5 (dynamic game sections).
    Returns win/loss/draw counts, ELO rating, tier, recent match form, and streaks.
    """
    defaults = {
        'matches_played': 0,
        'matches_won': 0,
        'matches_lost': 0,
        'matches_drawn': 0,
        'tournaments_played': 0,
        'tournaments_won': 0,
        'win_rate': 0.0,
        'elo_rating': None,      # ELO is hidden from frontend
        'tier': 'ROOKIE',
        'current_cp': 0,
        'global_rank': None,
        'activity_score': 0,
        'percentile_rank': 0.0,
        'current_streak': 0,
        'streak_type': '',       # 'W' or 'L'
        'longest_win_streak': 0,
        'recent_form': [],       # List of 'W'/'L'/'D' for last 10 matches
        'trophies_count': 0,
    }

    if is_restricted:
        return defaults

    import logging
    logger = logging.getLogger(__name__)

    game_slug = ''
    if team.game_id:
        try:
            from apps.games.models import Game
            g = Game.objects.only('slug').get(id=team.game_id)
            game_slug = g.slug
        except Exception:
            pass

    # --- TeamStats ---
    try:
        from apps.leaderboards.models import TeamStats
        ts = TeamStats.objects.filter(team=team, game_slug=game_slug).first() if game_slug else None
        if ts:
            defaults['matches_played'] = ts.matches_played or 0
            defaults['matches_won'] = ts.matches_won or 0
            defaults['matches_lost'] = ts.matches_lost or 0
            defaults['matches_drawn'] = ts.matches_drawn or 0
            defaults['tournaments_played'] = ts.tournaments_played or 0
            defaults['tournaments_won'] = ts.tournaments_won or 0
            defaults['win_rate'] = float(ts.win_rate or 0)
    except Exception as e:
        logger.debug(f"TeamStats lookup failed for {team.slug}: {e}")

    # --- Organizations TeamRanking (canonical CP + tier + rank + activity) ---
    try:
        from apps.organizations.models import TeamRanking as OrgTeamRanking
        org_ranking = OrgTeamRanking.objects.filter(team=team).first()
        if org_ranking:
            defaults['tier'] = org_ranking.tier or 'ROOKIE'
            defaults['current_cp'] = org_ranking.current_cp or 0
            defaults['global_rank'] = org_ranking.global_rank
            defaults['activity_score'] = org_ranking.activity_score or 0
            defaults['current_streak'] = abs(org_ranking.streak_count or 0)
            defaults['streak_type'] = 'W' if (org_ranking.streak_count or 0) > 0 else ('L' if (org_ranking.streak_count or 0) < 0 else '')
    except Exception as e:
        logger.debug(f"Organizations TeamRanking lookup failed for {team.slug}: {e}")

    # --- Recent Form (last 10 matches from TeamMatchHistory) ---
    try:
        from apps.leaderboards.models import TeamMatchHistory
        recent = TeamMatchHistory.objects.filter(
            team=team, game_slug=game_slug,
        ).order_by('-id')[:10]
        form = []
        for m in recent:
            if m.is_winner:
                form.append('W')
            elif hasattr(m, 'is_draw') and m.is_draw:
                form.append('D')
            else:
                form.append('L')
        defaults['recent_form'] = form
    except Exception as e:
        logger.debug(f"TeamMatchHistory lookup failed for {team.slug}: {e}")

    # --- Trophy count (tournaments won) ---
    try:
        from apps.tournaments.models import Tournament
        # Count tournaments where this team won (participant_id = team.id and is completed)
        # Simpler: use tournaments_won from TeamStats if available
        if defaults['tournaments_won'] == 0:
            # Fallback: count from TeamMatchHistory where flags contain 'tournament_winner'
            pass
    except Exception:
        pass

    defaults['trophies_count'] = defaults['tournaments_won']

    # --- Canonical competitive results (Showdown + tournament matches + Bounty outcomes) ---
    canonical = _build_canonical_competitive_stats(team)
    if canonical['matches_played'] > defaults['matches_played']:
        defaults['matches_played'] = canonical['matches_played']
        defaults['matches_won'] = canonical['matches_won']
        defaults['matches_lost'] = canonical['matches_lost']
        defaults['matches_drawn'] = canonical['matches_drawn']
        defaults['win_rate'] = canonical['win_rate']
        defaults['recent_form'] = canonical['recent_form'] or defaults['recent_form']
        defaults['current_streak'] = canonical['current_streak']
        defaults['streak_type'] = canonical['streak_type']
        defaults['longest_win_streak'] = max(defaults['longest_win_streak'], canonical['longest_win_streak'])
    defaults['showdown_matches'] = canonical['showdown_matches']
    defaults['bounty_matches'] = canonical['bounty_matches']
    defaults['dropzone_placements'] = canonical['dropzone_placements']

    return defaults


def _build_canonical_competitive_stats(team: Team) -> Dict[str, Any]:
    """
    Compute public-safe competitive result stats from canonical systems.

    Dropzone is intentionally tracked separately because current entries are
    user-based placements, not team-vs-team win/loss records.
    """
    import logging
    from django.db.models import Q

    logger = logging.getLogger(__name__)
    results = []
    showdown_count = 0
    bounty_count = 0
    dropzone_placements = 0

    try:
        from apps.competition.models import Challenge
        challenges = (
            Challenge.objects
            .filter(
                Q(challenger_team=team) | Q(challenged_team=team),
                status__in=['COMPLETED', 'SETTLED', 'ADMIN_RESOLVED'],
            )
            .exclude(result='PENDING')
            .only('id', 'challenger_team_id', 'challenged_team_id', 'result', 'updated_at')
            .order_by('-updated_at')
        )
        for challenge in challenges:
            if challenge.result == 'DRAW':
                outcome = 'D'
            elif (
                challenge.challenger_team_id == team.pk and challenge.result == 'CHALLENGER_WIN'
            ) or (
                challenge.challenged_team_id == team.pk and challenge.result == 'CHALLENGED_WIN'
            ):
                outcome = 'W'
            else:
                outcome = 'L'
            results.append((challenge.updated_at, outcome))
            showdown_count += 1
    except Exception as exc:
        logger.debug("Canonical Showdown stats lookup failed for %s: %s", team.slug, exc)

    try:
        from apps.competition.models import BountyClaim
        claims = (
            BountyClaim.objects
            .filter(
                Q(bounty__issuer_team=team) | Q(claiming_team=team),
                bounty__is_hitlist=True,
                status__in=['VERIFIED', 'PAID', 'REJECTED'],
            )
            .select_related('bounty')
            .only('id', 'status', 'claiming_team_id', 'verified_at', 'claimed_at', 'bounty__issuer_team_id')
            .order_by('-verified_at', '-claimed_at')
        )
        for claim in claims:
            if claim.status in ('VERIFIED', 'PAID'):
                outcome = 'W' if claim.claiming_team_id == team.pk else 'L'
            else:
                outcome = 'L' if claim.claiming_team_id == team.pk else 'W'
            results.append((claim.verified_at or claim.claimed_at, outcome))
            bounty_count += 1
    except Exception as exc:
        logger.debug("Canonical Bounty stats lookup failed for %s: %s", team.slug, exc)

    try:
        from apps.tournaments.models import Match
        registration_ids = _get_team_registration_ids(team)
        participant_ids = _get_team_participant_ids(team, registration_ids)
        matches = (
            Match.objects
            .filter(
                _build_team_participant_q(team, registration_ids),
                state='completed',
            )
            .only('id', 'participant1_id', 'participant2_id', 'winner_id', 'updated_at')
            .order_by('-updated_at')
        )
        for match in matches:
            winner_id = getattr(match, 'winner_id', None)
            if not winner_id:
                outcome = 'D'
            else:
                outcome = 'W' if winner_id in participant_ids else 'L'
            results.append((match.updated_at, outcome))
    except Exception as exc:
        logger.debug("Canonical tournament stats lookup failed for %s: %s", team.slug, exc)

    results.sort(key=lambda row: row[0] or timezone.now(), reverse=True)
    form = [outcome for _, outcome in results[:10]]
    wins = sum(1 for _, outcome in results if outcome == 'W')
    losses = sum(1 for _, outcome in results if outcome == 'L')
    draws = sum(1 for _, outcome in results if outcome == 'D')
    total = wins + losses + draws

    current_streak = 0
    streak_type = ''
    if form:
        streak_type = form[0] if form[0] in ('W', 'L') else ''
        if streak_type:
            for outcome in form:
                if outcome == streak_type:
                    current_streak += 1
                else:
                    break

    longest = 0
    run = 0
    for _, outcome in sorted(results, key=lambda row: row[0] or timezone.now()):
        if outcome == 'W':
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    return {
        'matches_played': total,
        'matches_won': wins,
        'matches_lost': losses,
        'matches_drawn': draws,
        'win_rate': round((wins / total) * 100, 1) if total else 0.0,
        'recent_form': form,
        'current_streak': current_streak,
        'streak_type': streak_type,
        'longest_win_streak': longest,
        'showdown_matches': showdown_count,
        'bounty_matches': bounty_count,
        'dropzone_placements': dropzone_placements,
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
    
    # Map vNext Team social fields to stream items (use _url suffix)
    social_platforms = [
        ('discord', getattr(team, 'discord_url', None), 'Discord', ''),
        ('twitch', getattr(team, 'twitch_url', None), 'Twitch', ''),
        ('twitter', getattr(team, 'twitter_url', None), 'Twitter/X', ''),
        ('youtube', getattr(team, 'youtube_url', None), 'YouTube', ''),
        ('instagram', getattr(team, 'instagram_url', None), 'Instagram', ''),
        ('facebook', getattr(team, 'facebook_url', None), 'Facebook', ''),
        ('tiktok', getattr(team, 'tiktok_url', None), 'TikTok', ''),
        ('website', getattr(team, 'website_url', None), 'Website', ''),
    ]
    
    for platform, url, platform_name, default_thumb in social_platforms:
        if url and url.strip():
            streams.append({
                'platform': platform,
                'url': url,
                'title': f"{team.name} on {platform_name}",
                'platform_name': platform_name,
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


def _build_recruitment_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """
    Build recruitment positions + requirements for the public detail page.
    7-Point Overhaul — Point 1B: "Join the Ranks" card data.
    """
    if is_restricted:
        return {'positions': [], 'requirements': []}

    try:
        from apps.organizations.models.recruitment import (
            RecruitmentPosition,
            RecruitmentRequirement,
        )
        positions = list(
            RecruitmentPosition.objects.filter(team=team, is_active=True)
            .order_by('sort_order', '-created_at')[:10]
            .values('title', 'role_category', 'rank_requirement', 'region',
                    'platform', 'short_pitch')
        )
        requirements = list(
            RecruitmentRequirement.objects.filter(team=team)
            .order_by('sort_order', '-created_at')[:15]
            .values('label', 'value')
        )
    except Exception:
        positions, requirements = [], []

    return {
        'positions': positions,
        'requirements': requirements,
    }


def _build_training_context(team: Team, viewer: Optional[User], is_restricted: bool) -> Dict[str, Any]:
    """
    Public-safe Team HQ training summary.

    Exposes only discovery data that belongs on a public team page. Private
    training notes, room details, review notes, and internal sessions stay in
    the Team HQ API.
    """
    context = {
        'tryouts_enabled': False,
        'general_recruitment_enabled': False,
        'has_open_positions': False,
        'active_tryout_application': None,
        'active_join_request': None,
        'applicant_status': None,
        'public_scrims': [],
        'has_public_scrims': False,
    }
    if is_restricted:
        return context

    try:
        from apps.organizations.models.join_request import TeamJoinRequest
        from apps.organizations.models.competitive_settings import TeamCompetitiveSettings
        from apps.organizations.models.training import (
            ScrimRequest,
            TrainingVisibility,
            TryoutApplication,
        )

        has_open_positions = False
        try:
            from apps.organizations.models.recruitment import RecruitmentPosition
            has_open_positions = RecruitmentPosition.objects.filter(team=team, is_active=True).exists()
        except Exception:
            has_open_positions = False

        is_recruiting = bool(getattr(team, 'is_recruiting', False))
        try:
            competitive_settings = team.competitive_settings
        except TeamCompetitiveSettings.DoesNotExist:
            competitive_settings = None
        public_tryouts_allowed = (
            True if competitive_settings is None else competitive_settings.allow_public_tryout_applications
        )
        public_scrims_allowed = (
            True if competitive_settings is None else competitive_settings.allow_public_scrim_availability
        )
        context['has_open_positions'] = has_open_positions
        context['tryouts_enabled'] = bool(is_recruiting and has_open_positions and public_tryouts_allowed)
        context['general_recruitment_enabled'] = bool(is_recruiting)

        if viewer and viewer.is_authenticated:
            tracked_tryout_statuses = [
                TryoutApplication.Status.PENDING,
                TryoutApplication.Status.REVIEWING,
                TryoutApplication.Status.INVITED,
                TryoutApplication.Status.SCHEDULED,
                TryoutApplication.Status.OBSERVATION,
                TryoutApplication.Status.ACCEPTED,
                TryoutApplication.Status.REJECTED,
            ]
            app = (
                TryoutApplication.objects.filter(
                    team=team,
                    applicant=viewer,
                    status__in=tracked_tryout_statuses,
                )
                .select_related('game', 'join_request')
                .prefetch_related('sessions')
                .order_by('-created_at')
                .first()
            )
            if app:
                session = next(iter(app.sessions.all()), None)
                context['active_tryout_application'] = {
                    'id': app.pk,
                    'status': app.status,
                    'status_label': app.get_status_display(),
                    'game': app.game.display_name if app.game_id else _safe_game_context(team).get('name', ''),
                    'created_at': app.created_at,
                    'scheduled_at': session.scheduled_at if session else None,
                    'session_status': session.status if session else '',
                }
                context['applicant_status'] = _build_tryout_applicant_status(app, team, session)

            active_join_statuses = [
                TeamJoinRequest.Status.PENDING,
                TeamJoinRequest.Status.TRYOUT_SCHEDULED,
                TeamJoinRequest.Status.TRYOUT_COMPLETED,
                TeamJoinRequest.Status.OFFER_SENT,
                TeamJoinRequest.Status.ACCEPTED,
                TeamJoinRequest.Status.DECLINED,
            ]
            join_request = (
                TeamJoinRequest.objects.filter(
                    team=team,
                    user=viewer,
                    status__in=active_join_statuses,
                )
                .order_by('-created_at')
                .first()
            )
            if join_request:
                context['active_join_request'] = {
                    'id': join_request.pk,
                    'status': join_request.status,
                    'status_label': join_request.get_status_display(),
                    'created_at': join_request.created_at,
                    'scheduled_at': join_request.tryout_date,
                    'applied_position': join_request.applied_position,
                }
                if not context['applicant_status']:
                    context['applicant_status'] = _build_join_applicant_status(join_request)

        public_scrims = ScrimRequest.objects.none()
        if public_scrims_allowed:
            public_scrims = (
                ScrimRequest.objects.filter(
                    requesting_team=team,
                    status=ScrimRequest.Status.OPEN,
                    visibility=TrainingVisibility.PUBLIC,
                    scheduled_at__gte=timezone.now(),
                )
                .select_related('game')
                .order_by('scheduled_at')[:3]
            )
        context['public_scrims'] = [
            {
                'id': scrim.pk,
                'game': scrim.game.display_name if scrim.game_id else _safe_game_context(team).get('name', ''),
                'format': scrim.format,
                'skill_level': scrim.skill_level,
                'server_region': scrim.server_region,
                'scheduled_at': scrim.scheduled_at,
            }
            for scrim in public_scrims
        ]
        context['has_public_scrims'] = bool(context['public_scrims'])
    except Exception:
        pass

    return context


def _build_tryout_applicant_status(app, team: Team, session=None) -> Dict[str, Any]:
    join_request = getattr(app, 'join_request', None)
    if join_request:
        status = _build_join_applicant_status(join_request)
        status.update({
            'kind': 'tryout',
            'game': app.game.display_name if app.game_id else _safe_game_context(team).get('name', ''),
            'tryout_application_id': app.pk,
        })
        return status

    label_map = {
        'PENDING': 'Tryout Applied',
        'REVIEWING': 'Under Review',
        'INVITED': 'Tryout Invite',
        'SCHEDULED': 'Tryout Scheduled',
        'OBSERVATION': 'Under Review',
        'ACCEPTED': 'Offer Sent',
        'REJECTED': 'Not Selected',
    }
    detail_map = {
        'PENDING': 'Your tryout application is waiting for team review.',
        'REVIEWING': 'The team is reviewing your application.',
        'INVITED': 'The team has invited you for a tryout.',
        'SCHEDULED': 'Your tryout session has been scheduled.',
        'OBSERVATION': 'The team is keeping your application under observation.',
        'ACCEPTED': 'The team accepted your tryout evaluation. Follow the join process for roster membership.',
        'REJECTED': 'The team did not select this application.',
    }
    return {
        'has_any': True,
        'kind': 'tryout',
        'title': label_map.get(app.status, app.get_status_display()),
        'status': app.status,
        'status_label': app.get_status_display(),
        'detail': detail_map.get(app.status, ''),
        'game': app.game.display_name if app.game_id else _safe_game_context(team).get('name', ''),
        'scheduled_at': session.scheduled_at if session else None,
        'created_at': app.created_at,
    }


def _build_join_applicant_status(join_request) -> Dict[str, Any]:
    label_map = {
        'PENDING': 'Join Request Pending',
        'TRYOUT_SCHEDULED': 'Tryout Scheduled',
        'TRYOUT_COMPLETED': 'Tryout Completed',
        'OFFER_SENT': 'Offer Sent',
        'ACCEPTED': 'Offer Accepted',
        'DECLINED': 'Offer Declined',
    }
    detail_map = {
        'PENDING': 'Your join request is waiting for team review.',
        'TRYOUT_SCHEDULED': 'A tryout has been scheduled through the join pipeline.',
        'TRYOUT_COMPLETED': 'Your tryout is complete and waiting for team decision.',
        'OFFER_SENT': 'The team has sent a membership offer.',
        'ACCEPTED': 'You accepted the offer and joined the team roster.',
        'DECLINED': 'You declined this team offer.',
    }
    return {
        'has_any': True,
        'kind': 'join_request',
        'join_request_id': join_request.pk,
        'title': label_map.get(join_request.status, join_request.get_status_display()),
        'status': join_request.status,
        'status_label': join_request.get_status_display(),
        'detail': detail_map.get(join_request.status, ''),
        'scheduled_at': join_request.tryout_date,
        'created_at': join_request.created_at,
        'applied_position': join_request.applied_position,
        'can_accept_offer': join_request.status == 'OFFER_SENT',
        'can_decline_offer': join_request.status == 'OFFER_SENT',
        'offer_action_url': f'/api/vnext/teams/{join_request.team.slug}/apply/offers/{join_request.pk}/',
    }


def _build_sponsors_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    Build sponsors list from team.metadata['sponsors'].
    7-Point Overhaul — Point 6: Partners / Sponsors.
    """
    if is_restricted:
        return []
    meta = getattr(team, 'metadata', None) or {}
    return meta.get('sponsors', [])


def _build_pending_actions_context(
    team: Team, viewer, is_authorized: bool, *, viewer_role: str = 'PUBLIC',
) -> Dict[str, Any]:
    """
    Build pending actions awareness flags for authenticated viewers.
    
    Checks for pending invites and join requests for the viewing user.
    Uses pre-computed viewer_role to avoid redundant TeamMembership queries.
    
    Privacy: Returns all-false for anonymous or unauthorized viewers.
    """
    if not viewer or not viewer.is_authenticated:
        return {
            'can_request_to_join': False,
            'has_pending_invite': False,
            'has_pending_request': False,
            'pending_invite_id': None,
            'pending_request_id': None,
            'pending_request_status': None,
            'pending_request_status_label': '',
            'pending_join_request_count': 0,
        }
    if _is_private_team(team) and not is_authorized:
        return {
            'can_request_to_join': False,
            'has_pending_invite': False,
            'has_pending_request': False,
            'pending_invite_id': None,
            'pending_request_id': None,
            'pending_request_status': None,
            'pending_request_status_label': '',
            'pending_join_request_count': 0,
        }
    
    # Derive membership from pre-computed viewer_role (no extra query)
    is_member = viewer_role != 'PUBLIC'
    
    from apps.organizations.models import TeamInvite
    
    # Check for pending invite (vNext TeamInvite.invited_user is User FK)
    pending_invite = TeamInvite.objects.filter(
        team=team,
        invited_user=viewer,
        status='PENDING'
    ).first()
    
    # Check for pending join request (vNext TeamJoinRequest)
    from apps.organizations.models.join_request import TeamJoinRequest
    active_join_statuses = [
        TeamJoinRequest.Status.PENDING,
        TeamJoinRequest.Status.TRYOUT_SCHEDULED,
        TeamJoinRequest.Status.TRYOUT_COMPLETED,
        TeamJoinRequest.Status.OFFER_SENT,
    ]
    pending_request = TeamJoinRequest.objects.filter(
        team=team, user=viewer, status__in=active_join_statuses,
    ).first()
    
    # User can request to join if: not a member, no pending invite, no pending request, team is recruiting
    can_request = (
        not is_member and
        not pending_invite and
        not pending_request and
        getattr(team, 'is_recruiting', True) and
        not team.roster_locked
    )
    
    # Count pending join requests for admins/owners (use pre-computed role)
    pending_jr_count = 0
    if viewer_role in ('OWNER', 'MANAGER'):
        pending_jr_count = TeamJoinRequest.objects.filter(
            team=team, status__in=['PENDING', 'TRYOUT_SCHEDULED', 'TRYOUT_COMPLETED', 'OFFER_SENT'],
        ).count()

    return {
        'can_request_to_join': can_request,
        'has_pending_invite': pending_invite is not None,
        'has_pending_request': pending_request is not None,
        'pending_invite_id': pending_invite.id if pending_invite else None,
        'pending_request_id': pending_request.id if pending_request else None,
        'pending_request_status': pending_request.status if pending_request else None,
        'pending_request_status_label': pending_request.get_status_display() if pending_request else '',
        'pending_join_request_count': pending_jr_count,
    }


# ============================================================================
# P6-P15 CONTEXT BUILDERS
# ============================================================================

def _build_journey_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    P6 — Curated Journey Milestones.
    
    Shows up to 5 owner-curated milestones from TeamJourneyMilestone (is_visible=True).
    Falls back to legacy activity-based timeline if no curated milestones exist.
    """
    if is_restricted:
        return []

    # ── Primary: Curated milestones ──
    try:
        from apps.organizations.models.journey import TeamJourneyMilestone
        milestones = TeamJourneyMilestone.objects.filter(
            team=team, is_visible=True
        ).order_by('-milestone_date')[:5]
        if milestones.exists():
            return [
                {
                    'type': 'milestone',
                    'milestone_type': getattr(m, 'milestone_type', 'CUSTOM'),
                    'title': m.title,
                    'description': m.description,
                    'timestamp': m.milestone_date,
                    'id': m.pk,
                }
                for m in milestones
            ]
    except Exception:
        pass

    # ── Fallback: Legacy activity log timeline ──
    timeline = []
    PUBLIC_ACTIVITY_TYPES = {'CREATE', 'TOURNAMENT_REGISTER', 'ACQUIRE', 'DELETE'}
    try:
        from apps.organizations.models import TeamActivityLog
        from django.db.models import Q
        activities = TeamActivityLog.objects.filter(
            Q(team=team) & (
                Q(action_type__in=PUBLIC_ACTIVITY_TYPES) |
                Q(is_pinned=True) |
                Q(is_milestone=True)
            )
        ).order_by('-timestamp')[:5]
        for act in activities:
            # Map activity types to milestone categories
            act_type = getattr(act, 'action_type', '')
            m_type = 'CUSTOM'
            if act_type == 'CREATE':
                m_type = 'FOUNDED'
            elif act_type == 'ACQUIRE':
                m_type = 'TRANSFER'
            elif act_type == 'TOURNAMENT_REGISTER':
                m_type = 'TROPHY'
            title = getattr(act, 'description', '') or act_type.replace('_', ' ').title()
            timeline.append({
                'type': 'activity',
                'milestone_type': m_type,
                'title': title,
                'action': act_type,
                'description': '',
                'actor': getattr(act, 'actor_username', ''),
                'timestamp': act.timestamp,
                'metadata': getattr(act, 'metadata', {}),
                'is_pinned': getattr(act, 'is_pinned', False),
                'is_milestone': getattr(act, 'is_milestone', False),
                'id': act.pk,
            })
    except Exception:
        pass

    try:
        from apps.organizations.models import TeamMembershipEvent
        PUBLIC_MEMBERSHIP_EVENTS = {'JOINED', 'REMOVED', 'LEFT'}
        events = TeamMembershipEvent.objects.filter(
            team=team,
            event_type__in=PUBLIC_MEMBERSHIP_EVENTS,
        ).order_by('-created_at')[:5]
        for evt in events:
            timeline.append({
                'type': 'membership',
                'event_type': getattr(evt, 'event_type', ''),
                'actor': getattr(evt.actor, 'username', '') if evt.actor else '',
                'user': getattr(evt.user, 'username', '') if evt.user else '',
                'old_role': getattr(evt, 'old_role', ''),
                'new_role': getattr(evt, 'new_role', ''),
                'timestamp': evt.created_at,
                'metadata': getattr(evt, 'metadata', {}),
            })
    except Exception:
        pass

    timeline.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
    return timeline[:5]


def _build_announcements_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    P7: Transmission Feed — fetch TeamAnnouncement items.
    Returns most recent 10 announcements for public view.
    """
    if is_restricted:
        return []

    try:
        from apps.organizations.models import TeamAnnouncement
        announcements = TeamAnnouncement.objects.filter(
            team=team
        ).select_related('author').order_by('-pinned', '-created_at')[:10]
        return [
            {
                'id': ann.id,
                'content': ann.content,
                'type': getattr(ann, 'announcement_type', 'general'),
                'pinned': getattr(ann, 'pinned', False),
                'author_name': ann.author.username if ann.author else 'System',
                'author_avatar': _get_user_avatar(ann.author) if ann.author else _build_initials_avatar_data_uri('System', seed='system', fallback='SY'),
                'created_at': ann.created_at,
            }
            for ann in announcements
        ]
    except Exception:
        return []


def _build_upcoming_matches_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    P8: Up Next sidebar widget — fetch scheduled matches from tournaments.
    Returns the next 3 upcoming matches for this team.
    """
    if is_restricted:
        return []

    try:
        from django.utils import timezone
        from apps.tournaments.models import Match
        now = timezone.now()
        registration_ids = _get_team_registration_ids(team)
        participant_ids = _get_team_participant_ids(team, registration_ids)
        matches = list(Match.objects.filter(
            _build_team_participant_q(team, registration_ids),
            state__in=['scheduled', 'SCHEDULED', 'CHECK_IN'],
            scheduled_time__gte=now,
        ).select_related('tournament').order_by('scheduled_time')[:3])
        match_participant_ids = {
            participant_id
            for m in matches
            for participant_id in (m.participant1_id, m.participant2_id)
            if participant_id
        }
        registration_team_names = _build_registration_team_name_map(match_participant_ids)
        return [
            {
                'id': m.id,
                'tournament_name': m.tournament.name if m.tournament else 'Unknown',
                'opponent_name': _resolve_participant_name(
                    m.participant2_id if _get_match_side_for_team(m, participant_ids) == 1 else m.participant1_id,
                    m.participant2_name if _get_match_side_for_team(m, participant_ids) == 1 else m.participant1_name,
                    registration_team_names,
                ),
                'opponent_id': (
                    m.participant2_id if _get_match_side_for_team(m, participant_ids) == 1 else m.participant1_id
                ),
                'scheduled_time': m.scheduled_time,
                'format': getattr(m, 'best_of', 'BO1'),
                'stream_url': getattr(m, 'stream_url', ''),
                'state': m.state,
            }
            for m in matches
        ]
    except Exception:
        return []


def _build_trophy_cabinet_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    P13: Trophy Cabinet — fetch tournament placements.
    Queries TournamentResult + Registration to find team's placement history.
    """
    if is_restricted:
        return []

    trophies = []
    try:
        from apps.tournaments.models import TournamentResult, Registration
        # Find all registrations for this team
        reg_id_set = set(Registration.objects.filter(
            team_id=team.id
        ).values_list('id', flat=True))

        if reg_id_set:
            # Find results where this team placed
            from django.db.models import Q
            results = TournamentResult.objects.filter(
                Q(winner_id__in=reg_id_set) |
                Q(runner_up_id__in=reg_id_set) |
                Q(third_place_id__in=reg_id_set)
            ).select_related('tournament')[:12]

            for result in results:
                placement = None
                placement_label = None
                placement_emoji = None
                if result.winner_id in reg_id_set:
                    placement = 1
                    placement_label = '1st Place'
                    placement_emoji = '🏆'
                elif result.runner_up_id and result.runner_up_id in reg_id_set:
                    placement = 2
                    placement_label = '2nd Place'
                    placement_emoji = '🥈'
                elif result.third_place_id and result.third_place_id in reg_id_set:
                    placement = 3
                    placement_label = '3rd Place'
                    placement_emoji = '🥉'

                if placement:
                    tournament = result.tournament
                    trophies.append({
                        'tournament_name': tournament.name if tournament else 'Unknown',
                        'placement': placement,
                        'placement_label': placement_label,
                        'emoji': placement_emoji,
                        'date': getattr(tournament, 'end_date', None) or getattr(tournament, 'created_at', None),
                        'prize': None,  # Could query PrizeTransaction
                    })
    except Exception:
        pass

    # Sort by placement (1st first), then date
    trophies.sort(key=lambda x: (x['placement'], str(x.get('date') or '')))
    return trophies


def _build_media_highlights_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """
    P14: Highlights & Media — fetch TeamMedia + TeamHighlight.
    Returns dict with 'media' list (uploads) and 'highlights' list (external links).
    """
    if is_restricted:
        return {'media': [], 'highlights': []}

    media_items = []
    highlight_items = []

    try:
        from apps.organizations.models import TeamMedia
        media_qs = TeamMedia.objects.filter(team=team).order_by('-created_at')[:6]
        for m in media_qs:
            url = m.file.url if m.file else getattr(m, 'file_url', '')
            media_items.append({
                'id': m.id,
                'title': getattr(m, 'title', ''),
                'category': getattr(m, 'category', 'general'),
                'url': url,
                'file_url': url,
                'file_type': getattr(m, 'file_type', 'image'),
                'created_at': m.created_at,
            })
    except Exception:
        pass

    try:
        from apps.organizations.models import TeamHighlight
        highlights_qs = TeamHighlight.objects.filter(team=team).order_by('-created_at')[:6]
        for h in highlights_qs:
            highlight_items.append({
                'id': h.id,
                'title': getattr(h, 'title', ''),
                'url': getattr(h, 'url', ''),
                'description': getattr(h, 'description', ''),
                'thumbnail': getattr(h, 'thumbnail_url', ''),
                'thumbnail_url': getattr(h, 'thumbnail_url', ''),
                'created_at': h.created_at,
            })
    except Exception:
        pass

    return {
        'media': media_items,
        'highlights': highlight_items,
        'has_content': len(media_items) > 0 or len(highlight_items) > 0,
    }


def _build_challenges_context(team: Team, is_restricted: bool) -> Dict[str, Any]:
    """
    P11: Challenge Hub — fetch open/active challenges for the team.
    Returns dict with 'items' list, 'open_count', and summary stats.
    Uses Challenge & Bounty models from apps.competition.
    """
    if is_restricted:
        return {'items': [], 'open_count': 0, 'stats': {}}

    items = []
    stats = {'wins': 0, 'losses': 0, 'total_earned': 0}

    try:
        from apps.competition.models import Challenge
        from apps.competition.services import ChallengeService
        from django.db.models import Q
        from django.utils import timezone

        now = timezone.now()

        # Active challenges involving this team (open, accepted, scheduled, in_progress)
        qs = Challenge.objects.filter(
            Q(challenger_team=team) | Q(challenged_team=team),
            status__in=['OPEN', 'ACCEPTED', 'SCHEDULED', 'IN_PROGRESS'],
        ).select_related(
            'challenger_team', 'challenged_team', 'game'
        ).order_by('-created_at')[:5]

        for c in qs:
            # Determine opponent
            is_issuer = (c.challenger_team_id == team.pk)
            opponent = c.challenged_team if is_issuer else c.challenger_team
            opponent_name = opponent.name if opponent else 'Open Challenge'

            # Category for UI styling
            category = 'showdown' if c.challenge_type == 'WAGER' else (
                'community' if c.challenge_type == 'OPEN' else 'direct'
            )

            # Format display
            format_str = f'BO{c.best_of}'
            if c.game:
                format_str = f'{c.game.short_code} {format_str}'

            items.append({
                'id': str(c.pk),
                'title': c.title,
                'description': c.description or '',
                'category': category,
                'status': c.get_status_display().split(' —')[0],
                'format': format_str,
                'prize_amount': float(c.prize_amount) if c.prize_amount else 0,
                'prize_type': c.prize_type,
                'prize_description': c.prize_description or '',
                'opponent_name': opponent_name,
                'expires_at': c.expires_at,
                'created_at': c.created_at,
                'reference_code': c.reference_code,
            })

        # Summary stats
        challenge_stats = ChallengeService.get_challenge_stats(team)
        stats = {
            'wins': challenge_stats['wins'],
            'losses': challenge_stats['losses'],
            'total_earned': float(challenge_stats['total_earned']),
        }

    except Exception:
        pass

    return {
        'items': items,
        'open_count': sum(1 for i in items if 'Open' in i.get('status', '')),
        'stats': stats,
    }


def _build_match_history_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    P8 supplement: Match History — fetch recent completed matches.
    Uses leaderboard_stats recent_form if available, else queries Match model.
    """
    if is_restricted:
        return []

    matches = []
    try:
        from apps.tournaments.models import Match
        registration_ids = _get_team_registration_ids(team)
        participant_ids = _get_team_participant_ids(team, registration_ids)

        match_list = list(
            Match.objects.filter(
                _build_team_participant_q(team, registration_ids),
                state='completed',
            ).select_related('tournament').order_by('-updated_at')[:5]
        )

        # Batch-fetch opponent team names (eliminates N+1)
        opponent_ids = set()
        for m in match_list:
            side = _get_match_side_for_team(m, participant_ids)
            opp_id = m.participant2_id if side == 1 else m.participant1_id
            if opp_id:
                opponent_ids.add(opp_id)
        registration_team_names = _build_registration_team_name_map(opponent_ids)
        opponent_map = {}
        if opponent_ids:
            opponent_map = {
                t.id: t.name
                for t in Team.objects.filter(id__in=opponent_ids).only('id', 'name')
            }

        for m in match_list:
            side = _get_match_side_for_team(m, participant_ids)
            is_p1 = (side == 1)
            opponent_id = m.participant2_id if is_p1 else m.participant1_id
            opponent_name = _resolve_participant_name(
                opponent_id,
                f'Team #{opponent_id}' if opponent_id else 'TBD',
                registration_team_names,
                opponent_map,
            )

            # Determine result
            winner_id = getattr(m, 'winner_id', None)
            if winner_id in participant_ids:
                result = 'win'
            elif winner_id:
                result = 'loss'
            else:
                result = 'draw'

            score_display = ''
            if hasattr(m, 'participant1_score') and hasattr(m, 'participant2_score'):
                if is_p1:
                    score_display = f'{m.participant1_score or 0}-{m.participant2_score or 0}'
                else:
                    score_display = f'{m.participant2_score or 0}-{m.participant1_score or 0}'

            matches.append({
                'id': m.id,
                'opponent_name': opponent_name,
                'result': result,
                'score': score_display,
                'tournament_name': getattr(m.tournament, 'name', '') if m.tournament_id else '',
                'match_type': getattr(m, 'match_type', 'official'),
                'date': m.updated_at,
            })
    except Exception:
        pass

    return matches


def _build_operations_log_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    Operations Log — team's tournament participation and match results
    combined into a unified activity feed for the team detail page.
    Shows live matches, recent results, and tournament registrations.
    """
    if is_restricted:
        return []

    ops = []
    try:
        from apps.tournaments.models import Match
        from django.utils import timezone

        # 1. Live + recent matches (last 10)
        registration_ids = _get_team_registration_ids(team)
        participant_ids = _get_team_participant_ids(team, registration_ids)
        match_qs = list(Match.objects.filter(
            _build_team_participant_q(team, registration_ids),
        ).select_related('tournament', 'tournament__game').order_by('-updated_at')[:10])
        match_participant_ids = {
            participant_id
            for m in match_qs
            for participant_id in (m.participant1_id, m.participant2_id)
            if participant_id
        }
        registration_team_names = _build_registration_team_name_map(match_participant_ids)

        for m in match_qs:
            side = _get_match_side_for_team(m, participant_ids)
            is_p1 = (side == 1)
            opponent_id = m.participant2_id if is_p1 else m.participant1_id
            opponent_fallback = m.participant2_name if is_p1 else m.participant1_name
            opponent = _resolve_participant_name(
                opponent_id,
                opponent_fallback,
                registration_team_names,
            )

            # Determine result
            winner_id = getattr(m, 'winner_id', None)
            state = getattr(m, 'state', '')
            if state in ('live', 'LIVE'):
                result = None
                status = 'live'
            elif winner_id in participant_ids:
                result = 'win'
                status = 'completed'
            elif winner_id:
                result = 'loss'
                status = 'completed'
            else:
                result = None
                status = state.lower() if state else 'scheduled'

            score = ''
            if hasattr(m, 'participant1_score') and hasattr(m, 'participant2_score'):
                s1 = m.participant1_score or 0
                s2 = m.participant2_score or 0
                score = f'{s1}-{s2}' if is_p1 else f'{s2}-{s1}'

            prize_text = ''
            if result == 'win' and m.tournament and m.tournament.prize_pool:
                prize_text = f'৳{m.tournament.prize_pool:,.0f}'

            ops.append({
                'status': status,
                'squad_name': team.name,
                'event_name': m.tournament.name if m.tournament else 'Match',
                'opponent': opponent or 'TBD',
                'result': result,
                'score': score,
                'prize': prize_text,
                'date': m.updated_at,
            })

        # Sort: live first, then by date
        ops.sort(key=lambda x: (0 if x['status'] == 'live' else 1, -(x.get('date') or timezone.now()).timestamp()))

    except Exception:
        pass

    return ops[:10]


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
            
            # Get team size from GameRosterConfig
            team_size = 5
            max_team_size = 5
            try:
                from apps.games.models.roster_config import GameRosterConfig
                config = GameRosterConfig.objects.get(game=game)
                team_size = config.min_team_size or 5
                max_team_size = config.max_team_size or 5
            except Exception:
                pass
            
            # Map game category to game_type for template dynamics
            category = getattr(game, 'category', '')
            game_type = getattr(game, 'game_type', '') or category
            
            return {
                'id': game.id,
                'name': game.display_name,
                'slug': game.slug,
                'logo_url': game.logo.url if game.logo else None,
                'primary_color': game.primary_color,
                'category': category,
                'game_type': game_type,
                'short_code': getattr(game, 'short_code', ''),
                'team_size': team_size,
                'max_team_size': max_team_size,
            }
        except Game.DoesNotExist:
            # Fallback for invalid game_id
            return {
                'id': game_id,
                'name': f'Game #{game_id}',
                'slug': None,
                'logo_url': None,
                'primary_color': '#7c3aed',
                'category': '',
                'short_code': '',
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
    from apps.organizations.choices import MembershipRole
    from apps.organizations.services.team_authority import get_team_actor
    
    if not viewer or not viewer.is_authenticated:
        return 'PUBLIC'
    
    actor = get_team_actor(viewer, team)

    if actor.is_superuser or actor.is_creator or actor.org_authority == 'CEO':
        return 'OWNER'
    if actor.org_authority == 'MANAGER':
        return 'MANAGER'

    # Return truthful active team membership role where possible.
    role = actor.role
    if role == MembershipRole.OWNER:
        return 'OWNER'
    elif role == MembershipRole.MANAGER:
        return 'MANAGER'
    elif role == MembershipRole.COACH:
        return 'COACH'
    elif role in (MembershipRole.PLAYER, MembershipRole.SUBSTITUTE):
        return 'PLAYER'
    elif actor.membership is not None:
        return 'MEMBER'
    
    return 'PUBLIC'


def _is_team_member_or_staff(team: Team, viewer: Optional[User]) -> bool:
    """Check if viewer is team member or staff."""
    if not viewer or not viewer.is_authenticated:
        return False
    
    role = _get_viewer_role(team, viewer)
    return role in ('OWNER', 'MANAGER', 'COACH', 'PLAYER', 'MEMBER')


def _get_user_avatar(user: User) -> str:
    """Get user avatar URL with fallback."""
    username = getattr(user, 'username', 'User') if user else 'User'
    display_name = username

    try:
        if hasattr(user, 'profile') and user.profile:
            display_name = getattr(user.profile, 'display_name', '') or display_name
            avatar = getattr(user.profile, 'avatar', None)
            return _safe_image_url(
                avatar,
                _build_initials_avatar_data_uri(display_name, seed=username, fallback='US'),
            )
    except AttributeError:
        pass
    
    return _build_initials_avatar_data_uri(display_name, seed=username, fallback='US')


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


def _build_follow_context(team: Team, viewer) -> Dict[str, Any]:
    """Build follow state for the current viewer."""
    from apps.organizations.models.team_follower import TeamFollower

    count = TeamFollower.objects.filter(team=team).count()
    is_following = False
    if viewer and viewer.is_authenticated:
        is_following = TeamFollower.objects.filter(team=team, user=viewer).exists()
    return {
        'is_following': is_following,
        'follower_count': count,
    }
