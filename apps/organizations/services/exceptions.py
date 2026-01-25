"""
Service layer exceptions for Team & Organization vNext system.

These exceptions provide stable error codes and safe messages for consumers.
All service methods should raise these typed exceptions instead of raw
ValueError, IntegrityError, or DoesNotExist exceptions.
"""

from typing import Any, Dict, Optional


class TeamServiceError(Exception):
    """
    Base exception for all Team Service errors.
    
    All service-layer exceptions inherit from this class to enable
    centralized error handling and logging.
    
    Attributes:
        error_code: Stable string identifier for error type (API-safe)
        safe_message: User-facing error message (sanitized, no internal details)
        details: Optional dict with additional context (for logging, not user display)
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEAM_SERVICE_ERROR",
        safe_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.safe_message = safe_message or "An error occurred while processing your request."
        self.details = details or {}


class NotFoundError(TeamServiceError):
    """
    Raised when a requested resource (team, organization, member) does not exist.
    
    Usage:
        if not team_exists:
            raise NotFoundError(
                f"Team {team_id} not found",
                error_code="TEAM_NOT_FOUND",
                safe_message=f"Team with ID {team_id} does not exist."
            )
    """
    
    def __init__(
        self,
        message: str,
        resource_type: str = "Resource",
        resource_id: Any = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_code = f"{resource_type.upper()}_NOT_FOUND"
        safe_message = f"{resource_type} not found."
        if resource_id is not None:
            safe_message = f"{resource_type} with ID {resource_id} not found."
        
        details = details or {}
        details.update({
            'resource_type': resource_type,
            'resource_id': resource_id,
        })
        
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class PermissionDeniedError(TeamServiceError):
    """
    Raised when a user lacks permission to perform an action.
    
    Usage:
        if not user.can_manage_team(team):
            raise PermissionDeniedError(
                f"User {user.id} cannot manage team {team.id}",
                error_code="TEAM_MANAGEMENT_DENIED",
                safe_message="You do not have permission to manage this team.",
                details={'required_role': 'MANAGER'}
            )
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "PERMISSION_DENIED",
        safe_message: str = "You do not have permission to perform this action.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class ValidationError(TeamServiceError):
    """
    Raised when input data fails validation (business logic rules).
    
    Usage:
        if len(team_name) > 100:
            raise ValidationError(
                "Team name too long",
                error_code="TEAM_NAME_TOO_LONG",
                safe_message="Team name must be 100 characters or less.",
                details={'max_length': 100, 'actual_length': len(team_name)}
            )
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        safe_message: str = "The provided data is invalid.",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field_errors:
            details['field_errors'] = field_errors
        
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class ConflictError(TeamServiceError):
    """
    Raised when an operation conflicts with existing state (duplicate slug, roster lock, etc.).
    
    Usage:
        if Team.objects.filter(slug=slug).exists():
            raise ConflictError(
                f"Team slug '{slug}' already exists",
                error_code="TEAM_SLUG_CONFLICT",
                safe_message=f"A team with the slug '{slug}' already exists.",
                details={'slug': slug}
            )
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "CONFLICT_ERROR",
        safe_message: str = "This action conflicts with existing data.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class ContractViolationError(TeamServiceError):
    """
    Raised when service detects violation of compatibility contract assumptions.
    
    This exception should trigger alerts in production as it indicates
    a dependent app is using deprecated patterns or invalid assumptions.
    
    Usage:
        if app_accessing_team_owner_directly:
            raise ContractViolationError(
                "Direct access to team.owner bypasses brand inheritance",
                error_code="CONTRACT_VIOLATION_DIRECT_MODEL_ACCESS",
                safe_message="Invalid team access pattern detected.",
                details={'violating_pattern': 'direct_model_access'}
            )
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "CONTRACT_VIOLATION",
        safe_message: str = "An internal system constraint was violated.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class ServiceUnavailableError(TeamServiceError):
    """
    Raised when service temporarily cannot process request (database down, external API timeout, etc.).
    
    Usage:
        try:
            result = external_api.call()
        except ExternalAPIError:
            raise ServiceUnavailableError(
                "Game Passport API unreachable",
                error_code="GAME_PASSPORT_API_UNAVAILABLE",
                safe_message="Unable to verify Game Passports at this time. Please try again later."
            )
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "SERVICE_UNAVAILABLE",
        safe_message: str = "The service is temporarily unavailable. Please try again later.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            safe_message=safe_message,
            details=details
        )


