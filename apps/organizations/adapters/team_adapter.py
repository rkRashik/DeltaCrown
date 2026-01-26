"""
TeamAdapter - Routing layer for legacy and vNext team operations.

This adapter provides unified access to team functionality during the migration
period (Phases 3-7), routing requests to either the legacy system (apps.teams)
or the vNext system (apps.organizations) based on migration state.

Design Principles:
- Zero breaking changes to existing behavior
- Performance overhead: +1 query maximum for routing decision
- Legacy behavior preserved identically (no refactoring)
- Fail-safe: If routing is ambiguous, prefer legacy system
- Feature flags control routing behavior (P3-T2)

Feature Flags (P3-T2):
- TEAM_VNEXT_FORCE_LEGACY: Emergency killswitch (forces all legacy)
- TEAM_VNEXT_ADAPTER_ENABLED: Master switch for adapter
- TEAM_VNEXT_ROUTING_MODE: "legacy_only" | "vnext_only" | "auto"
- TEAM_VNEXT_TEAM_ALLOWLIST: List of team IDs for auto mode

Thread Safety: All methods are thread-safe (no shared mutable state).
"""

import time
from typing import Dict, Any, Optional
from django.urls import reverse
from django.db.models import Q

# vNext system imports
from apps.organizations.models import Team as VNextTeam, TeamMembership as VNextMembership
from apps.organizations.services.team_service import TeamService
from apps.organizations.services.exceptions import NotFoundError

# Legacy system imports (for fallback behavior)
from apps.teams.models import Team as LegacyTeam, TeamMembership as LegacyMembership

# Feature flags and metrics (P3-T2)
from .flags import should_use_vnext_routing, get_routing_reason
from .metrics import record_routing_decision, record_adapter_error, MetricsContext


