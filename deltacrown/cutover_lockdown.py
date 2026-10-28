"""Fail-closed single-service cutover guard for the production Daphne ASGI app.

No HTTP application/media routes or WebSockets are reachable while the operator
explicitly sets OWNLOBBY_CUTOVER_LOCKDOWN=1, OR the hybrid release still has an
unverified storage/recovery/legacy privacy condition. This guard is applied
outside Django and Channels routing, before authentication or media I/O.

The only route permitted during lockdown is GET/HEAD /healthz/, which serves
as a startup liveness endpoint, NOT evidence that media privacy is verified.
CDN URLs hosted outside OwnLobby are NOT protected by this middleware.
"""
from __future__ import annotations

import os


def lockdown_required(settings):
    """Fail closed even if the explicit lockdown flag is accidentally cleared."""
    if os.getenv("OWNLOBBY_CUTOVER_LOCKDOWN", "0") == "1":
        return True
    return (
        getattr(settings, "OWNLOBBY_MEDIA_MODE", "legacy") == "hybrid"
        and not all((
            getattr(settings, "MEDIA_STORAGE_VERIFIED", False),
            getattr(settings, "MEDIA_RESTORE_VERIFIED", False),
            getattr(settings, "MEDIA_LEGACY_PRIVACY_VERIFIED", False),
        ))
    )


class CutoverLockdown:
    """Keep the app unavailable until *all* truthfully verified conditions pass."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        kind = scope.get("type")
        if kind == "http":
            if (
                scope.get("path") == "/healthz/"
                and scope.get("method") in {"GET", "HEAD"}
            ):
                await self.application(scope, receive, send)
                return
            body = b"OwnLobby is undergoing secure release maintenance.\n"
            headers = [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"cache-control", b"no-store"),
                (b"retry-after", b"60"),
                (b"x-robots-tag", b"noindex, noarchive"),
                (b"referrer-policy", b"no-referrer"),
            ]
            await send({"type": "http.response.start", "status": 503,
                        "headers": headers})
            await send({"type": "http.response.body",
                        "body": b"" if scope.get("method") == "HEAD" else body})
            return
        if kind == "websocket":
            await send({"type": "websocket.close", "code": 4403})
            return
        await self.application(scope, receive, send)
