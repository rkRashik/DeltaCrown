"""Answer GET/HEAD /healthz/ inside the ASGI event loop, before middleware, threads and the database (OL-10).

Render's 5 s health probe used to queue behind Django's sync middleware/view threads, so a burst of slow
media reads could make the probe time out and get the instance restarted. This is liveness only (the
process accepts and answers HTTP); it deliberately proves nothing about the database or media.
"""
_BODY = b'{"status": "ok"}'
_HEADERS = [(b"content-type", b"application/json"), (b"cache-control", b"no-store"),
            (b"content-length", str(len(_BODY)).encode())]


class FastHealth:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") == "/healthz/" and scope.get("method") in ("GET", "HEAD"):
            await send({"type": "http.response.start", "status": 200, "headers": _HEADERS})
            await send({"type": "http.response.body", "body": b"" if scope["method"] == "HEAD" else _BODY})
            return
        await self.application(scope, receive, send)
