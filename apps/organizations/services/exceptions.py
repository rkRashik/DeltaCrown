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
