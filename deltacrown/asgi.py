"""
ASGI config for deltacrown project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/

Phase 2: Real-Time Features & Security
- Supports both HTTP and WebSocket protocols
- Django Channels 3 integration for real-time match updates
- Module 2.5: Rate limiting and abuse protection
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing code that may import ORM models
django_asgi_app = get_asgi_application()

# Import WebSocket routing and middleware after Django setup
from apps.tournaments.realtime.routing import websocket_urlpatterns as tournament_ws_urls
from apps.organizations.realtime.routing import websocket_urlpatterns as team_ws_urls
from apps.tournaments.realtime.middleware import JWTAuthMiddleware
from apps.tournaments.realtime.middleware_ratelimit import RateLimitMiddleware
from django.conf import settings

# Build WebSocket middleware stack
# Base stack: Origin validation -> session auth -> JWT override -> URL routing.
# AuthMiddlewareStack must wrap JWT middleware so session user exists when no
# token is provided (Hub page uses session auth by default).
websocket_app = AllowedHostsOriginValidator(
    AuthMiddlewareStack(
        JWTAuthMiddleware(
            URLRouter(tournament_ws_urls + team_ws_urls)
        )
    )
)

# Conditionally wrap rate limiter (Module 2.5) only when enabled
# This allows test environments to work without Redis
if getattr(settings, "WS_RATE_ENABLED", False):
    websocket_app = RateLimitMiddleware(websocket_app)

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,
    
    # WebSocket handler for real-time tournament and team updates
    # Middleware chain (innermost to outermost):
    # 1. URLRouter: Routes to TournamentConsumer (Module 2.2) and TeamConsumer (Module 3.3)
    # 2. JWTAuthMiddleware: Validates JWT token and can override user when provided
    # 3. AuthMiddlewareStack: Session/cookie auth fallback for browser clients
    # 4. AllowedHostsOriginValidator: Validates host/origin
    # 5. RateLimitMiddleware (Module 2.5): Conditionally applied when WS_RATE_ENABLED=True
    "websocket": websocket_app,
})

