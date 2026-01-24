"""
Service Layer - Unified API for Team & Organization operations.

This module provides the service layer interface for the vNext Team and
Organization system. Services abstract business logic away from views/APIs
and handle routing between legacy and vNext systems during migration.

Architecture:
- TeamService: Team lifecycle, roster management, authorization
- OrganizationService: Organization lifecycle, membership management
- RankingService: Crown Point calculations, tier updates, leaderboards

Usage:
    from apps.organizations.services import TeamService, OrganizationService
    
    # Get team identity for display
    team = TeamService.get_team_identity(team_id=42)
    
    # Validate tournament eligibility
    result = TeamService.validate_roster(
        team_id=42,
        tournament_id=100,
        game_id=1
    )
    if not result.is_valid:
        return HttpResponseBadRequest(result.errors)
    
    # Apply match result
    delta = RankingService.apply_match_result(
        winner_team_id=42,
        loser_team_id=99,
        match_id=12345
    )

Exception Handling:
    from apps.organizations.services import (
        TeamServiceError,
        NotFoundError,
        ValidationError
    )
    
    try:
        team = TeamService.get_team_identity(team_id=42)
    except NotFoundError as e:
        return JsonResponse({'error': e.safe_message}, status=404)
    except TeamServiceError as e:
        logger.error(f"Team service error: {e}", extra=e.details)
        return JsonResponse({'error': 'Service unavailable'}, status=503)

Performance Contract:
- Simple reads: <50ms (p95), ≤3 queries
- Complex reads/writes: <100ms (p95), ≤5 queries
- Consumers should implement caching at API/view layer

Migration Phases:
- Phase 2-4: Services route to legacy apps.teams (READ-ONLY)
- Phase 5-7: Services check TeamMigrationMap, route to either system
- Phase 8+: Services route exclusively to apps.organizations (vNext)
"""

# Service classes
from .team_service import TeamService
from .organization_service import OrganizationService
from .ranking_service import RankingService

# DTOs (for type hints in consumer code)
from .team_service import (
    TeamIdentity,
    WalletInfo,
    ValidationResult,
    RosterMember,
)
from .organization_service import (
    OrganizationInfo,
    OrganizationMember,
)
from .ranking_service import (
    RankingSnapshot,
    MatchResultDelta,
)

# Exceptions (for error handling)
from .exceptions import (
    # Base classes
    TeamServiceError,
    OrganizationServiceError,
    RankingServiceError,
    
    # Typed exceptions
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    ConflictError,
    ContractViolationError,
    ServiceUnavailableError,
)

__all__ = [
    # Services
    'TeamService',
    'OrganizationService',
    'RankingService',
    
    # Team DTOs
    'TeamIdentity',
    'WalletInfo',
    'ValidationResult',
    'RosterMember',
    
    # Organization DTOs
    'OrganizationInfo',
    'OrganizationMember',
    
    # Ranking DTOs
    'RankingSnapshot',
    'MatchResultDelta',
    
    # Exception base classes
    'TeamServiceError',
    'OrganizationServiceError',
    'RankingServiceError',
    
    # Typed exceptions
    'NotFoundError',
    'PermissionDeniedError',
    'ValidationError',
    'ConflictError',
    'ContractViolationError',
    'ServiceUnavailableError',
]
