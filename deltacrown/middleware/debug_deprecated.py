"""
TEMP MIDDLEWARE - REMOVE AFTER PHASE4_STEP4_2 FIX

Logs any response that might indicate deprecated/gone endpoints.
Used to capture runtime evidence of deprecated_endpoint issues.

USAGE: Enable in settings.py MIDDLEWARE list (DEBUG only)
"""
import json
import logging
from django.urls import resolve, Resolver404

logger = logging.getLogger(__name__)


class DeprecatedEndpointTracerMiddleware:
    """
    Middleware to trace any deprecated/gone/410 responses.
    
    Logs detailed info when:
    - Response status is 410 (Gone)
    - Response body contains deprecation keywords
    """
    
    KEYWORDS = ['deprecated', 'gone', 'legacy', 'deprecated_endpoint']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if response indicates deprecated endpoint
        should_log = False
        reason = ""
        
        # Check 1: 410 Gone status
        if response.status_code == 410:
            should_log = True
            reason = "410_GONE"
        
        # Check 2: JSON response with deprecation keywords
        content_type = response.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                # Get response body (handle both string and bytes)
                if hasattr(response, 'content'):
                    body = response.content
                    if isinstance(body, bytes):
                        body_str = body.decode('utf-8', errors='ignore')
                    else:
                        body_str = str(body)
                    
                    body_lower = body_str.lower()
                    
                    # Check for deprecation keywords
                    for keyword in self.KEYWORDS:
                        if keyword in body_lower:
                            should_log = True
                            reason = f"JSON_CONTAINS_{keyword.upper()}"
                            break
            except Exception:
                pass  # If we can't decode, skip
        
        # Log if deprecated response detected
        if should_log:
            # Resolve view function
            view_info = "UNKNOWN"
            try:
                resolved = resolve(request.path_info)
                view_func = resolved.func
                view_name = resolved.view_name
                view_info = f"{view_func.__module__}.{view_func.__name__} (name={view_name})"
            except Resolver404:
                view_info = "NO_MATCH_404"
            except Exception as e:
                view_info = f"RESOLVE_ERROR: {e}"
            
            # Get body snippet
            body_snippet = ""
            if hasattr(response, 'content'):
                try:
                    body = response.content
                    if isinstance(body, bytes):
                        body_str = body.decode('utf-8', errors='ignore')
                    else:
                        body_str = str(body)
                    body_snippet = body_str[:200]
                except Exception:
                    body_snippet = "ERROR_READING_BODY"
            
            # Log with clear marker
            log_msg = (
                f"[DEPRECATED_TRACE] "
                f"path={request.path} "
                f"method={request.method} "
                f"status={response.status_code} "
                f"reason={reason} "
                f"view={view_info} "
                f"body_snippet={body_snippet}"
            )
            
            logger.warning(log_msg)
            print("\n" + "="*80)
            print(log_msg)
            print("="*80 + "\n")
        
        return response
