"""
Test-Only ASGI Application for WebSocket Integration Tests

This module provides a test-specific ASGI application that uses TestJWTAuthMiddleware
instead of the production JWTAuthMiddleware to work around pytest-django's
transaction isolation limitations.

IMPORTANT: This is ONLY for tests. Production uses deltacrown/asgi.py.

**WHY AllowedHostsOriginValidator IS INTENTIONALLY OMITTED IN TESTS:**

AllowedHostsOriginValidator silently closes WebSocket connections with close code 1000
when the Origin header doesn't match ALLOWED_HOSTS. In test environments:
- WebsocketCommunicator doesn't send Origin headers by default
- Test settings use WS_ALLOWED_ORIGINS=[] (allow all)
- The validator was closing ALL test connections before any consumer code executed

This was discovered during Module 6.6 integration test unblocking (see 
MODULE_6.6_INTEGRATION_UNBLOCK.md for full root cause analysis).

**PRODUCTION ASGI (deltacrown/asgi.py) REMAINS UNCHANGED:**
- Full security middleware stack intact
- AllowedHostsOriginValidator enforces WS_ALLOWED_ORIGINS
- Rate limiting middleware active
- JWT authentication enforced

This test-only modification enables integration testing without compromising production
security. See tests/websocket_test_middleware.py for detailed explanation of why this
is necessary.
"""

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

# Import test middleware
from tests.websocket_test_middleware import TestJWTAuthMiddleware

# Import WebSocket routing
from apps.tournaments.realtime.routing import websocket_urlpatterns as tournament_ws_urls
from apps.teams.realtime.routing import websocket_urlpatterns as team_ws_urls

# Import echo consumer for wiring tests
from tests.test_echo_consumer import EchoConsumer

# Add echo route for testing ASGI wiring (no middleware, no auth)
echo_app = URLRouter([
    path("ws/test/echo/", EchoConsumer.as_asgi()),
])

# Build test WebSocket middleware stack
# Uses TestJWTAuthMiddleware instead of production JWTAuthMiddleware
# NOTE: AllowedHostsOriginValidator removed for tests - WS_ALLOWED_ORIGINS=[] in settings
websocket_app = TestJWTAuthMiddleware(
    URLRouter([
        path("ws/test/echo/", EchoConsumer.as_asgi()),
    ] + tournament_ws_urls + team_ws_urls)
)

# Test ASGI application (no rate limiting in tests)
test_application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": websocket_app,
})
