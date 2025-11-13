"""
WebSocket Authentication Middleware

Provides JWT-based authentication for WebSocket connections.
Extracts JWT token from query parameters and validates against user model.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates
Module 2.4: Security Hardening (JWT expiry handling)
Module 2.6: Realtime Monitoring & Logging Enhancement

Features:
    - JWT token validation from query parameters
    - Graceful handling of expired tokens (close code 4002)
    - Graceful handling of invalid tokens (close code 4003)
    - Configurable leeway for clock skew (JWT_LEEWAY_SECONDS)

Usage:
    # In asgi.py
    from apps.tournaments.realtime.middleware import JWTAuthMiddleware
    
    application = ProtocolTypeRouter({
        "websocket": JWTAuthMiddleware(
            AllowedHostsOriginValidator(
                URLRouter(websocket_urlpatterns)
            )
        ),
    })
    
Close Codes:
    - 4002: JWT token expired (client should refresh and reconnect)
    - 4003: JWT token invalid/forbidden (authentication failed)
"""

import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt

# Module 2.6: Realtime Monitoring & Logging Enhancement
from . import logging as ws_logging
from . import metrics

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_key: str):
    """
    Validate JWT token and return associated user with error details.
    
    Args:
        token_key: JWT access token string
        
    Returns:
        Tuple of (User instance or AnonymousUser, error_code or None, error_message or None)
        - (User, None, None) on success
        - (AnonymousUser, 4002, message) on expired token
        - (AnonymousUser, 4003, message) on invalid/forbidden token
        
    Implementation:
        - Validates token signature and expiration
        - Applies JWT_LEEWAY_SECONDS for clock skew tolerance
        - Extracts user_id from token claims
        - Queries database for user
        - Returns AnonymousUser with error details on any failure
    """
    try:
        # Get leeway setting (default 60 seconds for clock skew)
        leeway = getattr(settings, 'JWT_LEEWAY_SECONDS', 60)
        
        # Validate and decode JWT token with leeway
        access_token = AccessToken(token_key)
        
        # Apply custom leeway if configured
        if leeway > 0:
            # Manually decode with leeway to handle clock skew
            # The simplejwt library uses the SECRET_KEY from settings
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
                
                # Module 2.6: Log auth failure (no user_id available)
                ws_logging.log_auth_failure(
                    reason_code=ws_logging.ReasonCode.JWT_EXPIRED,
                    user_id=None
                )
                
                # Module 2.6: Record auth failure metric
                metrics.record_auth_failure(
                    reason=metrics.ReasonCode.JWT_EXPIRED,
                    user_id=None
                )
                
                return (AnonymousUser(), 4002, "JWT token expired. Please refresh your token.")
            except jwt.InvalidTokenError as e:
                logger.warning(f"JWT token invalid: {str(e)}")
                
                # Module 2.6: Log auth failure
                ws_logging.log_auth_failure(
                    reason_code=ws_logging.ReasonCode.JWT_INVALID,
                    user_id=None
                )
                
                # Module 2.6: Record auth failure metric
                metrics.record_auth_failure(
                    reason=metrics.ReasonCode.JWT_INVALID,
                    user_id=None
                )
                
                return (AnonymousUser(), 4003, f"Invalid JWT token: {str(e)}")
        else:
            user_id = access_token.get('user_id')
        
        if not user_id:
            logger.warning("JWT token missing user_id claim")
            
            # Module 2.6: Log auth failure
            ws_logging.log_auth_failure(
                reason_code=ws_logging.ReasonCode.JWT_INVALID,
                user_id=None
            )
            
            # Module 2.6: Record auth failure metric
            metrics.record_auth_failure(
                reason=metrics.ReasonCode.JWT_INVALID,
                user_id=None
            )
            
            return (AnonymousUser(), 4003, "JWT token missing user_id claim")
        
        # Import here to avoid circular dependency
        from apps.accounts.models import User
        
        try:
            user = User.objects.get(id=user_id)
            logger.debug(f"WebSocket authenticated user: {user.username} (ID: {user_id})")
            return (user, None, None)
        except User.DoesNotExist:
            logger.warning(f"User ID {user_id} from JWT not found in database")
            
            # Module 2.6: Log auth failure
            ws_logging.log_auth_failure(
                reason_code=ws_logging.ReasonCode.JWT_INVALID,
                user_id=user_id
            )
            
            # Module 2.6: Record auth failure metric
            metrics.record_auth_failure(
                reason=metrics.ReasonCode.JWT_INVALID,
                user_id=user_id
            )
            
            return (AnonymousUser(), 4003, f"User ID {user_id} not found")
            
    except InvalidToken:
        logger.warning("Invalid JWT token provided for WebSocket connection")
        
        # Module 2.6: Log auth failure
        ws_logging.log_auth_failure(
            reason_code=ws_logging.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        # Module 2.6: Record auth failure metric
        metrics.record_auth_failure(
            reason=metrics.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        return (AnonymousUser(), 4003, "Invalid JWT token")
    except TokenError as e:
        logger.warning(f"JWT token error: {str(e)}")
        # Check if it's an expiration error
        if 'exp' in str(e).lower() or 'expired' in str(e).lower():
            # Module 2.6: Log auth failure (expired)
            ws_logging.log_auth_failure(
                reason_code=ws_logging.ReasonCode.JWT_EXPIRED,
                user_id=None
            )
            
            # Module 2.6: Record auth failure metric
            metrics.record_auth_failure(
                reason=metrics.ReasonCode.JWT_EXPIRED,
                user_id=None
            )
            
            return (AnonymousUser(), 4002, f"JWT token expired: {str(e)}")
        
        # Module 2.6: Log auth failure (invalid)
        ws_logging.log_auth_failure(
            reason_code=ws_logging.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        # Module 2.6: Record auth failure metric
        metrics.record_auth_failure(
            reason=metrics.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        return (AnonymousUser(), 4003, f"JWT token error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error validating WebSocket JWT: {str(e)}", exc_info=True)
        
        # Module 2.6: Log auth failure (generic)
        ws_logging.log_auth_failure(
            reason_code=ws_logging.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        # Module 2.6: Record auth failure metric
        metrics.record_auth_failure(
            reason=metrics.ReasonCode.JWT_INVALID,
            user_id=None
        )
        
        return (AnonymousUser(), 4003, "Authentication failed")


class JWTAuthMiddleware:
    """
    Middleware to authenticate WebSocket connections via JWT tokens.
    
    Token is extracted from query string parameter 'token':
        ws://domain/ws/tournament/123/?token=<jwt_access_token>
    
    Attributes:
        app: The ASGI application to wrap
        
    Methods:
        __call__: Process WebSocket connection and inject user into scope
        
    Example:
        # Client-side connection
        const token = localStorage.getItem('access_token');
        const ws = new WebSocket(`ws://localhost:8000/ws/tournament/1/?token=${token}`);
        
        # Server-side validation
        # User is available in scope['user'] for all downstream consumers
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
            
        Close Codes:
            - 4002: JWT token expired (client should refresh)
            - 4003: JWT token invalid (authentication failed)
        """
        # Only process WebSocket connections
        if scope['type'] != 'websocket':
            return await self.app(scope, receive, send)
        
        # Extract token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            # Validate token and get user with error details
            user, error_code, error_message = await get_user_from_token(token)
            scope['user'] = user
            
            # If authentication failed, send error and close connection
            if error_code:
                await self._send_auth_error_and_close(send, error_code, error_message)
                return
        else:
            logger.warning("WebSocket connection attempted without token parameter")
            scope['user'] = AnonymousUser()
            await self._send_auth_error_and_close(send, 4003, "Missing JWT token")
            return
        
        return await self.app(scope, receive, send)
    
    async def _send_auth_error_and_close(self, send, close_code: int, message: str):
        """
        Send error message and close WebSocket connection.
        
        Args:
            send: ASGI send callable
            close_code: WebSocket close code (4002 for expired, 4003 for invalid)
            message: Error message to send
            
        Implementation:
            1. Accept the WebSocket connection
            2. Send error message as JSON
            3. Close connection with appropriate code
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
