"""
Content Security Policy (CSP) middleware.

Adds a Content-Security-Policy header to every response.
"""


class CSPMiddleware:
    """Set Content-Security-Policy header on all responses."""

    # Trusted CDN domains used in base templates
    CDN_SOURCES = (
        "https://cdn.tailwindcss.com",
        "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com",
        "https://unpkg.com",
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
        self.csp_header = self._build_policy()

    def __call__(self, request):
        response = self.get_response(request)
        # Don't override if already set (e.g. by a view)
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = self.csp_header
        return response

    def _build_policy(self):
        cdn = " ".join(self.CDN_SOURCES)
        fonts = " ".join(self.FONT_SOURCES)
        analytics = " ".join(self.ANALYTICS_SOURCES)

        directives = [
            "default-src 'self'",
            f"script-src 'self' 'unsafe-inline' {cdn} {analytics}",
            f"style-src 'self' 'unsafe-inline' {cdn} {fonts}",
            f"font-src 'self' {fonts} {cdn}",
            f"img-src 'self' data: blob: https:",
            f"connect-src 'self' {analytics}",
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        return "; ".join(directives)
