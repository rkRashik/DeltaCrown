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
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing code that may import ORM models
django_asgi_app = get_asgi_application()

# Import WebSocket routing and middleware after Django setup
from apps.tournaments.realtime.routing import websocket_urlpatterns as tournament_ws_urls
from apps.teams.realtime.routing import websocket_urlpatterns as team_ws_urls
from apps.tournaments.realtime.middleware import JWTAuthMiddleware
from apps.tournaments.realtime.middleware_ratelimit import RateLimitMiddleware

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,
    
    # WebSocket handler for real-time tournament and team updates
    # Middleware chain (innermost to outermost):
    # 1. URLRouter: Routes to TournamentConsumer (Module 2.2) and TeamConsumer (Module 3.3)
    # 2. AllowedHostsOriginValidator: Validates host header
    # 3. RateLimitMiddleware (Module 2.5): Enforces connection/message rate limits
    # 4. JWTAuthMiddleware: Validates JWT token and injects user
    "websocket": JWTAuthMiddleware(
        RateLimitMiddleware(
            AllowedHostsOriginValidator(
                URLRouter(tournament_ws_urls + team_ws_urls)
            )
        )
    ),
})

