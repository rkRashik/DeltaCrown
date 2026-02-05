"""
TeamService - Service layer for Team operations (vNext system).

This service provides the unified interface for all team-related operations,
routing between legacy (apps.teams) and vNext (apps.organizations) systems
during the migration period (Phases 2-7).

COMPATIBILITY CONTRACT: All public method signatures MUST remain stable.
Breaking changes require version bump and deprecation notice.

Performance Targets (p95 latency):
- Simple reads (get_team_identity): <50ms, ≤3 queries
- Complex reads (validate_roster): <100ms, ≤5 queries
- Writes (create_team): <100ms, ≤5 queries
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    ConflictError,
)


# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class TeamIdentity:
    """
    Display-ready team branding and metadata.
    
    Used by: tournaments (brackets), notifications (messages), 
             user_profile (team cards), leaderboards (rankings).
    """
    team_id: int
    name: str
    slug: str
    logo_url: str
    badge_url: Optional[str]  # Organization badge if applicable
    game_name: str
    game_id: int
    region: str
    is_verified: bool  # Organization verification status
    is_org_team: bool
    organization_name: Optional[str]
    organization_slug: Optional[str]


@dataclass
class WalletInfo:
    """
    Prize distribution destination for economy integration.
    
    Used by: economy (prize payouts), tournaments (payout confirmation).
    """
    wallet_id: int
    owner_name: str
    wallet_type: str  # 'USER' or 'ORG'
    revenue_split: Optional[Dict[str, float]]  # e.g., {'players': 0.8, 'org': 0.2}


@dataclass
class ValidationResult:
    """
    Tournament registration eligibility validation result.
    
    Used by: tournaments (registration flow), tournament_ops (dashboard).
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    roster_data: Dict[str, Any]  # Debug info for troubleshooting


@dataclass
class RosterMember:
    """
    Single roster member with role and status information.
    
    Used by: tournaments (lineup display), notifications (roster changes).
    
    Attributes:
        membership_id: TeamMembership primary key (for member operations)
        user_id: User primary key
        username: User's username
        display_name: User's display name
        role: PLAYER, SUBSTITUTE, COACH, ANALYST, MANAGER
        roster_slot: STARTER, SUBSTITUTE, BENCH, STAFF
        status: ACTIVE, INACTIVE, REMOVED
        is_tournament_captain: If True, user can act as captain in tournaments
        joined_date: ISO 8601 formatted join timestamp
    """
    membership_id: int
    user_id: int
    username: str
    display_name: str
    role: str  # PLAYER, SUBSTITUTE, COACH, ANALYST, MANAGER
    roster_slot: str  # STARTER, SUBSTITUTE, BENCH, STAFF
    status: str  # ACTIVE, INACTIVE, REMOVED
    is_tournament_captain: bool
    joined_date: str  # ISO 8601 format


# ============================================================================
# TEAMSERVICE - PUBLIC API
# ============================================================================

