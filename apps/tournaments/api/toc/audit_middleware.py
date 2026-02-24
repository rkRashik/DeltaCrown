"""
TOC Sprint 11 — Audit middleware for TOC write operations.
Injects audit logging into all POST/PUT/PATCH/DELETE requests
hitting TOC API endpoints.
"""

import json
import logging

logger = logging.getLogger(__name__)


class TOCAuditMiddleware:
    """
    Middleware that intercepts write operations on TOC API endpoints
    and creates audit log entries automatically.

    Attach after authentication middleware so request.user is available.
    """

    TOC_PREFIX = "/api/toc/"

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only intercept TOC API write operations
        is_toc = request.path.startswith(self.TOC_PREFIX)
        is_write = request.method in self.WRITE_METHODS

        response = self.get_response(request)

        if is_toc and is_write and response.status_code < 400:
            self._log_action(request, response)

        return response

    def _log_action(self, request, response):
        try:
            from apps.tournaments.api.toc.audit_service import TOCAuditService

            # Extract slug from URL: /api/toc/<slug>/...
            parts = request.path.strip("/").split("/")
            if len(parts) < 3:
                return
            slug = parts[2]  # api / toc / <slug> / ...
            endpoint = "/".join(parts[3:]) if len(parts) > 3 else ""

            # Resolve tournament
            from apps.tournaments.models import Tournament
            try:
                tournament = Tournament.objects.get(slug=slug)
            except Tournament.DoesNotExist:
                return

            action = f"{request.method} /{endpoint}"
            user = request.user if request.user and request.user.is_authenticated else None

            # Build detail
            detail = {"tab": self._infer_tab(endpoint), "endpoint": endpoint}

            # Build diff (body snapshot for POST/PUT)
            diff = None
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = json.loads(request.body) if request.body else {}
                    # Redact sensitive fields
                    redacted = {k: v for k, v in body.items() if k not in ("password", "token", "secret")}
                    diff = redacted
                except (json.JSONDecodeError, Exception):
                    pass

            TOCAuditService.log_action(tournament, user, action, detail=detail, diff=diff)

            # Also dispatch real-time event
            TOCAuditService.dispatch_event(slug, "audit", {
                "action": action,
                "user": getattr(user, "username", "system"),
                "tab": detail.get("tab", ""),
            })

        except Exception as e:
            logger.debug("TOC audit middleware error: %s", e)

    @staticmethod
    def _infer_tab(endpoint):
        """Infer which tab an endpoint belongs to based on the URL prefix."""
        tab_map = {
            "overview": "overview",
            "lifecycle": "overview",
            "alerts": "overview",
            "participants": "participants",
            "payments": "payments",
            "brackets": "brackets",
            "schedule": "schedule",
            "matches": "matches",
            "disputes": "disputes",
            "settings": "settings",
            "announcements": "announcements",
            "stats": "overview",
            "certificates": "settings",
            "trophies": "participants",
            "trust": "participants",
            "staff": "settings",
            "roles": "settings",
            "permissions": "settings",
            "economy": "payments",
            "audit-log": "settings",
        }
        prefix = endpoint.split("/")[0] if endpoint else ""
        return tab_map.get(prefix, "unknown")
