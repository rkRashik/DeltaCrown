"""
Test-only WebSocket Authentication Middleware

Bypasses JWT validation and directly injects a user from query parameter.
This solves the transaction visibility issue in Django + Channels tests where
users created in test fixtures are not visible to the middleware's database queries.

Usage in tests:
    from tests.test_auth_middleware import create_test_websocket_app
    
    test_app = create_test_websocket_app()
    communicator = WebsocketCommunicator(
        test_app,
        f"/ws/match/1/?user_id={user.id}"
    )
"""

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

User = get_user_model()


class TestAuthMiddleware(BaseMiddleware):
    """
    Test-only WebSocket auth middleware.
    
    Reads user_id from query parameter and injects user into scope.
    Optionally accepts ?role=organizer to inject organizer privileges.
    Bypasses JWT validation to avoid transaction visibility issues in tests.
    """
    
    async def __call__(self, scope, receive, send):
        # Only process websocket connections
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)
        
        # Extract user_id and role from query string
        query_string = scope.get('query_string', b'').decode('utf-8')
        user_id = None
        test_role = None
        
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                if key == 'user_id':
                    try:
                        user_id = int(value)
                    except ValueError:
                        pass
                elif key == 'role':
                    test_role = value
        
        # Fetch user from database (async-safe)
        if user_id:
            user = await self._get_user(user_id)
            if user:
                # Inject test role if specified (for organizer tests)
                if test_role:
                    user._test_role = test_role
                scope['user'] = user
            else:
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def _get_user(self, user_id):
        """Fetch user from database (async-safe)."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def create_test_websocket_app():
    """
    Create a test-only WebSocket application with TestAuthMiddleware.
    
    Returns:
        ProtocolTypeRouter configured for tests with test auth middleware
        
    Example:
        test_app = create_test_websocket_app()
        communicator = WebsocketCommunicator(
            test_app,
            f"/ws/tournament/1/?user_id={user.id}"
        )
        
        # For organizer tests:
        communicator = WebsocketCommunicator(
            test_app,
            f"/ws/match/1/?user_id={user.id}&role=organizer"
        )
    """
    from apps.tournaments.realtime import routing
    
    # Note: Removed AllowedHostsOriginValidator for tests to avoid host validation issues
    return ProtocolTypeRouter({
        "websocket": TestAuthMiddleware(
            URLRouter(routing.websocket_urlpatterns)
        )
    })


def get_test_user_role(user):
    """
    Test-aware wrapper for get_user_tournament_role.
    
    Checks for _test_role attribute injected by TestAuthMiddleware before
    falling back to the real role resolution logic.
    
    This allows tests to specify roles via query parameter (?role=organizer)
    without dealing with transaction visibility issues in role lookups.
    """
    from apps.tournaments.security.permissions import get_user_tournament_role, TournamentRole
    
    # Check for test role override
    if hasattr(user, '_test_role'):
        role_map = {
            'organizer': TournamentRole.ORGANIZER,
            'admin': TournamentRole.ADMIN,
            'player': TournamentRole.PLAYER,
            'spectator': TournamentRole.SPECTATOR,
        }
        return role_map.get(user._test_role, TournamentRole.SPECTATOR)
    
    # Fall back to real role resolution
    return get_user_tournament_role(user)
