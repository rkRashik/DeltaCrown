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
        'leaderboard_stats': _build_leaderboard_stats_context(team, is_private_restricted),
        'streams': _build_streams_context(team, is_private_restricted),
        'partners': _build_partners_context(team, is_private_restricted),
        'merch': _build_merch_context(team, is_private_restricted),
        'pending_actions': _build_pending_actions_context(team, viewer, is_authorized),
        'page': _build_page_context(team, request),
        # P6-P15 context
        'journey': _build_journey_context(team, is_private_restricted),
        'announcements': _build_announcements_context(team, is_private_restricted),
        'upcoming_matches': _build_upcoming_matches_context(team, is_private_restricted),
        'trophy_cabinet': _build_trophy_cabinet_context(team, is_private_restricted),
        'media_highlights': _build_media_highlights_context(team, is_private_restricted),
        'challenges': _build_challenges_context(team, is_private_restricted),
        'match_history': _build_match_history_context(team, is_private_restricted),
        # 7-Point Overhaul — recruitment & sponsors
        'recruitment': _build_recruitment_context(team, is_private_restricted),
        'sponsors': _build_sponsors_context(team, is_private_restricted),
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

def _get_starting_lineup_size(team: Team) -> int:
    """Get the starting lineup size for a team's game from GameRosterConfig."""
    try:
        from apps.games.models.roster_config import GameRosterConfig
        config = GameRosterConfig.objects.get(game_id=team.game_id)
        return config.min_team_size or 5
    except Exception:
        return 5


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
        'elo_rating': 1200,
        'peak_elo': 1200,
        'tier': 'UNRANKED',
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

    # --- TeamRanking (ELO) ---
    try:
        from apps.leaderboards.models import TeamRanking
        tr = TeamRanking.objects.filter(team=team, game_slug=game_slug).first() if game_slug else None
        if tr:
            defaults['elo_rating'] = tr.elo_rating or 1200
            defaults['peak_elo'] = tr.peak_elo or defaults['elo_rating']
    except Exception as e:
        logger.debug(f"TeamRanking lookup failed for {team.slug}: {e}")

    # --- TeamAnalyticsSnapshot (tier, percentile, streaks) ---
    try:
        from apps.leaderboards.models import TeamAnalyticsSnapshot
        snap = TeamAnalyticsSnapshot.objects.filter(
            team=team, game_slug=game_slug,
        ).order_by('-id').first() if game_slug else None
        if snap:
            defaults['tier'] = getattr(snap, 'tier', 'UNRANKED') or 'UNRANKED'
            defaults['percentile_rank'] = float(getattr(snap, 'percentile_rank', 0) or 0)
            defaults['current_streak'] = abs(getattr(snap, 'current_streak', 0) or 0)
            streak_val = getattr(snap, 'current_streak', 0) or 0
            defaults['streak_type'] = 'W' if streak_val > 0 else ('L' if streak_val < 0 else '')
            defaults['longest_win_streak'] = getattr(snap, 'longest_win_streak', 0) or 0
    except Exception as e:
        logger.debug(f"TeamAnalyticsSnapshot lookup failed for {team.slug}: {e}")

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

    return defaults


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


