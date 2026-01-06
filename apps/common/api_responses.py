"""
Common API Response Helpers (Phase 9A-13 Section C)

Provides standardized JSON response formats across all DeltaCrown APIs.

Unified Error Schema:
{
  "success": false,
  "error_code": "VALIDATION_ERROR|LOCKED|VERIFIED_LOCK|DUPLICATE|NOT_FOUND|FORBIDDEN|SERVER_ERROR",
  "message": "Human-readable message",
  "field_errors": {"field": "error"},  // Optional
  "metadata": {"key": "value"}         // Optional
}

Success Schema:
{
  "success": true,
  "data": {...}  // Payload
}
"""

from django.http import JsonResponse
from django.conf import settings
import logging
import traceback as tb

logger = logging.getLogger(__name__)


# Standard HTTP status codes for error types
ERROR_STATUS_MAP = {
    'VALIDATION_ERROR': 400,
    'DUPLICATE': 409,
    'NOT_FOUND': 404,
    'LOCKED': 403,
    'VERIFIED_LOCK': 403,
    'FORBIDDEN': 403,
    'UNAUTHORIZED': 401,
    'SERVER_ERROR': 500,
}


def error_response(
    error_code: str,
    message: str,
    status: int = None,
    field_errors: dict = None,
    metadata: dict = None,
    exception: Exception = None
) -> JsonResponse:
    """
    Generate standardized error response.
    
    Args:
        error_code: Standard error code (VALIDATION_ERROR, LOCKED, etc.)
        message: Human-readable error message
        status: HTTP status code (auto-determined from error_code if None)
        field_errors: Dict mapping field names to error messages
        metadata: Additional context (days_remaining, help_url, etc.)
        exception: Exception object for DEBUG traceback
    
    Returns:
        JsonResponse with standardized error structure
    
    Example:
        return error_response(
            error_code='LOCKED',
            message='Passport locked for 15 days',
            metadata={'days_remaining': 15, 'locked_until': '2026-01-20'}
        )
    """
    # Determine status code
    if status is None:
        status = ERROR_STATUS_MAP.get(error_code, 400)
    
    # Build response payload
    payload = {
        'success': False,
        'error_code': error_code,
        'message': message,
    }
    
    # Add optional fields
    if field_errors:
        payload['field_errors'] = field_errors
    
    if metadata:
        payload['metadata'] = metadata
    
    # Add traceback in DEBUG mode only
    if settings.DEBUG and exception:
        payload['metadata'] = payload.get('metadata', {})
        payload['metadata']['traceback'] = tb.format_exc()
        logger.error(f"API Error [{error_code}]: {message}", exc_info=exception)
    
    return JsonResponse(payload, status=status)


def success_response(data: dict = None, status: int = 200) -> JsonResponse:
    """
    Generate standardized success response.
    
    Args:
        data: Response payload (defaults to empty dict)
        status: HTTP status code (default 200)
    
    Returns:
        JsonResponse with standardized success structure
    
    Example:
        return success_response({
            'passport': passport_data,
            'message': 'Passport created successfully'
        })
    """
    payload = {
        'success': True,
    }
    
    if data is not None:
        payload['data'] = data
    
    return JsonResponse(payload, status=status)


def validation_error_response(field_errors: dict, message: str = None) -> JsonResponse:
    """
    Shortcut for validation errors with field-level details.
    
    Args:
        field_errors: Dict mapping field names to error messages
        message: Overall error message (auto-generated if None)
    
    Returns:
        JsonResponse with VALIDATION_ERROR code
    """
    if message is None:
        message = f"Validation failed for {len(field_errors)} field(s)"
    
    return error_response(
        error_code='VALIDATION_ERROR',
        message=message,
        field_errors=field_errors,
        status=400
    )


def locked_error_response(days_remaining: int, locked_until: str, lock_type: str = 'LOCKED') -> JsonResponse:
    """
    Shortcut for passport lock errors.
    
    Args:
        days_remaining: Days until lock expires
        locked_until: ISO timestamp of lock expiration
        lock_type: LOCKED (time-based) or VERIFIED_LOCK (permanent)
    
    Returns:
        JsonResponse with LOCKED or VERIFIED_LOCK code
    """
    if lock_type == 'VERIFIED_LOCK':
        message = 'This passport is verified and cannot be edited. Contact support if you need to update identity fields.'
        metadata = {}
    else:
        message = f'This passport is locked for {days_remaining} more days. Identity changes are restricted by Fair Play Protocol.'
        metadata = {
            'days_remaining': days_remaining,
            'locked_until': locked_until,
        }
    
    return error_response(
        error_code=lock_type,
        message=message,
        metadata=metadata,
        status=403
    )


def duplicate_error_response(resource_type: str, existing_id: int = None) -> JsonResponse:
    """
    Shortcut for duplicate resource errors.
    
    Args:
        resource_type: Type of resource (e.g., 'passport', 'team')
        existing_id: ID of existing resource
    
    Returns:
        JsonResponse with DUPLICATE code
    """
    message = f'{resource_type.capitalize()} already exists'
    metadata = {}
    
    if existing_id:
        metadata['existing_id'] = existing_id
    
    return error_response(
        error_code='DUPLICATE',
        message=message,
        metadata=metadata if metadata else None,
        status=409
    )


def not_found_error_response(resource_type: str, resource_id: str = None) -> JsonResponse:
    """
    Shortcut for not found errors.
    
    Args:
        resource_type: Type of resource (e.g., 'passport', 'game')
        resource_id: ID or slug of missing resource
    
    Returns:
        JsonResponse with NOT_FOUND code
    """
    if resource_id:
        message = f'{resource_type.capitalize()} "{resource_id}" not found'
    else:
        message = f'{resource_type.capitalize()} not found'
    
    return error_response(
        error_code='NOT_FOUND',
        message=message,
        status=404
    )
