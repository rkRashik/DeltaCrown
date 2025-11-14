"""
Health check endpoints (Module 9.5).
Provides Kubernetes-compatible health checks.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def healthz(request):
    """
    Basic liveness check.
    Returns 200 if service is alive (no dependencies checked).
    """
    return JsonResponse({
        'status': 'ok',
        'service': 'deltacrown',
    })


def readyz(request):
    """
    Readiness check.
    Returns 200 only if all dependencies are healthy.
    """
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JsonResponse({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks,
    }, status=status_code)


def _check_database():
    """Check database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def _check_cache():
    """Check cache connection (Redis)."""
    try:
        cache.set('health_check', '1', timeout=10)
        result = cache.get('health_check')
        cache.delete('health_check')
        return result == '1'
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False