class TeamService:
    """
    Unified service layer for Team operations.
    
    Migration Phases:
    - Phase 2-4: Routes all queries to legacy system (apps.teams)
    - Phase 5-7: Checks TeamMigrationMap, routes to legacy OR vNext
    - Phase 8+: Routes all queries to vNext system only
    
    Thread Safety: All methods are thread-safe (no shared mutable state).
    Caching: No internal caching (consumers should cache at API/view layer).
    """
    
    # ========================================================================
    # IDENTITY & BRANDING
    # ========================================================================
    
    @staticmethod
    def get_team_identity(team_id: int) -> TeamIdentity:
        """
        Retrieve display-ready team branding and metadata.
        
        This is the PRIMARY method for fetching team information for display.
        Handles brand inheritance logic (organization logo enforcement).
        
        Args:
            team_id: Team primary key (stable across legacy and vNext)
        
        Returns:
            TeamIdentity DTO with all display fields populated
        
        Raises:
            NotFoundError: If team_id does not exist in either system
            ServiceUnavailableError: If database connection fails
        
        Performance Notes:
            - Target: <50ms (p95), ≤3 queries
            - Uses select_related('organization', 'game') to prevent N+1
            - Logo URL computed without database hit (uses model property)
        
        Migration Strategy:
            - Phase 2-4: Query legacy teams.Team
            - Phase 5-7: Check TeamMigrationMap, query appropriate system
            - Phase 8+: Query vNext organizations.Team only
        
        Example:
            identity = TeamService.get_team_identity(team_id=42)
            print(f"{identity.name} ({identity.region})")
            template_context['team_logo'] = identity.logo_url
        """
        from apps.organizations.models import Team
        
        # Query team with organization join to prevent N+1
        # select_related fetches organization in same query (1 query total)
        try:
            team = Team.objects.select_related('organization').get(id=team_id)
        except Team.DoesNotExist:
            raise NotFoundError("team", team_id)
        
        # Determine if team belongs to organization
        is_org_team = team.organization is not None
        
        # Brand inheritance logic: use org logo if enforce_brand is True
        if is_org_team and team.organization.enforce_brand:
            # Organization enforces branding - use org logo
            logo_url = team.organization.logo.url if team.organization.logo else '/static/images/default_org_logo.png'
            badge_url = team.organization.badge.url if team.organization.badge else None
        else:
            # Use team's own logo (or fallback)
            logo_url = team.logo.url if team.logo else '/static/images/default_team_logo.png'
            badge_url = None
            # If org team without brand enforcement, still show org badge if available
            if is_org_team and team.organization.badge:
                badge_url = team.organization.badge.url
        
        # Build TeamIdentity DTO
        # TODO: game_name will need lookup from games.Game in Phase 4
        # For now, using game_id as placeholder
        return TeamIdentity(
            team_id=team.id,
            name=team.name,
            slug=team.slug,
            logo_url=logo_url,
            badge_url=badge_url,
            game_name=f"Game {team.game_id}",  # TODO: Replace with actual game lookup in Phase 4
            game_id=team.game_id,
            region=team.region,
            is_verified=team.organization.is_verified if is_org_team else False,
            is_org_team=is_org_team,
            organization_name=team.organization.name if is_org_team else None,
            organization_slug=team.organization.slug if is_org_team else None,
        )
    
    # ========================================================================
    # FINANCIAL & ECONOMY INTEGRATION
    # ========================================================================
    
    @staticmethod
    def get_team_wallet(team_id: int) -> WalletInfo:
        """
        Retrieve wallet for prize distribution.
        
        CRITICAL: This method handles Organization revenue splits. Independent
        teams route to owner's personal wallet, Organization teams route to
        master wallet with configured revenue_split.
        
        Args:
            team_id: Team primary key
        
        Returns:
            WalletInfo DTO with wallet_id and revenue split configuration
        
        Raises:
            NotFoundError: If team_id does not exist
            ValidationError: If team has no wallet configured (should never happen)
        
        Performance Notes:
            - Target: <50ms (p95), ≤3 queries
            - Uses select_related('organization', 'owner__wallet')
            - Revenue split computed from JSON config (no additional query)
        
        Contract Violation Risks:
            - Direct access to team.owner.wallet FAILS for Organization teams
            - Always use this service method for wallet retrieval
        
        Example:
            wallet = TeamService.get_team_wallet(team_id=42)
            economy.distribute_prize(
                wallet_id=wallet.wallet_id,
                amount=10000,
                split=wallet.revenue_split
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # ROSTER VALIDATION (TOURNAMENT INTEGRATION)
    # ========================================================================
    
    @staticmethod
    def validate_roster(
        team_id: int,
        *,
        tournament_id: Optional[int] = None,
        game_id: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate team roster meets tournament eligibility requirements.
        
        Validation Checks:
        1. Roster size (minimum players for game)
        2. Game Passports (active lineup has valid, non-expired Game IDs)
        3. Ban status (no suspended/banned players)
        4. Roster lock conflicts (not locked in overlapping tournament)
        5. Game match (team.game == tournament.game)
        6. Active lineup configured (TOC set for vNext teams)
        
        Args:
            team_id: Team primary key
            tournament_id: Tournament to validate against (optional)
            game_id: Game to validate for (optional, inferred from team if omitted)
        
        Returns:
            ValidationResult with is_valid flag, errors list, warnings list
        
        Raises:
            NotFoundError: If team_id or tournament_id does not exist
            ValidationError: If both tournament_id and game_id are None
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses prefetch_related('memberships__user') for roster
            - Game Passport check may query external API (cached 15 min)
        
        Async Boundary:
            - Ban status checks may trigger external API calls
            - Consider moving to async job for tournament ops dashboard
        
        Example:
            result = TeamService.validate_roster(
                team_id=42,
                tournament_id=123
            )
            if not result.is_valid:
                return JsonResponse({
                    'eligible': False,
                    'errors': result.errors
                })
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # PERMISSIONS & AUTHORIZATION
    # ========================================================================
    
    @staticmethod
    def get_authorized_managers(team_id: int) -> List[int]:
        """
        Retrieve user IDs authorized to manage team operations.
        
        Management Permissions:
        - Register for tournaments
        - Edit roster (add/remove members)
        - Update team profile (name, logo, region)
        - Withdraw from tournaments
        
        Authorization Logic:
        - Independent Team: Owner only
        - Organization Team: CEO + assigned Managers + Coaches with permissions
        
        Args:
            team_id: Team primary key
        
        Returns:
            List of user IDs with management permissions (deduplicated)
        
        Raises:
            NotFoundError: If team_id does not exist
        
        Performance Notes:
            - Target: <50ms (p95), ≤3 queries
            - Uses filter() on memberships (indexed query)
            - Returns user IDs only (no full User objects to reduce serialization)
        
        Example:
            authorized_users = TeamService.get_authorized_managers(team_id=42)
            if request.user.id not in authorized_users:
                raise PermissionDeniedError("You cannot manage this team")
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # URL GENERATION (NOTIFICATION INTEGRATION)
    # ========================================================================
    
    @staticmethod
    def get_team_url(team_id: int) -> str:
        """
        Generate canonical team URL for notifications and external links.
        
        URL Routing Logic:
        - Legacy Team: /teams/{slug}/
        - vNext Independent Team: /teams/{slug}/ (redirect from legacy)
        - vNext Organization Team: /orgs/{org_slug}/teams/{team_slug}/
        
        CRITICAL: Notifications MUST use this method to generate links.
        Hardcoded URLs will break during Phase 6 URL migration.
        
        Args:
            team_id: Team primary key
        
        Returns:
            Absolute URL path (without domain) for team detail page
        
        Raises:
            NotFoundError: If team_id does not exist
        
        Performance Notes:
            - Target: <50ms (p95), ≤2 queries
            - Uses select_related('organization') if vNext team
            - No reverse() call (URL computed directly for performance)
        
        Migration Strategy:
            - Phase 2-4: Returns legacy URL (/teams/{slug}/)
            - Phase 5-7: Checks migration map, returns appropriate URL
            - Phase 6+: Redirects handled by URL shim layer
            - Phase 8+: Returns vNext URL only
        
        Example:
            team_url = TeamService.get_team_url(team_id=42)
            notification.send(
                message=f"Your team was accepted!",
                link=team_url
            )
        """
        from apps.organizations.models import Team
        
        # Query team with organization join (1 query only)
        # select_related('organization') ensures org slug fetched in same query
        try:
            team = Team.objects.select_related('organization').get(id=team_id)
        except Team.DoesNotExist:
            raise NotFoundError("team", team_id)
        
        # Generate canonical URL based on ownership type
        if team.organization:
            # Organization team: /orgs/{org_slug}/teams/{team_slug}/
            return f"/orgs/{team.organization.slug}/teams/{team.slug}/"
        else:
            # Independent team: /teams/{slug}/
            return f"/teams/{team.slug}/"
    
    # ========================================================================
    # ROSTER MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def get_roster_members(
        team_id: int,
        *,
        status: str = "ACTIVE"
    ) -> List[RosterMember]:
        """
        Retrieve team roster with member details.
        
        Filters:
        - status: ACTIVE (default), INACTIVE, REMOVED, ALL
        
        Args:
            team_id: Team primary key
            status: Membership status filter (default: ACTIVE only)
        
        Returns:
            List of RosterMember DTOs sorted by role hierarchy then join date
        
        Raises:
            NotFoundError: If team_id does not exist
            ValidationError: If status is invalid
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Uses select_related('user') to prevent N+1
            - Sorted in Python (no database ORDER BY for flexibility)
        
        Example:
            roster = TeamService.get_roster_members(team_id=42)
            for member in roster:
                print(f"{member.username} ({member.role})")
        """
        from apps.organizations.models import Team, TeamMembership
        
        # Validate team exists (1 query)
        if not Team.objects.filter(id=team_id).exists():
            raise NotFoundError("team", team_id)
        
        # Build query with user join to prevent N+1 (1 query)
        queryset = TeamMembership.objects.select_related('user').filter(team_id=team_id)
        
        # Apply status filter
        if status != "ALL":
            queryset = queryset.filter(status=status)
        
        # Fetch memberships
        memberships = list(queryset)
        
        # Build RosterMember DTOs
        roster = []
        for membership in memberships:
            roster.append(RosterMember(
                membership_id=membership.id,
                user_id=membership.user.id,
                username=membership.user.username,
                display_name=getattr(membership.user, 'display_name', membership.user.username),
                role=membership.role,
                roster_slot=membership.roster_slot or '',
                status=membership.status,
                is_tournament_captain=membership.is_tournament_captain,
                joined_date=membership.joined_at.isoformat(),
            ))
        
        # Sort by role hierarchy (Owner > Manager > Coach > Player > Substitute > Analyst > Scout)
        role_priority = {
            'OWNER': 1,
            'MANAGER': 2,
            'COACH': 3,
            'PLAYER': 4,
            'SUBSTITUTE': 5,
            'ANALYST': 6,
            'SCOUT': 7,
        }
        roster.sort(key=lambda m: (role_priority.get(m.role, 99), m.joined_date))
        
        return roster
    
    @staticmethod
    def get_team_detail(
        *,
        team_id: Optional[int] = None,
        team_slug: Optional[str] = None,
        include_members: bool = True,
        include_invites: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive team information for detail page.
        
        Args:
            team_id: Team primary key (optional if team_slug provided)
            team_slug: Team URL slug (optional if team_id provided)
            include_members: If True, fetch all active members (default: True)
            include_invites: If True, fetch pending invitations (default: False)
        
        Returns:
            Dict with keys: {team, members, invites}
        
        Raises:
            NotFoundError: If team not found
            ValidationError: If neither team_id nor team_slug provided
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses select_related('organization', 'created_by') for team
            - Uses prefetch_related('memberships__user') for members
        """
        from apps.organizations.models import Team
        
        # Validate inputs
        if not team_id and not team_slug:
            raise ValidationError("Either team_id or team_slug must be provided")
        
        # Query team with related data (1-2 queries with prefetch)
        try:
            queryset = Team.objects.select_related('organization', 'created_by')
            if team_id:
                team = queryset.get(id=team_id)
            else:
                team = queryset.get(slug=team_slug)
        except Team.DoesNotExist:
            raise NotFoundError("team", team_id or team_slug)
        
        # Build team dict
        team_data = {
            'id': team.id,
            'name': team.name,
            'slug': team.slug,
            'logo_url': team.logo.url if team.logo else '/static/images/default_team_logo.png',
            'banner_url': team.banner.url if team.banner else None,
            'game_id': team.game_id,
            'region': team.region,
            'status': team.status,
            'description': team.description,
            'is_organization_team': team.organization is not None,
            'organization_name': team.organization.name if team.organization else None,
            'organization_slug': team.organization.slug if team.organization else None,
            'creator_username': team.created_by.username if team.created_by else None,
            'created_at': team.created_at.isoformat(),
        }
        
        result = {'team': team_data}
        
        # Include members if requested
        if include_members:
            result['members'] = [
                {
                    'id': m.membership_id,  # Frontend expects 'id' for member operations
                    'membership_id': m.membership_id,
                    'user_id': m.user_id,
                    'username': m.username,
                    'display_name': m.display_name,
                    'role': m.role,
                    'roster_slot': m.roster_slot,
                    'status': m.status,
                    'is_tournament_captain': m.is_tournament_captain,
                    'joined_date': m.joined_date,
                }
                for m in TeamService.get_roster_members(team.id, status='ACTIVE')
            ]
        else:
            result['members'] = []
        
        # Include invites if requested (placeholder for now)
        if include_invites:
            result['invites'] = []  # TODO: Implement invite system in future task
        else:
            result['invites'] = []
        
        return result
    
    @staticmethod
    def add_team_member(
        *,
        team_id: int,
        user_lookup: str,
        role: str,
        roster_slot: Optional[str] = None,
        added_by_user_id: int,
        is_active: bool = True
    ) -> int:
        """
        Add a new member to team roster.
        
        Args:
            team_id: Team primary key
            user_lookup: User ID, username, or email
            role: MembershipRole choice (OWNER, MANAGER, COACH, PLAYER, etc.)
            roster_slot: RosterSlot choice (STARTER, SUBSTITUTE, etc.)
            added_by_user_id: User performing the action (for permission check)
            is_active: If True, status=ACTIVE; if False, status=INVITED
        
        Returns:
            New membership ID
        
        Raises:
            NotFoundError: If team or user not found
            PermissionDeniedError: If added_by_user doesn't have permission
            ValidationError: If role/slot invalid, or user already has active membership
            ConflictError: If adding OWNER to organization-owned team
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses transaction.atomic for data integrity
        """
        from django.db import transaction
        from apps.organizations.models import Team, TeamMembership, OrganizationMembership
        from apps.organizations.choices import MembershipRole, MembershipStatus, RosterSlot
        
        with transaction.atomic():
            # Get team with organization (1 query with lock)
            try:
                team = Team.objects.select_related('organization', 'created_by').select_for_update().get(id=team_id)
            except Team.DoesNotExist:
                raise NotFoundError("team", team_id)
            
            # Permission check
            if team.organization:
                # Org-owned team: Check if user is org CEO or MANAGER
                org_membership = OrganizationMembership.objects.filter(
                    organization=team.organization,
                    user_id=added_by_user_id,
                    role__in=['CEO', 'MANAGER']
                ).first()
                
                # Also check if user is team OWNER or MANAGER
                team_membership = TeamMembership.objects.filter(
                    team=team,
                    user_id=added_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).first()
                
                if not org_membership and not team_membership:
                    raise PermissionDeniedError("Only organization managers or team managers can add members")
            else:
                # Independent team: Check if user is OWNER or MANAGER
                if not TeamMembership.objects.filter(
                    team=team,
                    user_id=added_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).exists():
                    raise PermissionDeniedError("Only team owner or managers can add members")
            
            # Validate role
            valid_roles = [choice[0] for choice in MembershipRole.choices]
            if role not in valid_roles:
                raise ValidationError(f"Invalid role: {role}")
            
            # Prevent adding OWNER to organization-owned team
            if role == MembershipRole.OWNER and team.organization:
                raise ConflictError("Organization-owned teams cannot have OWNER role members")
            
            # Validate roster slot if provided
            if roster_slot:
                valid_slots = [choice[0] for choice in RosterSlot.choices]
                if roster_slot not in valid_slots:
                    raise ValidationError(f"Invalid roster slot: {roster_slot}")
            
            # Find user by ID, username, or email
            User = get_user_model()
            user = None
            if user_lookup.isdigit():
                try:
                    user = User.objects.get(id=int(user_lookup))
                except User.DoesNotExist:
                    pass
            
            if not user:
                try:
                    user = User.objects.get(username=user_lookup)
                except User.DoesNotExist:
                    try:
                        user = User.objects.get(email=user_lookup)
                    except User.DoesNotExist:
                        raise NotFoundError("user", user_lookup)
            
            # Check for existing active membership
            existing = TeamMembership.objects.filter(
                team=team,
                user=user,
                status=MembershipStatus.ACTIVE
            ).first()
            
            if existing:
                raise ConflictError(f"User {user.username} already has an active membership on this team")
            
            # Create membership
            status = MembershipStatus.ACTIVE if is_active else MembershipStatus.INVITED
            membership = TeamMembership.objects.create(
                team=team,
                user=user,
                role=role,
                roster_slot=roster_slot,
                status=status,
                is_tournament_captain=False,
            )
            
            return membership.id
    
    @staticmethod
    def update_member_role(
        *,
        membership_id: int,
        role: Optional[str] = None,
        roster_slot: Optional[str] = None,
        updated_by_user_id: int
    ) -> Dict[str, Any]:
        """
        Update member's role or roster slot.
        
        Args:
            membership_id: TeamMembership primary key
            role: New role (optional, keeps current if None)
            roster_slot: New roster slot (optional, keeps current if None)
            updated_by_user_id: User performing action (for permission check)
        
        Returns:
            Updated member dict with all fields
        
        Raises:
            NotFoundError: If membership not found
            PermissionDeniedError: If user doesn't have permission
            ValidationError: If role/slot invalid
            ConflictError: If trying to change/remove OWNER on independent team
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses transaction.atomic + select_for_update
        """
        from django.db import transaction
        from apps.organizations.models import Team, TeamMembership, OrganizationMembership
        from apps.organizations.choices import MembershipRole, MembershipStatus, RosterSlot
        
        with transaction.atomic():
            # Get membership with team and organization (1 query with lock)
            try:
                membership = TeamMembership.objects.select_related(
                    'team__organization', 'user'
                ).select_for_update().get(id=membership_id)
            except TeamMembership.DoesNotExist:
                raise NotFoundError("membership", membership_id)
            
            team = membership.team
            
            # Permission check (same logic as add_team_member)
            if team.organization:
                org_membership = OrganizationMembership.objects.filter(
                    organization=team.organization,
                    user_id=updated_by_user_id,
                    role__in=['CEO', 'MANAGER']
                ).first()
                
                team_membership = TeamMembership.objects.filter(
                    team=team,
                    user_id=updated_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).first()
                
                if not org_membership and not team_membership:
                    raise PermissionDeniedError("Only organization managers or team managers can update roles")
            else:
                if not TeamMembership.objects.filter(
                    team=team,
                    user_id=updated_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).exists():
                    raise PermissionDeniedError("Only team owner or managers can update roles")
            
            # HARD RULE: Cannot change OWNER role on independent teams
            if membership.role == MembershipRole.OWNER and not team.organization:
                raise ConflictError("Cannot change OWNER role on independent teams (transfer ownership not implemented)")
            
            # Update role if provided
            if role:
                valid_roles = [choice[0] for choice in MembershipRole.choices]
                if role not in valid_roles:
                    raise ValidationError(f"Invalid role: {role}")
                
                # Prevent setting OWNER on org-owned teams
                if role == MembershipRole.OWNER and team.organization:
                    raise ConflictError("Organization-owned teams cannot have OWNER role members")
                
                membership.role = role
            
            # Update roster slot if provided
            if roster_slot:
                valid_slots = [choice[0] for choice in RosterSlot.choices]
                if roster_slot not in valid_slots:
                    raise ValidationError(f"Invalid roster slot: {roster_slot}")
                membership.roster_slot = roster_slot
            
            membership.save()
            
            # Return updated member dict
            return {
                'id': membership.id,
                'user_id': membership.user.id,
                'username': membership.user.username,
                'display_name': getattr(membership.user, 'display_name', membership.user.username),
                'role': membership.role,
                'roster_slot': membership.roster_slot or '',
                'status': membership.status,
                'is_tournament_captain': membership.is_tournament_captain,
                'joined_date': membership.joined_at.isoformat(),
            }
    
    @staticmethod
    def remove_team_member(
        *,
        membership_id: int,
        removed_by_user_id: int
    ) -> bool:
        """
        Remove member from team roster.
        
        Args:
            membership_id: TeamMembership primary key
            removed_by_user_id: User performing action (for permission check)
        
        Returns:
            True if removed successfully
        
        Raises:
            NotFoundError: If membership not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If trying to remove OWNER from independent team
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses transaction.atomic
        """
        from django.db import transaction
        from apps.organizations.models import Team, TeamMembership, OrganizationMembership
        from apps.organizations.choices import MembershipRole, MembershipStatus
        from django.utils import timezone
        
        with transaction.atomic():
            # Get membership (1 query with lock)
            try:
                membership = TeamMembership.objects.select_related(
                    'team__organization', 'user'
                ).select_for_update().get(id=membership_id)
            except TeamMembership.DoesNotExist:
                raise NotFoundError("membership", membership_id)
            
            team = membership.team
            
            # Permission check
            if team.organization:
                org_membership = OrganizationMembership.objects.filter(
                    organization=team.organization,
                    user_id=removed_by_user_id,
                    role__in=['CEO', 'MANAGER']
                ).first()
                
                team_membership = TeamMembership.objects.filter(
                    team=team,
                    user_id=removed_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).first()
                
                if not org_membership and not team_membership:
                    raise PermissionDeniedError("Only organization managers or team managers can remove members")
            else:
                if not TeamMembership.objects.filter(
                    team=team,
                    user_id=removed_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).exists():
                    raise PermissionDeniedError("Only team owner or managers can remove members")
            
            # HARD RULE: Cannot remove OWNER from independent teams
            if membership.role == MembershipRole.OWNER and not team.organization:
                raise ConflictError("Cannot remove OWNER from independent teams (transfer ownership first)")
            
            # Soft delete: set status to INACTIVE
            membership.status = MembershipStatus.INACTIVE
            membership.left_at = timezone.now()
            membership.left_reason = 'Removed by manager'
            membership.save()
            
            return True
    
    @staticmethod
    def update_team_settings(
        *,
        team_id: int,
        updated_by_user_id: int,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        region: Optional[str] = None,
        description: Optional[str] = None,
        preferred_server: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update team branding and settings.
        
        Args:
            team_id: Team primary key
            updated_by_user_id: User performing action (for permission check)
            logo_url: New logo URL (optional)
            banner_url: New banner URL (optional)
            region: New region (optional)
            description: New description (optional)
            preferred_server: New preferred server (optional)
        
        Returns:
            Updated team dict
        
        Raises:
            NotFoundError: If team not found
            PermissionDeniedError: If user doesn't have permission
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses transaction.atomic
        """
        from django.db import transaction
        from apps.organizations.models import Team, TeamMembership, OrganizationMembership
        from apps.organizations.choices import MembershipRole, MembershipStatus
        
        with transaction.atomic():
            # Get team (1 query with lock)
            try:
                team = Team.objects.select_related('organization', 'created_by').select_for_update().get(id=team_id)
            except Team.DoesNotExist:
                raise NotFoundError("team", team_id)
            
            # Permission check
            if team.organization:
                org_membership = OrganizationMembership.objects.filter(
                    organization=team.organization,
                    user_id=updated_by_user_id,
                    role__in=['CEO', 'MANAGER']
                ).first()
                
                team_membership = TeamMembership.objects.filter(
                    team=team,
                    user_id=updated_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).first()
                
                if not org_membership and not team_membership:
                    raise PermissionDeniedError("Only organization managers or team managers can update settings")
            else:
                if not TeamMembership.objects.filter(
                    team=team,
                    user_id=updated_by_user_id,
                    status=MembershipStatus.ACTIVE,
                    role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]
                ).exists():
                    raise PermissionDeniedError("Only team owner or managers can update settings")
            
            # Update fields (partial update)
            if logo_url is not None:
                # TODO: Handle file upload instead of URL
                pass  # Skip for now, will implement file upload in future
            
            if banner_url is not None:
                pass  # Skip for now, will implement file upload in future
            
            if region is not None:
                team.region = region
            
            if description is not None:
                team.description = description
            
            if preferred_server is not None:
                team.preferred_server = preferred_server
            
            team.save()
            
            # Return updated team dict
            return {
                'id': team.id,
                'name': team.name,
                'slug': team.slug,
                'logo_url': team.logo.url if team.logo else '/static/images/default_team_logo.png',
                'banner_url': team.banner.url if team.banner else None,
                'game_id': team.game_id,
                'region': team.region,
                'status': team.status,
                'description': team.description,
                'preferred_server': team.preferred_server,
                'is_organization_team': team.organization is not None,
                'organization_name': team.organization.name if team.organization else None,
                'organization_slug': team.organization.slug if team.organization else None,
                'created_at': team.created_at.isoformat(),
            }
    
    # ========================================================================
    # TEAM CREATION (TEMPORARY TEAMS FOR TOURNAMENTS)
    # ========================================================================
    
    @staticmethod
    def create_temporary_team(
        *,
        owner_user_id: int,
        game_id: int,
        name: str,
        tournament_id: Optional[int] = None
    ) -> int:
        """
        Create a temporary team for tournament participation.
        
        Temporary teams are auto-deleted after tournament concludes.
        Used for one-time events where users don't want permanent teams.
        
        Args:
            owner_user_id: User creating the team (becomes owner)
            game_id: Game title ID (FK to games.Game)
            name: Team display name (max 100 chars)
            tournament_id: Tournament this team is created for (optional)
        
        Returns:
            New team ID (integer primary key)
        
        Raises:
            NotFoundError: If owner_user_id or game_id does not exist
            ValidationError: If name is invalid (empty, too long, special chars)
            ConflictError: If slug generated from name already exists
            PermissionDeniedError: If user already owns team for this game
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Slug generation may require multiple attempts (counter increment)
            - Auto-creates TeamRanking via post_save signal (1 additional query)
        
        Business Rules:
            - User can own max 1 independent team per game
            - Temporary teams marked with temporary=True flag
            - Auto-deleted 7 days after tournament end (async job)
        
        Example:
            team_id = TeamService.create_temporary_team(
                owner_user_id=request.user.id,
                game_id=5,  # Valorant
                name="Last Minute Squad",
                tournament_id=123
            )
            return JsonResponse({'team_id': team_id})
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # INTERNAL HELPERS (NOT PART OF PUBLIC CONTRACT)
    # ========================================================================
    
    @staticmethod
    def _get_team_from_either_system(team_id: int):
        """
        Internal helper to route team lookup between legacy and vNext systems.
        
        NOT part of public contract - consumers should use specific service methods.
        
        Migration Logic:
        - Phase 2-4: Query legacy system only
        - Phase 5-7: Check TeamMigrationMap, query appropriate system
        - Phase 8+: Query vNext system only
        
        This method will be implemented with proper routing logic in P2-T2+.
        """
        raise NotImplementedError("Migration routing logic pending")
