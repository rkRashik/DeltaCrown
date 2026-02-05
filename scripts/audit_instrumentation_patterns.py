"""
Audit Instrumentation - Add Response Headers to Team API Endpoints

This script adds truth headers to validation/creation endpoints:
- X-TeamsVNext-Sig: API version signature
- X-TeamsVNext-Endpoint: Endpoint identifier  
- X-TeamsVNext-TraceId: Unique request correlation ID

Usage: Apply these changes manually to apps/organizations/api/views/__init__.py
"""

TRUTH_HEADERS = {
    'X-TeamsVNext-Sig': 'api-2026-02-05-A',
    'X-TeamsVNext-TraceId': lambda: str(__import__('uuid').uuid4())[:8]
}

# ==============================================================================
# VALIDATE_TEAM_NAME INSTRUMENTATION
# ==============================================================================

# Location: apps/organizations/api/views/__init__.py, line ~427 (final return)
# OLD:
"""
        return Response({
            'ok': True,
            'available': True
        })
"""

# NEW:
"""
        import uuid
        return Response({
            'ok': True,
            'available': True
        }, headers={
            'X-TeamsVNext-Sig': 'api-2026-02-05-A',
            'X-TeamsVNext-Endpoint': 'validate-name',
            'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
        })
"""

# ==============================================================================
# VALIDATE_TEAM_TAG INSTRUMENTATION
# ==============================================================================

# Location: apps/organizations/api/views/__init__.py, line ~575 (final return)
# OLD:
"""
        return Response({
            'ok': True,
            'available': True
        })
"""

# NEW:
"""
        import uuid
        return Response({
            'ok': True,
            'available': True
        }, headers={
            'X-TeamsVNext-Sig': 'api-2026-02-05-A',
            'X-TeamsVNext-Endpoint': 'validate-tag',
            'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
        })
"""

# ==============================================================================
# CHECK_TEAM_OWNERSHIP INSTRUMENTATION
# ==============================================================================

# Location: apps/organizations/api/views/__init__.py, line ~675 (both returns)
# OLD:
"""
        return Response({
            'ok': True,
            'has_team': False
        })
"""

# NEW:
"""
        import uuid
        return Response({
            'ok': True,
            'has_team': False
        }, headers={
            'X-TeamsVNext-Sig': 'api-2026-02-05-A',
            'X-TeamsVNext-Endpoint': 'ownership-check',
            'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
        })
"""

# ==============================================================================
# CREATE_TEAM INSTRUMENTATION
# ==============================================================================

# Location: apps/organizations/api/views/__init__.py, line ~1050 (success return)
# OLD:
"""
        return Response({
            'ok': True,
            'team_id': team.id,
            'team_slug': team.slug,
            'team_url': team_url
        }, status=status.HTTP_201_CREATED)
"""

# NEW:
"""
        import uuid
        return Response({
            'ok': True,
            'team_id': team.id,
            'team_slug': team.slug,
            'team_url': team_url
        }, status=status.HTTP_201_CREATED, headers={
            'X-TeamsVNext-Sig': 'api-2026-02-05-A',
            'X-TeamsVNext-Endpoint': 'team-create',
            'X-TeamsVNext-TraceId': str(uuid.uuid4())[:8]
        })
"""

# ==============================================================================
# ADD UUID IMPORT AT TOP OF FILE
# ==============================================================================

# Location: apps/organizations/api/views/__init__.py, line ~5 (after other imports)
# ADD:
"""
import uuid
"""

print("""
Audit instrumentation patterns defined.

MANUAL APPLICATION REQUIRED:
1. Add 'import uuid' near top of apps/organizations/api/views/__init__.py
2. Add headers={...} parameter to ALL Response() calls in:
   - validate_team_name (2 locations)
   - validate_team_tag (2 locations)
   - check_team_ownership (2 locations)
   - create_team (1 location for success)

VERIFICATION:
After applying, test with:
  curl -H "Authorization: Bearer <token>" http://localhost:8000/api/vnext/teams/validate-name/?name=test&game_slug=apex-legends -v

Look for response headers:
  X-TeamsVNext-Sig: api-2026-02-05-A
  X-TeamsVNext-Endpoint: validate-name
  X-TeamsVNext-TraceId: <8-char-uuid>
""")
