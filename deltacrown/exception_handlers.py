"""
Custom exception handlers for DRF (Module 9.5).
Provides consistent JSON error responses with proper status codes.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns consistent JSON error responses.
    
    Response format:
    {
        "error": "Error message",
        "code": "ERROR_CODE",
        "details": {...}  # Optional
    }
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)
    
    # Handle DRF exceptions (already have response)
    if response is not None:
        error_data = {
            "error": _get_error_message(response.data),
            "code": _get_error_code(exc.__class__.__name__, response.status_code),
        }
        
        # Add details if available
        if isinstance(response.data, dict) and len(response.data) > 1:
            details = {k: v for k, v in response.data.items() if k not in ['detail', 'error']}
            if details:
                error_data["details"] = details
        
        response.data = error_data
        return response
    
    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        error_data = {
            "error": "Validation error",
            "code": "VALIDATION_ERROR",
        }
        if hasattr(exc, 'message_dict'):
            error_data["details"] = exc.message_dict
        elif hasattr(exc, 'messages'):
            error_data["details"] = {"messages": exc.messages}
        
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle IntegrityError (database constraint violations)
    if isinstance(exc, IntegrityError):
        error_data = {
            "error": "Database constraint violation",
            "code": "INTEGRITY_ERROR",
        }
        logger.error(f"IntegrityError: {str(exc)}", exc_info=True)
        return Response(error_data, status=status.HTTP_409_CONFLICT)
    
    # Log unhandled exceptions
    logger.error(f"Unhandled exception: {exc.__class__.__name__}", exc_info=True)
    
    # Return generic 500 error for unhandled exceptions
    return Response(
        {
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _get_error_message(data):
    """Extract error message from DRF response data."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'error' in data:
            return str(data['error'])
        # Return first error message
        for value in data.values():
            if isinstance(value, (str, list)):
                return str(value[0]) if isinstance(value, list) else str(value)
    if isinstance(data, list):
        return str(data[0]) if data else "An error occurred"
    return "An error occurred"


def _get_error_code(exception_name, status_code):
    """Generate error code based on exception type and status code."""
    code_map = {
        'NotAuthenticated': 'UNAUTHENTICATED',
        'AuthenticationFailed': 'AUTHENTICATION_FAILED',
        'PermissionDenied': 'PERMISSION_DENIED',
        'NotFound': 'NOT_FOUND',
        'ValidationError': 'VALIDATION_ERROR',
        'ParseError': 'PARSE_ERROR',
        'MethodNotAllowed': 'METHOD_NOT_ALLOWED',
        'Throttled': 'RATE_LIMITED',
    }
    
    return code_map.get(exception_name, f'ERROR_{status_code}')
