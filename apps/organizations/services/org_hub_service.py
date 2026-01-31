"""
Organization Hub Service Layer.

Provides business logic for the Organization Hub page (/orgs/<slug>/hub/).

Functions:
- get_org_hub_context: Retrieve all data needed for hub dashboard
"""

import logging
from typing import Dict, List, Any, Optional
from django.db.models import Count, Q, Prefetch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings

from apps.organizations.permissions import get_permission_context

logger = logging.getLogger(__name__)

# Cache TTL for organization hub context (5 minutes)
ORG_HUB_CACHE_TTL = getattr(settings, 'ORG_HUB_CACHE_TTL', 300)


def get_org_hub_context(org_slug: str, user: Optional[User] = None) -> Dict[str, Any]:
    """
    Get organization hub context with stats, teams, members, and activity.
    
    Retrieves all data needed to render the organization hub dashboard,
    including organization details, statistics, teams list, recent activity,
    and permission checks. Results are cached for 5 minutes per org_slug.
    
    Args:
        org_slug: Organization URL slug
        user: Current user (for permission checks), can be None
    
    Returns:
        dict: Hub context with keys:
            - organization: Organization instance with related data
            - stats: Dict with computed statistics
            - teams: List of organization teams
            - members: List of organization members (if can_manage)
            - recent_activity: List of recent activity dicts
            - can_manage: Boolean permission flag
    
    Raises:
        Organization.DoesNotExist: If org_slug is invalid
    
    Example:
        >>> context = get_org_hub_context('syntax', request.user)
        >>> context['stats']['team_count']
        4
        >>> context['can_manage']
        True
    """
    from apps.organizations.models import Organization, OrganizationMembership, Team
    
    # Build cache key (public data only, not permission-specific)
    cache_key = f'org_hub_context:{org_slug}'
    
    # Try to get cached data
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Cache hit - use cached organization data
        organization = cached_data['organization']
        teams = cached_data['teams']
        stats = cached_data['stats']
        recent_activity = cached_data['recent_activity']
        
        logger.debug(
            f"Organization hub cache HIT",
            extra={'org_slug': org_slug, 'cache_key': cache_key}
        )
    else:
        # Cache miss - fetch from database
        logger.debug(
            f"Organization hub cache MISS",
            extra={'org_slug': org_slug, 'cache_key': cache_key}
        )
        
        # Fetch organization with optimized queries
        try:
            organization = Organization.objects.select_related(
                'profile',
                'ranking',
                'ceo'
            ).prefetch_related(
                Prefetch(
                    'teams',
                    queryset=Team.objects.prefetch_related('memberships')
                )
            ).get(slug=org_slug)
        except Organization.DoesNotExist:
            logger.warning(
                f"Organization not found for hub access",
                extra={'org_slug': org_slug, 'user_id': user.id if user else None}
            )
            raise
    
# Get permissions (NOT cached for security - must be computed per-request)
permissions = get_permission_context(user, organization) if (user and user.is_authenticated) else {
    'viewer_role': 'NONE',
    'can_access_control_plane': False,
    'can_manage_org': False,
    'can_view_financials': False,
    'can_manage_staff': False,
    'can_modify_governance': False,
    'can_execute_terminal_actions': False,
}
        for team in teams:
            team.roster_count = team.roster.count() if hasattr(team, 'roster') else 0
            team.match_count = 0  # TODO: wire to matches app when ready
        
        # Compute statistics
        stats = _compute_org_stats(organization, teams)
        
        # Get recent activity
        recent_activity = _get_recent_activity(organization, limit=10)
        
        # Cache the data (5 minutes)
        cache_data = {
            'organization': organization,
            'teams': teams,
            'stats': stats,
            'recent_activity': recent_activity,
        }
        cache.set(cache_key, cache_data, ORG_HUB_CACHE_TTL)
        
        logger.debug(
            f"Organization hub data cached",
            extra={'org_slug': org_slug, 'cache_key': cache_key, 'ttl': ORG_HUB_CACHE_TTL}
        )
    
    # Get members (only if user can manage) - NOT cached for security
    members = []
    if permissions['can_manage_org']:
        members = list(
            organization.staff_memberships.select_related('user')
            .filter(role__in=['MANAGER', 'ADMIN'])
            .order_by('-joined_at')[:5]
        )
    
    logger.info(
        f"Organization hub context generated",
        extra={
            'org_slug': org_slug,
            'org_id': organization.id,
            'user_id': user.id if user else None,
            'can_manage': permissions['can_manage_org'],
            'team_count': len(teams),
            'member_count': len(members),
            'cache_hit': cached_data is not None
        }
    )
    
    return {
        'organization': organization,
        'stats': stats,
        'teams': teams,
        'members': members,
        'recent_activity': recent_activity,
        **permissions,
    }


