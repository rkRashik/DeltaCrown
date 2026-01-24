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
    """
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
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
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
