from apps.common.seo import should_noindex_path
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from urllib.parse import urlsplit


class SearchIndexingMiddleware:
    """Crawler hints complement authentication; they never grant access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code >= 400 or should_noindex_path(request.path, request.META.get("QUERY_STRING", "")):
            response["X-Robots-Tag"] = "noindex, nofollow"
        # Only approved public HTML pages participate. API/POST/callback/WS,
        # signed-in sessions, private pages, errors and asset requests stay put.
        public_path = request.path in {"/", "/about/", "/faq/", "/rules/", "/contact/", "/terms/", "/privacy/", "/cookies/", "/moderation/"} or request.path.startswith(("/tournaments/", "/teams/", "/orgs/", "/@", "/competition/leaderboards/", "/community/"))
        origin = urlsplit(settings.SITE_URL)
        host = request.get_host().split(":")[0].lower() if getattr(settings, "PUBLIC_DOMAIN_REDIRECTS_ENABLED", False) else ""
        public_response = public_path and not response.get("X-Robots-Tag") and b'content="noindex' not in getattr(response, 'content', b'')[:50000]
        # Direct new-www login/reset entry pages must move before users submit a
        # form or initiate provider state. Existing-domain auth and callbacks stay.
        www_auth_entry = host == "www.ownlobby.com" and request.path in {"/account/login/", "/account/signup/", "/account/password_reset/"}
        if (getattr(settings, "PUBLIC_DOMAIN_REDIRECTS_ENABLED", False)
                and origin.scheme == "https" and origin.hostname == settings.BRAND["domain"]
                and host in {"deltacrown.xyz", "www.deltacrown.xyz", "www.ownlobby.com"}
                and request.method in {"GET", "HEAD"} and response.status_code == 200
                and response.get("Content-Type", "").startswith("text/html")
                and not getattr(getattr(request, "user", None), "is_authenticated", False)
                and (public_response or www_auth_entry)):
            return HttpResponsePermanentRedirect(settings.SITE_URL + request.get_full_path())
        return response
