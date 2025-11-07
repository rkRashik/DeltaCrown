"""
Health Check Endpoints

Provides health and readiness endpoints for monitoring and load balancer health checks.

Phase 2: Real-Time Features & Security
Module 2.4: Security Hardening

Endpoints:
    - /healthz: Basic health check (no authentication required)
    - /readiness: Readiness check with dependency validation (authentication optional)

Usage:
    # Load balancer health check
    curl http://localhost:8000/healthz
    # Returns: {"status": "ok"}
    
    # Kubernetes readiness probe
    curl http://localhost:8000/readiness
    # Returns: {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
"""

import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def healthz(request):
    """
    Basic health check endpoint.
    
    Returns HTTP 200 if application is running.
    No authentication required - suitable for load balancer health checks.
    
    Response:
        {
            "status": "ok"
        }
    """
    return JsonResponse({'status': 'ok'})


@require_http_methods(["GET"])
def readiness(request):
    """
    Readiness check endpoint with dependency validation.
    
    Checks:
        - Database connectivity
        - Redis connectivity (if configured)
        - Critical services availability
        
    Returns HTTP 200 if all checks pass, HTTP 503 if any fail.
    Authentication optional - can be restricted in production.
    
    Response (success):
        {
            "status": "ready",
            "checks": {
                "database": "ok",
                "redis": "ok"
            }
        }
        
    Response (failure):
        {
            "status": "not_ready",
            "checks": {
                "database": "ok",
                "redis": "error: Connection failed"
            },
            "error": "One or more dependency checks failed"
        }
    """
    checks = {}
    all_passed = True
    
    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        all_passed = False
        logger.error(f"Database health check failed: {e}", exc_info=True)
    
    # Check Redis connectivity (if configured)
    if getattr(settings, 'USE_REDIS_CHANNELS', False):
        try:
            # Test Redis with a simple get/set
            cache.set('healthcheck_ping', 'pong', timeout=10)
            value = cache.get('healthcheck_ping')
            if value == 'pong':
                checks['redis'] = 'ok'
            else:
                checks['redis'] = 'error: Value mismatch'
                all_passed = False
        except Exception as e:
            checks['redis'] = f'error: {str(e)}'
            all_passed = False
            logger.error(f"Redis health check failed: {e}", exc_info=True)
    else:
        checks['redis'] = 'disabled'
    
    # Return appropriate status
    if all_passed:
        return JsonResponse({
            'status': 'ready',
            'checks': checks
        })
    else:
        return JsonResponse({
            'status': 'not_ready',
            'checks': checks,
            'error': 'One or more dependency checks failed'
        }, status=503)
