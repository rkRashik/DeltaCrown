"""Shared Redis URL handling; never log URLs containing credentials."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def verified_redis_url(url):
    if not url or urlsplit(url).scheme != "rediss":
        return url
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in {"ssl_cert_reqs", "ssl_check_hostname"}
    ]
    # Lowercase spelling works across redis-py, Kombu and Celery Redis backend.
    query.extend([("ssl_cert_reqs", "required"), ("ssl_check_hostname", "true")])
    return urlunsplit(parts._replace(query=urlencode(query)))


def redis_url_with_db(url, db):
    if not url:
        return url
    parts = urlsplit(url)
    hostname = (parts.hostname or "").lower()
    if hostname == "upstash.io" or hostname.endswith(".upstash.io"):
        db = 0
    return urlunsplit(parts._replace(path=f"/{db}"))