def _compute_org_stats(organization, teams: List) -> Dict[str, Any]:
    """
    Compute organization statistics for dashboard cards.
    
    Args:
        organization: Organization instance with related data
        teams: List of Team instances
    
    Returns:
        dict: Statistics with keys:
            - global_rank: Global ranking position (from ranking model)
            - total_cp: Total Crown Points
            - cp_progress: Progress percentage (0-100)
            - total_earnings: Total earnings in thousands
            - team_count: Number of active teams
    """
    stats = {
        'global_rank': None,
        'total_cp': 0,
        'cp_progress': 75,  # Default progress bar value
        'total_earnings': 0,
        'team_count': len(teams),
    }
    
    # Get ranking data if available
    if hasattr(organization, 'ranking') and organization.ranking:
        try:
            stats['global_rank'] = organization.ranking.global_rank
            stats['total_cp'] = organization.ranking.total_points
        except AttributeError:
            logger.warning(
                f"Ranking model missing expected fields",
                extra={'org_id': organization.id}
            )
    
    # Get earnings from profile if available
    if hasattr(organization, 'profile') and organization.profile:
        try:
            # Assuming profile has total_earnings field (add if not exists)
            if hasattr(organization.profile, 'total_earnings'):
                # Convert to thousands for display
                stats['total_earnings'] = organization.profile.total_earnings / 1000
        except AttributeError:
            pass
    
    # Calculate CP progress (for progress bar)
    if stats['total_cp'] > 0:
        # Map CP to percentage (example: 100k CP = 100%)
        stats['cp_progress'] = min(int((stats['total_cp'] / 100000) * 100), 100)
    
    return stats


def _get_recent_activity(organization, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent activity feed for organization.
    
    Aggregates recent activities from teams, member changes, and org events.
    Returns REAL data only - no fake placeholder items.
    
    Args:
        organization: Organization instance
        limit: Maximum number of activities to return
    
    Returns:
        list: Activity dicts with keys: description, timestamp, icon, color
        Empty list if no real activities exist.
    """
    # TODO: Wire to matches app when ready for match results
    # TODO: Wire to economy app when ready for transactions
    
    activities = []
    
    # TODO PHASE 6: Add team creation activities once org-team FK activated
    # Organizations do NOT own teams yet (Legacy Team is authoritative)
    # Stubbing team activities until migration complete
    except Exception as e:
        logger.warning(
            f"Error fetching team activities",
            extra={'org_id': organization.id, 'error': str(e)}
        )
    
    # Add organization creation activity (REAL DATA)
    if hasattr(organization, 'created_at') and organization.created_at:
        activities.append({
            'description': f"<strong>{organization.name}</strong> organization was founded.",
            'timestamp': organization.created_at,
            'icon': 'flag',
            'color': 'yellow',
        })
    
    # Add organization verification activity (REAL DATA)
    if organization.is_verified and hasattr(organization, 'profile'):
        try:
            if hasattr(organization.profile, 'verified_at') and organization.profile.verified_at:
                activities.append({
                    'description': f"<strong>{organization.name}</strong> received official verification.",
                    'timestamp': organization.profile.verified_at,
                    'icon': 'check-circle',
                    'color': 'green',
                })
        except Exception:
            pass
    
    # Sort by timestamp and limit
    activities = sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    logger.debug(
        f"Generated {len(activities)} REAL activity items for organization",
        extra={'org_id': organization.id}
    )
    
    return activities