def _build_sponsors_context(team: Team, is_restricted: bool) -> List[Dict[str, Any]]:
    """
    Build sponsors list from team.metadata['sponsors'].
    7-Point Overhaul — Point 6: Partners / Sponsors.
    """
    if is_restricted:
        return []
    meta = getattr(team, 'metadata', None) or {}
    return meta.get('sponsors', [])


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
    
    # Check for pending join request (vNext TeamJoinRequest)
    from apps.organizations.models.join_request import TeamJoinRequest
    pending_request = TeamJoinRequest.objects.filter(
        team=team, user=viewer, status='PENDING',
    ).first()
    
    # User can request to join if: not a member, no pending invite, no pending request, team is recruiting
    can_request = (
        not is_member and
        not pending_invite and
        not pending_request and
        getattr(team, 'is_recruiting', True) and
        not team.roster_locked
    )
    
    return {
        'can_request_to_join': can_request,
        'has_pending_invite': pending_invite is not None,
        'has_pending_request': pending_request is not None,
        'pending_invite_id': pending_invite.id if pending_invite else None,
        'pending_request_id': pending_request.id if pending_request else None,
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
                'author_avatar': _get_user_avatar(ann.author) if ann.author else FALLBACK_URLS['user_avatar'],
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
        from django.db.models import Q
        from django.utils import timezone
        from apps.tournaments.models import Match
        now = timezone.now()
        matches = Match.objects.filter(
            Q(participant1_id=team.id) | Q(participant2_id=team.id),
            state__in=['scheduled', 'SCHEDULED', 'CHECK_IN'],
            scheduled_time__gte=now,
        ).select_related('tournament').order_by('scheduled_time')[:3]
        return [
            {
                'id': m.id,
                'tournament_name': m.tournament.name if m.tournament else 'Unknown',
                'opponent_name': (
                    m.participant2_name if str(m.participant1_id) == str(team.id) else m.participant1_name
                ),
                'opponent_id': (
                    m.participant2_id if str(m.participant1_id) == str(team.id) else m.participant1_id
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
        team_registrations = Registration.objects.filter(
            team_id=team.id
        ).values_list('id', flat=True)

        if team_registrations:
            # Find results where this team placed
            from django.db.models import Q
            results = TournamentResult.objects.filter(
                Q(winner_id__in=team_registrations) |
                Q(runner_up_id__in=team_registrations) |
                Q(third_place_id__in=team_registrations)
            ).select_related('tournament')[:12]

            for result in results:
                placement = None
                placement_label = None
                placement_emoji = None
                if result.winner_id in list(team_registrations):
                    placement = 1
                    placement_label = '1st Place'
                    placement_emoji = '🏆'
                elif result.runner_up_id and result.runner_up_id in list(team_registrations):
                    placement = 2
                    placement_label = '2nd Place'
                    placement_emoji = '🥈'
                elif result.third_place_id and result.third_place_id in list(team_registrations):
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
            category = 'wager' if c.challenge_type == 'WAGER' else (
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
        from django.db.models import Q
        from django.utils import timezone

        qs = Match.objects.filter(
            Q(participant1_id=team.id) | Q(participant2_id=team.id),
            state__in=['COMPLETED', 'completed', 'DONE', 'done'],
        ).select_related('tournament').order_by('-updated_at')[:5]

        for m in qs:
            is_p1 = (m.participant1_id == team.id)
            opponent_id = m.participant2_id if is_p1 else m.participant1_id
            opponent_name = f'Team #{opponent_id}' if opponent_id else 'TBD'

            # Try to resolve opponent name
            try:
                opp_team = Team.objects.only('name', 'tag').get(id=opponent_id)
                opponent_name = opp_team.name
            except Team.DoesNotExist:
                pass

            # Determine result
            winner_id = getattr(m, 'winner_id', None)
            if winner_id == team.id:
                result = 'win'
            elif winner_id:
                result = 'loss'
            else:
                result = 'draw'

            score_display = ''
            if hasattr(m, 'score_participant1') and hasattr(m, 'score_participant2'):
                if is_p1:
                    score_display = f'{m.score_participant1 or 0}-{m.score_participant2 or 0}'
                else:
                    score_display = f'{m.score_participant2 or 0}-{m.score_participant1 or 0}'

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
    from apps.organizations.models import TeamMembership
    from apps.organizations.choices import MembershipStatus, MembershipRole
    
    if not viewer or not viewer.is_authenticated:
        return 'PUBLIC'
    
    # Check if viewer is the team creator (created_by)
    if team.created_by_id == viewer.id:
        return 'OWNER'
    
    # Check if viewer is Organization CEO
    if team.organization_id:
        try:
            org = team.organization
            if org and org.ceo_id == viewer.id:
                return 'OWNER'
        except Exception:
            pass
    
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
