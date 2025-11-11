"""
Test-Only WebSocket Authentication Middleware

TIER 2 SOLUTION for pytest-django + Channels DB visibility issue.

This middleware is ONLY used in tests to work around the fundamental limitation
that pytest-django's transaction-wrapped fixtures are not visible to ASGI
WebSocket connections running in separate database connections.

WHAT IT DOES:
- Validates JWT token signature/claims (same as production)
- Resolves user from an in-memory test registry (NOT database)
- Role/membership checks still hit the real database (with transaction=True visibility)

WHAT IT DOESN'T DO:
- Does NOT bypass authentication (JWT still validated)
- Does NOT bypass authorization (roles/permissions still checked)
- Does NOT affect production code (test-only import)

WHY THIS IS NECESSARY:
pytest-django wraps tests in database transactions that are NOT committed until
test completion. ASGI WebSocket connections run in separate DB connections and
cannot see uncommitted test data. This is a documented limitation of testing
Django Channels with pytest.

ALTERNATIVES TRIED (all failed):
1. Standard fixtures with `db` marker → middleware can't see users
2. `transactional_db` fixture → breaks test isolation
3. `@pytest.mark.django_db(transaction=True)` → ALL tests fail
4. Async helpers with `database_sync_to_async` → same transaction isolation issue

SEE: https://channels.readthedocs.io/en/stable/topics/testing.html#integration-testing
"""

import logging
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt

logger = logging.getLogger(__name__)

# In-memory test user registry (populated by tests before connecting)
_test_user_registry = {}


def seed_test_user(user):
    """
    Seed a user into the test registry for WebSocket authentication.
    
    Args:
        user: User instance to seed
        
    Returns:
        The seeded user
        
    Usage:
        test_user = User.objects.create_superuser(...)
        seed_test_user(test_user)  # Now middleware can find this user
    """
    _test_user_registry[user.id] = user
    logger.debug(f"Seeded test user {user.id} into registry")
    return user


def clear_test_users():
    """Clear the test user registry (call in teardown/cleanup)."""
    _test_user_registry.clear()


class TestJWTAuthMiddleware:
    """
    Test-only middleware that validates JWT but bypasses DB user lookup.
    
    CRITICAL: This still validates JWT tokens with the same secret/algorithm
    as production. It only bypasses the DB lookup to work around pytest-django
    transaction isolation.
    
    For production, use JWTAuthMiddleware from apps.tournaments.realtime.middleware.
    """
    
    def __init__(self, app):
        """
        Initialize middleware with ASGI application.
        
        Args:
            app: The ASGI application to wrap (typically URLRouter)
        """
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """
        Process WebSocket connection and authenticate user.
        
        Args:
            scope: ASGI connection scope dict
            receive: ASGI receive callable
            send: ASGI send callable
            
        Returns:
            Result of calling wrapped application
            
        Side Effects:
            - Adds 'user' key to scope dict
            - Logs authentication attempts and failures
            - Sends error message and closes connection on invalid/expired JWT
        """
        # Only process WebSocket connections
        if scope['type'] != 'websocket':
            return await self.app(scope, receive, send)
        
        # Extract token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            # Validate token and get user (from test registry, not DB)
            user, error_code, error_message = await self._get_user_from_token(token)
            scope['user'] = user
            
            # If authentication failed, send error and close connection
            if error_code:
                await self._send_auth_error_and_close(send, error_code, error_message)
                return
        else:
            # No token provided - set AnonymousUser and let consumer decide
            # (Some routes like /ws/test/echo/ may not require auth)
            logger.warning("WebSocket connection attempted without token parameter")
            scope['user'] = AnonymousUser()
            # Don't close here - let the consumer handle auth requirements
        
        return await self.app(scope, receive, send)
    
    async def _get_user_from_token(self, token_key: str):
        """
        Validate JWT token and return user from test registry.
        
        Args:
            token_key: JWT access token string
            
        Returns:
            Tuple of (User instance or AnonymousUser, error_code or None, error_message or None)
            
        Implementation:
            - Validates token signature and expiration (SAME AS PRODUCTION)
            - Extracts user_id from token claims
            - Looks up user in test registry (DIFFERENT FROM PRODUCTION)
            - Returns AnonymousUser with error details on any failure
        """
        try:
            # Get leeway setting (default 60 seconds for clock skew)
            leeway = getattr(settings, 'JWT_LEEWAY_SECONDS', 60)
            
            # Validate and decode JWT token with leeway (SAME AS PRODUCTION)
            from rest_framework_simplejwt.settings import api_settings
            
            try:
                decoded = jwt.decode(
                    token_key,
                    api_settings.SIGNING_KEY,
                    algorithms=[api_settings.ALGORITHM],
                    options={'verify_exp': True},
                    leeway=leeway
                )
                user_id = decoded.get('user_id')
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token expired (beyond leeway)")
                return (AnonymousUser(), 4002, "JWT token expired. Please refresh your token.")
            except jwt.InvalidTokenError as e:
                logger.warning(f"JWT token invalid: {str(e)}")
                return (AnonymousUser(), 4003, f"Invalid JWT token: {str(e)}")
            
            if not user_id:
                logger.warning("JWT token missing user_id claim")
                return (AnonymousUser(), 4003, "JWT token missing user_id claim")
            
            # Look up user in test registry (DIFFERENT FROM PRODUCTION)
            # JWT stores user_id as string, but User.id is int
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id in JWT: {user_id}")
                return (AnonymousUser(), 4003, "Invalid user_id in JWT token")
            
            user = _test_user_registry.get(user_id_int)
            if user:
                logger.debug(f"WebSocket authenticated test user: {user.username} (ID: {user_id_int})")
                return (user, None, None)
            else:
                logger.warning(f"User ID {user_id_int} not found in test registry (did you call seed_test_user?)")
                return (AnonymousUser(), 4003, f"User ID {user_id_int} not found in test registry")
                
        except InvalidToken:
            logger.warning("Invalid JWT token provided for WebSocket connection")
            return (AnonymousUser(), 4003, "Invalid JWT token")
        except TokenError as e:
            logger.warning(f"JWT token error: {str(e)}")
            if 'exp' in str(e).lower() or 'expired' in str(e).lower():
                return (AnonymousUser(), 4002, f"JWT token expired: {str(e)}")
            return (AnonymousUser(), 4003, f"JWT token error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error validating WebSocket JWT: {str(e)}", exc_info=True)
            return (AnonymousUser(), 4003, "Authentication failed")
    
    async def _send_auth_error_and_close(self, send, close_code: int, message: str):
        """
        Send error message and close WebSocket connection.
        
        Args:
            send: ASGI send callable
            close_code: WebSocket close code (4002 for expired, 4003 for invalid)
            message: Error message to send
        """
        import json
        
        # Accept the connection first
        await send({
            'type': 'websocket.accept'
        })
        
        # Send error message
        await send({
            'type': 'websocket.send',
            'text': json.dumps({
                'type': 'error',
                'code': 'authentication_failed',
                'message': message,
                'close_code': close_code
            })
        })
        
        # Close connection with appropriate code
        await send({
            'type': 'websocket.close',
            'code': close_code
        })
        
        logger.info(f"WebSocket connection closed: {close_code} - {message}")
