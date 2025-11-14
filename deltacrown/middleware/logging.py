"""
Structured logging middleware (Module 9.5).
Adds correlation IDs and structured logging for all requests.
"""
import uuid
import time
import logging
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('deltacrown.requests')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware that logs all requests with structured data.
    Adds correlation ID to track requests across services.
    """
    
    def process_request(self, request):
        """Add correlation ID and start time to request."""
        # Generate or extract correlation ID
        request.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Log request completion with structured data."""
        if not hasattr(request, 'start_time'):
            return response
        
        duration = time.time() - request.start_time
        
        log_data = {
            'correlation_id': getattr(request, 'correlation_id', None),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'user_id': request.user.id if request.user.is_authenticated else None,
            'remote_addr': _get_client_ip(request),
        }
        
        # Add query params (excluding sensitive data)
        if request.GET:
            log_data['query_params'] = {k: v for k, v in request.GET.items() if k not in ['password', 'token', 'secret']}
        
        # Log based on status code
        if response.status_code >= 500:
            logger.error(f"Request failed: {request.method} {request.path}", extra=log_data)
        elif response.status_code >= 400:
            logger.warning(f"Client error: {request.method} {request.path}", extra=log_data)
        else:
            logger.info(f"Request completed: {request.method} {request.path}", extra=log_data)
        
        # Add correlation ID to response headers
        response['X-Correlation-ID'] = log_data['correlation_id']
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions with correlation ID."""
        log_data = {
            'correlation_id': getattr(request, 'correlation_id', None),
            'method': request.method,
            'path': request.path,
            'exception': exception.__class__.__name__,
            'message': str(exception),
            'user_id': request.user.id if request.user.is_authenticated else None,
        }
        
        logger.exception(f"Unhandled exception: {request.method} {request.path}", extra=log_data)
        return None


def _get_client_ip(request):
    """Extract client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
