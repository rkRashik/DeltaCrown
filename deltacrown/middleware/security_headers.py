"""
Content Security Policy (CSP) middleware.

Generates a per-request nonce for inline ``<script>`` tags, replacing
``'unsafe-inline'`` in the ``script-src`` directive.

Usage in templates::

    <script nonce="{{ request.csp_nonce }}">…</script>
"""

import secrets


class CSPMiddleware:
    """Set Content-Security-Policy header on all responses."""

    # Trusted CDN domains used in base templates
    CDN_SOURCES = (
        "https://cdn.tailwindcss.com",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "https://unpkg.com",
        "https://code.jquery.com",
    )
    FONT_SOURCES = (
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
    )
    ANALYTICS_SOURCES = (
        "https://www.googletagmanager.com",
        "https://www.google-analytics.com",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a unique nonce per request
        nonce = secrets.token_urlsafe(32)
        request.csp_nonce = nonce

        response = self.get_response(request)
        # Don't override if already set (e.g. by a view)
        if "Content-Security-Policy" not in response:
            # Admin requires 'unsafe-eval' for Unfold's Alpine.js expression evaluator
            is_admin = request.path.startswith("/admin/")
            response["Content-Security-Policy"] = self._build_policy(
                nonce, unsafe_eval=is_admin
            )
        return response

    def _build_policy(self, nonce: str, *, unsafe_eval: bool = False) -> str:
        cdn = " ".join(self.CDN_SOURCES)
        fonts = " ".join(self.FONT_SOURCES)
        analytics = " ".join(self.ANALYTICS_SOURCES)

        eval_token = " 'unsafe-eval'" if unsafe_eval else ""
        directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' {cdn} {analytics}{eval_token}",
            # style-src keeps unsafe-inline — Tailwind CDN injects inline styles
            f"style-src 'self' 'unsafe-inline' {cdn} {fonts}",
            f"font-src 'self' {fonts} {cdn}",
            f"img-src 'self' data: blob: https:",
            "media-src 'self' data: blob:",
            f"connect-src 'self' {analytics} {cdn} ws: wss:",
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        return "; ".join(directives)