class TeamAdapter:
    """
    Adapter for routing team operations to correct backend.
    
    Routing Logic:
        1. Check if team_id exists in TeamMigrationMap → use vNext
        2. Otherwise check if team_id exists in organizations.Team → use vNext
        3. Otherwise → use legacy system (apps.teams)
    
    Performance:
        - Routing decision: 1-2 queries (cached in future phases)
        - get_team_url: +0 queries beyond routing
        - get_team_identity: +1-2 queries beyond routing
        - validate_roster: +3-5 queries beyond routing
    """
    
    def __init__(self):
        """Initialize adapter (stateless, no configuration needed)."""
        pass
    
    # ============================================================================
    # ROUTING DECISION
    # ============================================================================
    
    def is_vnext_team(self, team_id: int) -> bool:
        """
        Determine if team_id belongs to vNext system.
        
        Strategy (P3-T2 with feature flags):
            1. Check feature flags first (should_use_vnext_routing)
               - If flags say legacy → return False (no DB query)
               - If flags say vNext → check database existence
            2. Check TeamMigrationMap (Phase 5-7 migrations)
            3. Check direct existence in organizations.Team
            4. Return False if neither (assume legacy)
        
        Args:
            team_id: Primary key of team
            
        Returns:
            True if team is in vNext system, False if legacy
            
        Performance:
            - With flags disabled: 0 queries (immediate return False)
            - Phase 3-4: 1 query (organizations.Team.objects.filter(id=team_id).exists())
            - Phase 5-7: 2 queries (check map first, then direct)
            - TODO P4-T2: Add caching layer to reduce to 0 queries
        
        Note:
            This method is conservative: when in doubt, it returns False (legacy)
            to prevent breaking existing functionality.
        """
        # P3-T2: Feature flag check (zero queries, fast exit)
        start_time = time.time()
        
        use_vnext = should_use_vnext_routing(team_id)
        
        # Record routing decision with metrics
        duration_ms = (time.time() - start_time) * 1000
        path = "vnext" if use_vnext else "legacy"
        reason = get_routing_reason(team_id)
        record_routing_decision(team_id, path, reason, duration_ms)
        
        # If flags say legacy, don't query database at all
        if not use_vnext:
            return False
        
        # Phase 5-7: Check TeamMigrationMap first (not implemented yet)
        # TODO P5-T3: Uncomment when migration map is populated
        # from apps.organizations.models import TeamMigrationMap
        # if TeamMigrationMap.objects.filter(legacy_team_id=team_id).exists():
        #     return True
        
        # Phase 3-4: Direct existence check in vNext system
        # Note: This is fast (PK index lookup) and safe (no false positives)
        exists = VNextTeam.objects.filter(id=team_id).exists()
        
        # If flags said vNext but team doesn't exist, log discrepancy
        if not exists:
            record_adapter_error(
                team_id=team_id,
                error_code="VNEXT_TEAM_NOT_FOUND",
                path="vnext",
                duration_ms=(time.time() - start_time) * 1000,
            )
        
        return exists
    
    # ============================================================================
    # TEAM URL GENERATION
    # ============================================================================
    
    def get_team_url(self, team_id: int) -> str:
        """
        Generate team detail page URL (works for both legacy and vNext).
        
        Routing Strategy:
            - vNext teams: Use TeamService.get_team_url(team_id)
            - Legacy teams: Use legacy URL pattern (teams:team_detail)
        
        Args:
            team_id: Primary key of team
            
        Returns:
            Absolute URL path (e.g., "/organizations/protocol-v/" or "/teams/protocol-v/")
            
        Raises:
            NotFoundError: If team_id does not exist in either system
            
        Performance:
            - vNext path: 1-2 queries (routing + TeamService.get_team_url)
            - Legacy path: 1-2 queries (routing + legacy Team lookup for slug)
        
        Examples:
            >>> adapter = TeamAdapter()
            >>> adapter.get_team_url(123)  # vNext team
            '/organizations/protocol-v/'
            >>> adapter.get_team_url(456)  # legacy team
            '/teams/syntax-gaming/'
        """
        # P3-T2: Metrics tracking
        start_time = time.time()
        path = "vnext" if self.is_vnext_team(team_id) else "legacy"
        
        try:
            with MetricsContext("get_team_url", team_id, path):
                if path == "vnext":
                    # vNext path: Use TeamService
                    try:
                        team_identity = TeamService.get_team_identity(team_id=team_id)
                        # Use vNext URL pattern (organizations app)
                        return reverse('organizations:team_detail', kwargs={'team_slug': team_identity.slug})
                    except NotFoundError:
                        # Should not happen if is_vnext_team returned True, but fail-safe
                        raise NotFoundError(
                            message=f"Team {team_id} not found in vNext system",
                            error_code="TEAM_NOT_FOUND",
                        )
                else:
                    # Legacy path: Use existing legacy Team model
                    try:
                        legacy_team = LegacyTeam.objects.get(id=team_id)
                        # Use vNext URL pattern (all team URLs now in organizations app)
                        return reverse('organizations:team_detail', kwargs={'team_slug': legacy_team.slug})
                    except LegacyTeam.DoesNotExist:
                        raise NotFoundError(
                            message=f"Team {team_id} not found in legacy system",
                            error_code="TEAM_NOT_FOUND",
                        )
        except NotFoundError as e:
            # P3-T2: Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            record_adapter_error(
                team_id=team_id,
                error_code=e.error_code,
                path=path,
                duration_ms=duration_ms,
                exception_type="NotFoundError",
            )
            raise
    
    # ============================================================================
    # TEAM IDENTITY (BRANDING & METADATA)
    # ============================================================================
    
    def get_team_identity(self, team_id: int) -> Dict[str, Any]:
        """
        Retrieve team branding and metadata for display purposes.
        
        Routing Strategy:
            - vNext teams: Use TeamService.get_team_identity() and convert to dict
            - Legacy teams: Query legacy Team model and format to same structure
        
        Args:
            team_id: Primary key of team
            
        Returns:
            Dictionary with standardized team identity fields (see contracts.py)
            
        Raises:
            NotFoundError: If team_id does not exist in either system
            
        Performance:
            - vNext path: 2-3 queries (routing + TeamService.get_team_identity)
            - Legacy path: 2-3 queries (routing + legacy Team with select_related)
        
        Examples:
            >>> adapter = TeamAdapter()
            >>> identity = adapter.get_team_identity(123)
            >>> identity['name']
            'Protocol V'
            >>> identity['is_org_team']
            True  # vNext team
        """
        # P3-T2: Metrics tracking
        start_time = time.time()
        path = "vnext" if self.is_vnext_team(team_id) else "legacy"
        
        try:
            with MetricsContext("get_team_identity", team_id, path):
                if path == "vnext":
                    # vNext path: Use TeamService
                    try:
                        team_identity = TeamService.get_team_identity(team_id=team_id)
                        # Convert DTO to dict for standardized interface
                        return {
                            'team_id': team_identity.team_id,
                            'name': team_identity.name,
                            'slug': team_identity.slug,
                            'logo_url': team_identity.logo_url,
                            'badge_url': team_identity.badge_url,
                            'game_name': team_identity.game_name,
                            'game_id': team_identity.game_id,
                            'region': team_identity.region,
                            'is_verified': team_identity.is_verified,
                            'is_org_team': team_identity.is_org_team,
                            'organization_name': team_identity.organization_name,
                            'organization_slug': team_identity.organization_slug,
                        }
                    except NotFoundError:
                        raise NotFoundError(
                            message=f"Team {team_id} not found in vNext system",
                            error_code="TEAM_NOT_FOUND",
                        )
                else:
                    # Legacy path: Query legacy Team model directly
                    try:
                        legacy_team = LegacyTeam.objects.select_related('game').get(id=team_id)
                        
                        # Format legacy team data to match vNext structure
                        # Note: Legacy teams do NOT have organization relationships
                        return {
                            'team_id': legacy_team.id,
                            'name': legacy_team.name,
                            'slug': legacy_team.slug,
                            'logo_url': legacy_team.logo.url if legacy_team.logo else '',
                            'badge_url': None,  # Legacy teams have no org badges
                            'game_name': legacy_team.game.name if legacy_team.game else '',
                            'game_id': legacy_team.game.id if legacy_team.game else None,
                            'region': legacy_team.region if hasattr(legacy_team, 'region') else 'UNKNOWN',
                            'is_verified': False,  # Legacy teams not verified
                            'is_org_team': False,  # Explicitly False for legacy
                            'organization_name': None,
                            'organization_slug': None,
                        }
                    except LegacyTeam.DoesNotExist:
                        raise NotFoundError(
                            message=f"Team {team_id} not found in legacy system",
                            error_code="TEAM_NOT_FOUND",
                        )
        except NotFoundError as e:
            # P3-T2: Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            record_adapter_error(
                team_id=team_id,
                error_code=e.error_code,
                path=path,
                duration_ms=duration_ms,
                exception_type="NotFoundError",
            )
            raise
    
    # ============================================================================
    # ROSTER VALIDATION (TOURNAMENT REGISTRATION)
    # ============================================================================
    
    def validate_roster(
        self,
        team_id: int,
        tournament_id: Optional[int] = None,
        game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate team roster eligibility for tournament registration.
        
        Routing Strategy:
            - vNext teams: Use TeamService.validate_roster()
            - Legacy teams: Call existing legacy validation logic (unchanged)
        
        Args:
            team_id: Primary key of team
            tournament_id: Optional tournament ID for tournament-specific rules
            game_id: Optional game ID for game-specific validation
            
        Returns:
            Validation result dictionary (see contracts.py for structure)
            
        Raises:
            NotFoundError: If team_id does not exist in either system
            
        Performance:
            - vNext path: ≤6 queries (routing + TeamService.validate_roster)
            - Legacy path: ≤5 queries (routing + legacy validation logic)
        
        Examples:
            >>> adapter = TeamAdapter()
            >>> result = adapter.validate_roster(123, tournament_id=456)
            >>> result['is_valid']
            True
            >>> result['errors']
            []
        """
        # P3-T2: Metrics tracking
        start_time = time.time()
        path = "vnext" if self.is_vnext_team(team_id) else "legacy"
        
        try:
            with MetricsContext("validate_roster", team_id, path):
                if path == "vnext":
                    # vNext path: Use TeamService
                    try:
                        validation_result = TeamService.validate_roster(
                            team_id=team_id,
                            tournament_id=tournament_id,
                            game_id=game_id,
                        )
                        # Convert DTO to dict for standardized interface
                        return {
                            'is_valid': validation_result.is_valid,
                            'errors': validation_result.errors,
                            'warnings': validation_result.warnings,
                            'roster_data': validation_result.roster_data,
                        }
                    except NotFoundError:
                        raise NotFoundError(
                            message=f"Team {team_id} not found in vNext system",
                            error_code="TEAM_NOT_FOUND",
                        )
                else:
                    # Legacy path: Use existing legacy validation logic
                    # NOTE: This preserves legacy behavior EXACTLY as-is (no refactoring)
                    return self._legacy_validate_roster(team_id, tournament_id, game_id)
        except NotFoundError as e:
            # P3-T2: Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            record_adapter_error(
                team_id=team_id,
                error_code=e.error_code,
                path=path,
                duration_ms=duration_ms,
                exception_type="NotFoundError",
            )
            raise
    
    def _legacy_validate_roster(
        self,
        team_id: int,
        tournament_id: Optional[int] = None,
        game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Legacy roster validation logic (preserved from apps.tournaments).
        
        This is a thin wrapper around the existing tournament roster validation
        that dependent apps currently use. It is NOT refactored to avoid breaking
        changes to legacy team behavior.
        
        Args:
            team_id: Legacy team primary key
            tournament_id: Optional tournament ID
            game_id: Optional game ID
            
        Returns:
            Validation result matching vNext structure
            
        Raises:
            NotFoundError: If legacy team does not exist
            
        Performance:
            ≤5 queries (same as current tournament validation)
        
        Implementation Notes:
            - This method wraps existing tournament validation logic
            - It does NOT import from tournaments.services to avoid circular deps
            - Instead, it reimplements the minimal validation inline
            - Future refactoring will consolidate this into TeamService
        """
        try:
            legacy_team = LegacyTeam.objects.get(id=team_id)
        except LegacyTeam.DoesNotExist:
            raise NotFoundError(
                message=f"Team {team_id} not found in legacy system",
                error_code="TEAM_NOT_FOUND",
            )
        
        # Basic roster validation (mirrors current tournament logic)
        errors = []
        warnings = []
        roster_data = {}
        
        # Count active members
        active_members = LegacyMembership.objects.filter(
            team=legacy_team,
            status='ACTIVE',
        ).select_related('profile__user')
        
        active_count = active_members.count()
        roster_data['active_count'] = active_count
        
        # Minimum roster size check (game-specific, default to 5)
        min_roster_size = 5  # TODO: Make game-specific
        if active_count < min_roster_size:
            errors.append(f"Roster size ({active_count}) below minimum ({min_roster_size})")
        
        # Check for tournament locks (if tournament_id provided)
        if tournament_id:
            # TODO P3-T2: Add proper tournament lock checking
            # For now, assume no locks (legacy behavior preserved)
            roster_data['tournament_locks'] = []
        
        # Validation result
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'roster_data': roster_data,
        }
