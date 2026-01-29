"""
Team Detail Service - Public Display

Handles read-only queries for public-facing team detail page (P4-T1).

This service provides data for anonymous users and platform visitors to view
team information, roster, and statistics WITHOUT authentication requirements.

Architectural Rules:
- Read-only (no mutations)
- Respects team privacy settings (public/private)
- Respects organization visibility settings
- No permission checks (handles anonymous users)
- Returns display-ready data (no raw ORM objects)

Performance Targets:
- Query count: ≤5 queries
- Response time: <100ms (p95)
"""

import logging
from typing import Dict, Any, Optional, List
from django.db.models import Count, Q, Prefetch
from django.core.cache import cache

from apps.organizations.models import Team, TeamMembership, Organization
from apps.organizations.services.exceptions import NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)


class TeamDetailService:
    """Service for public team detail page queries."""
    
    @staticmethod
    def _is_team_public(team) -> bool:
        """
        Detect if team is public or private using available model fields.
        
        Priority order:
        1. visibility field ("PUBLIC" / "public" = public)
        2. is_private field (public = not is_private)
        3. privacy field (check if indicates public)
        4. Default to PUBLIC (no privacy system implemented yet)
        
        Args:
            team: Team instance
        
        Returns:
            bool: True if team is public, False if private
        """
        # Check for visibility field
        if hasattr(team, 'visibility'):
            visibility = getattr(team, 'visibility', '').upper()
            return visibility in ('PUBLIC', 'OPEN')
        
        # Check for is_private field
        if hasattr(team, 'is_private'):
            return not team.is_private
        
        # Check for privacy field
        if hasattr(team, 'privacy'):
            privacy = getattr(team, 'privacy', '').upper()
            return privacy in ('PUBLIC', 'OPEN')
        
        # Default: Public (no privacy system implemented)
        # Log warning so we know when this needs proper implementation
        logger.debug(
            f"Team {team.slug} has no privacy fields - defaulting to public. "
            "Consider adding 'visibility' field to Team model."
        )
        return True
    
    @staticmethod
    def get_public_team_display(
        team_slug: str,
        viewer_user=None
    ) -> Dict[str, Any]:
        """
        Retrieve public team display data for detail page.
        
        Returns team information formatted for public display. Respects
        privacy settings - private teams only visible to members.
        
        Args:
            team_slug: Team URL slug
            viewer_user: Optional authenticated user (None for anonymous)
        
        Returns:
            Dict with keys: {team, member_count, public_members, stats, can_view_details}
        
        Raises:
            NotFoundError: If team not found
            PermissionDeniedError: If team is private and user is not a member
        
        Query Budget: ≤5 queries
        - Query 1: Team + Organization (select_related)
        - Query 2: Member count (annotate)
        - Query 3: Public roster members (prefetch_related)
        - Query 4: Team statistics (aggregate)
        - Query 5: Viewer membership check (if authenticated)
        """
        from apps.organizations.models import Team, TeamMembership
        from apps.organizations.choices import MembershipStatus
        
        # Query 1: Get team with organization
        try:
            team = Team.objects.select_related('organization').get(slug=team_slug)
        except Team.DoesNotExist:
            raise NotFoundError("team", team_slug)
        
        # Check if viewer can access this team
        is_member = False
        if viewer_user and viewer_user.is_authenticated:
            # Query 2: Check membership
            is_member = TeamMembership.objects.filter(
                team=team,
                user=viewer_user,
                status=MembershipStatus.ACTIVE
            ).exists()
        
        # Privacy check using helper
        is_public = TeamDetailService._is_team_public(team)
        if not is_public and not is_member:
            # Private team - viewer must be member
            can_view_details = False
        else:
            can_view_details = True
        
        # Build team data
        team_data = {
            'id': team.id,
            'name': team.name,
            'slug': team.slug,
            'tag': team.tag if hasattr(team, 'tag') else None,
            'description': team.description if can_view_details else None,
            'is_public': is_public,  # Use computed value, not model field
            'avatar': team.logo.url if team.logo else None,
            'banner': team.banner.url if hasattr(team, 'banner') and team.banner else None,
            'organization': {
                'name': team.organization.name,
                'slug': team.organization.slug,
            } if team.organization else None,
        }
        
        # Query 3: Get member count
        member_count = TeamMembership.objects.filter(
            team=team,
            status=MembershipStatus.ACTIVE
        ).count() if can_view_details else 0
        
        # Query 4: Get public roster (only if can view details)
        public_members = []
        if can_view_details:
            memberships = TeamMembership.objects.filter(
                team=team,
                status=MembershipStatus.ACTIVE
            ).select_related('user').order_by('-role', 'joined_at')[:10]  # Top 10 members
            
            for membership in memberships:
                public_members.append({
                    'user': {
                        'id': membership.user.id,
                        'username': membership.user.username,
                        'avatar': membership.user.avatar.url if hasattr(membership.user, 'avatar') and membership.user.avatar else None,
                    },
                    'role': membership.role,
                    'joined_at': membership.joined_at,
                })
        
        # Query 5: Get team statistics (placeholder - implement when match/tournament models ready)
        stats = {
            'tournament_count': 0,  # TODO: Implement when tournament app integrated
            'match_count': 0,  # TODO: Implement when match app integrated
            'win_rate': 0,  # TODO: Calculate from match results
        }
        
        # Permission flags
        permissions = {
            'can_view_details': can_view_details,
            'can_view_hub': is_member,  # Members can access hub
            'can_manage_team': False,  # Determined in team_manage/control_plane views
        }
        
        return {
            'team': team_data,
            'member_count': member_count,
            'public_members': public_members,
            'stats': stats,
            **permissions,
        }
    
    @staticmethod
    def check_team_accessibility(team_slug: str, viewer_user=None) -> Dict[str, bool]:
        """
        Quick check if team is accessible to viewer.
        
        Args:
            team_slug: Team URL slug
            viewer_user: Optional authenticated user
        
        Returns:
            Dict with: {exists, is_public, is_member, can_view}
        """
        from apps.organizations.models import Team, TeamMembership
        from apps.organizations.choices import MembershipStatus
        
        try:
            team = Team.objects.only('id', 'slug').get(slug=team_slug)
        except Team.DoesNotExist:
            return {
                'exists': False,
                'is_public': False,
                'is_member': False,
                'can_view': False,
            }
        
        is_member = False
        if viewer_user and viewer_user.is_authenticated:
            is_member = TeamMembership.objects.filter(
                team=team,
                user=viewer_user,
                status=MembershipStatus.ACTIVE
            ).exists()
        
        is_public = TeamDetailService._is_team_public(team)
        can_view = is_public or is_member
        
        return {
            'exists': True,
            'is_public': is_public,
            'is_member': is_member,
            'can_view': can_view,
        }
