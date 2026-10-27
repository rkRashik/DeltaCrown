"""Low-overhead opt-in RSS attribution for Render memory incidents.

Does not log raw paths, query strings, user identifiers, headers or response bodies.
Sampling is per process; a sample cannot identify every source of growth.
"""
import logging
import os
import time

logger = logging.getLogger("deltacrown.memory")

def _rss_bytes():
    try:
        with open("/proc/self/statm", "r", encoding="ascii") as f:
            pages = int(f.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError, AttributeError):
        return None


class RequestMemoryProbeMiddleware:
    """Observe RSS after each Nth request, without retaining request objects."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = os.getenv("ENABLE_REQUEST_MEMORY_PROBE", "0") == "1"
        try:
            self.every = max(1, int(os.getenv("REQUEST_MEMORY_SAMPLE_EVERY", "50")))
        except ValueError:
            self.every = 50
        self.count = 0

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        self.count += 1
        sample = self.count % self.every == 0
        before = _rss_bytes() if sample else None
        started = time.monotonic() if sample else None
        try:
            return self.get_response(request)
        finally:
            if sample:
                after = _rss_bytes()
                if after is not None and before is not None:
                    # Route name is a code-defined identifier, not a raw URL.
                    match = getattr(request, "resolver_match", None)
                    route = getattr(match, "view_name", None) or "unresolved"
                    logger.info(
                        "request_mem route=%s rss_mib=%.1f delta_mib=%.1f elapsed_ms=%d",
                        route, after / 1048576, (after - before) / 1048576,
                        int((time.monotonic() - started) * 1000),
                    )
