"""
Test exception contract stability for service layer.

These tests lock down the exception API contract to prevent breaking changes
to error_code strings, safe_message formats, and details structure.
"""

import pytest

from apps.organizations.services import (
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


class TestExceptionBaseClasses:
    """Verify base exception classes have required fields."""
    
    def test_team_service_error_has_error_code(self):
        """TeamServiceError must have error_code field."""
        error = TeamServiceError("Test error")
        assert hasattr(error, "error_code")
        assert isinstance(error.error_code, str)
        assert error.error_code == "TEAM_SERVICE_ERROR"
    
    def test_team_service_error_has_safe_message(self):
        """TeamServiceError must have safe_message field."""
        error = TeamServiceError("Internal error", safe_message="User-friendly message")
        assert hasattr(error, "safe_message")
        assert error.safe_message == "User-friendly message"
    
    def test_team_service_error_has_details(self):
        """TeamServiceError must have details field."""
        error = TeamServiceError("Test error", details={"key": "value"})
        assert hasattr(error, "details")
        assert isinstance(error.details, dict)
        assert error.details["key"] == "value"
    
    def test_organization_service_error_base_class(self):
        """OrganizationServiceError must have stable error_code."""
        error = OrganizationServiceError("Test error")
        assert error.error_code == "ORGANIZATION_SERVICE_ERROR"
        assert hasattr(error, "safe_message")
        assert hasattr(error, "details")
    
    def test_ranking_service_error_base_class(self):
        """RankingServiceError must have stable error_code."""
        error = RankingServiceError("Test error")
        assert error.error_code == "RANKING_SERVICE_ERROR"
        assert hasattr(error, "safe_message")
        assert hasattr(error, "details")


class TestNotFoundError:
    """Verify NotFoundError contract stability."""
    
    def test_not_found_error_inheritance(self):
        """NotFoundError must inherit from TeamServiceError."""
        error = NotFoundError("team", 42)
        assert isinstance(error, TeamServiceError)
    
    def test_not_found_error_code_format(self):
        """NotFoundError must generate UPPER_SNAKE_CASE error_code."""
        error = NotFoundError("team", 42)
        assert error.error_code == "TEAM_NOT_FOUND"
        assert error.error_code.isupper()
        assert "_" in error.error_code
    
    def test_not_found_error_safe_message(self):
        """NotFoundError must have user-friendly safe_message."""
        error = NotFoundError("team", 42)
        assert hasattr(error, "safe_message")
        assert isinstance(error.safe_message, str)
        assert len(error.safe_message) > 0
    
    def test_not_found_error_details_structure(self):
        """NotFoundError must include resource_type and resource_id in details."""
        error = NotFoundError("team", 42)
        assert error.details["resource_type"] == "team"
        assert error.details["resource_id"] == 42


class TestPermissionDeniedError:
    """Verify PermissionDeniedError contract stability."""
    
    def test_permission_denied_error_inheritance(self):
        """PermissionDeniedError must inherit from TeamServiceError."""
        error = PermissionDeniedError("Test message")
        assert isinstance(error, TeamServiceError)
    
    def test_permission_denied_error_code(self):
        """PermissionDeniedError must have stable error_code."""
        error = PermissionDeniedError("Test message")
        assert error.error_code == "PERMISSION_DENIED"
    
    def test_permission_denied_safe_message(self):
        """PermissionDeniedError must have safe_message."""
        error = PermissionDeniedError("Internal reason", safe_message="Access denied")
        assert error.safe_message == "Access denied"


class TestValidationError:
    """Verify ValidationError contract stability."""
    
    def test_validation_error_inheritance(self):
        """ValidationError must inherit from TeamServiceError."""
        error = ValidationError("Test message")
        assert isinstance(error, TeamServiceError)
    
    def test_validation_error_code(self):
        """ValidationError must have stable error_code."""
        error = ValidationError("Test message")
        assert error.error_code == "VALIDATION_ERROR"
    
    def test_validation_error_field_errors(self):
        """ValidationError must support field_errors in details."""
        field_errors = {"name": "Too long", "slug": "Invalid characters"}
        error = ValidationError("Validation failed", details={"field_errors": field_errors})
        assert "field_errors" in error.details
        assert error.details["field_errors"]["name"] == "Too long"


class TestConflictError:
    """Verify ConflictError contract stability."""
    
    def test_conflict_error_inheritance(self):
        """ConflictError must inherit from TeamServiceError."""
        error = ConflictError("Test message")
        assert isinstance(error, TeamServiceError)
    
    def test_conflict_error_code_format(self):
        """ConflictError must generate specific error_code."""
        error = ConflictError("Slug conflict", error_code="TEAM_SLUG_CONFLICT")
        assert error.error_code == "TEAM_SLUG_CONFLICT"
        assert error.error_code.isupper()


class TestContractViolationError:
    """Verify ContractViolationError contract stability."""
    
    def test_contract_violation_error_inheritance(self):
        """ContractViolationError must inherit from TeamServiceError."""
        error = ContractViolationError("Test message")
        assert isinstance(error, TeamServiceError)
    
    def test_contract_violation_error_code(self):
        """ContractViolationError must have stable error_code."""
        error = ContractViolationError(
            "Direct model access",
            error_code="CONTRACT_VIOLATION_DIRECT_MODEL_ACCESS"
        )
        assert error.error_code == "CONTRACT_VIOLATION_DIRECT_MODEL_ACCESS"


class TestServiceUnavailableError:
    """Verify ServiceUnavailableError contract stability."""
    
    def test_service_unavailable_error_inheritance(self):
        """ServiceUnavailableError must inherit from TeamServiceError."""
        error = ServiceUnavailableError("Test message")
        assert isinstance(error, TeamServiceError)
    
    def test_service_unavailable_error_code(self):
        """ServiceUnavailableError must have stable error_code."""
        error = ServiceUnavailableError(
            "API timeout",
            error_code="GAME_PASSPORT_API_UNAVAILABLE"
        )
        assert error.error_code == "GAME_PASSPORT_API_UNAVAILABLE"


class TestExceptionImportability:
    """Verify all exceptions are importable from service root."""
    
    def test_all_exceptions_importable(self):
        """All exception classes must be importable from apps.organizations.services."""
        from apps.organizations.services import (
            TeamServiceError,
            OrganizationServiceError,
            RankingServiceError,
            NotFoundError,
            PermissionDeniedError,
            ValidationError,
            ConflictError,
            ContractViolationError,
            ServiceUnavailableError,
        )
        
        # Verify they are all classes
        assert isinstance(TeamServiceError, type)
        assert isinstance(OrganizationServiceError, type)
        assert isinstance(RankingServiceError, type)
        assert isinstance(NotFoundError, type)
        assert isinstance(PermissionDeniedError, type)
        assert isinstance(ValidationError, type)
        assert isinstance(ConflictError, type)
        assert isinstance(ContractViolationError, type)
        assert isinstance(ServiceUnavailableError, type)