class OrganizationServiceError(Exception):
    """
    Base exception for Organization Service errors.
    
    Separate from TeamServiceError to enable granular error handling
    for organization-specific operations.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "ORGANIZATION_SERVICE_ERROR",
        safe_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.safe_message = safe_message or "An error occurred while processing organization request."
        self.details = details or {}


class OrganizationAlreadyExistsError(OrganizationServiceError):
    """
    Raised when attempting to create an organization with a name/slug that already exists.
    
    Usage:
        if Organization.objects.filter(slug=slug).exists():
            raise OrganizationAlreadyExistsError(
                f"Organization with slug '{slug}' already exists",
                details={'slug': slug, 'name': name}
            )
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="organization_already_exists",
            safe_message="An organization with this name or identifier already exists.",
            details=details
        )


class OrganizationNotFoundError(OrganizationServiceError):
    """
    Raised when a requested organization does not exist.
    
    Usage:
        if not Organization.objects.filter(id=org_id).exists():
            raise OrganizationNotFoundError(
                f"Organization {org_id} not found",
                organization_id=org_id
            )
    """
    
    def __init__(
        self,
        message: str,
        organization_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if organization_id is not None:
            details['organization_id'] = organization_id
        
        super().__init__(
            message=message,
            error_code="organization_not_found",
            safe_message=f"Organization not found.",
            details=details
        )


class TeamValidationError(TeamServiceError):
    """
    Raised when team data fails validation during creation or update.
    
    Usage:
        if not game_exists:
            raise TeamValidationError(
                f"Game {game_id} does not exist",
                field_errors={'game_id': 'Invalid game ID'}
            )
    """
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field_errors:
            details['field_errors'] = field_errors
        
        super().__init__(
            message=message,
            error_code="team_validation_error",
            safe_message="Team data validation failed.",
            details=details
        )


class RankingServiceError(Exception):
    """
    Base exception for Ranking Service errors.
    
    Used for Crown Point calculations, tier updates, and leaderboard operations.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "RANKING_SERVICE_ERROR",
        safe_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.safe_message = safe_message or "An error occurred while processing ranking request."
        self.details = details or {}


class LegacyWriteBlockedException(TeamServiceError):
    """
    Raised when a write operation is attempted on legacy team models during Phase 5 migration.
    
    This exception is thrown by the LegacyWriteEnforcementMixin when:
    - TEAM_LEGACY_WRITE_BLOCKED=True (default during Phase 5)
    - TEAM_LEGACY_WRITE_BYPASS_ENABLED=False (default)
    
    The exception provides structured information about the blocked write:
    - model: Legacy model class name (e.g., 'Team', 'TeamMembership')
    - operation: Write operation type (e.g., 'save', 'delete', 'bulk_update')
    - table: Database table name (e.g., 'teams_team')
    
    Usage:
        # During Phase 5 migration, any write to legacy models will raise:
        team = Team.objects.get(id=123)
        team.name = "New Name"
        team.save()  # Raises LegacyWriteBlockedException
        
        # Emergency bypass (controlled re-enable):
        settings.TEAM_LEGACY_WRITE_BYPASS_ENABLED = True
        team.save()  # Now allowed, but logged
    
    Error Code: LEGACY_WRITE_BLOCKED (stable, API-safe)
    HTTP Status: 403 Forbidden (operation not permitted during migration)
    """
    
    def __init__(
        self,
        model: str,
        operation: str,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            'model': model,
            'operation': operation,
            'table': table,
            'phase': 'Phase 5 (Data Migration)',
            'bypass_setting': 'TEAM_LEGACY_WRITE_BYPASS_ENABLED',
        })
        
        message = (
            f"Write operation '{operation}' blocked on legacy model '{model}' "
            f"during Phase 5 migration. Legacy tables are read-only. "
            f"Use vNext system (apps.organizations) for new writes."
        )
        
        safe_message = (
            f"This operation is not available during system migration. "
            f"Please use the new team management system or contact support."
        )
        
        super().__init__(
            message=message,
            error_code="LEGACY_WRITE_BLOCKED",
            safe_message=safe_message,
            details=details
        )
