"""
TOC API — Lightweight performance telemetry endpoints.

Provides per-tournament rolling request counters gathered by TOCBaseView.
"""

import time

from django.core.cache import cache
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView


class PerformanceSummaryView(TOCBaseView):
    """GET /api/toc/<slug>/perf/summary/ — Rolling request telemetry."""

    def get(self, request, slug):
        try:
            minutes = int(request.query_params.get('minutes', 10))
        except (TypeError, ValueError):
            minutes = 10
        minutes = max(1, min(minutes, 60))

        now_bucket = int(time.time() // 60)
        rows = []

        total_requests = 0
        total_slow = 0
        total_errors = 0

        for offset in range(minutes - 1, -1, -1):
            bucket = now_bucket - offset
            prefix = f"toc:perf:{self.tournament.id}:{bucket}"

            total = int(cache.get(f"{prefix}:total", 0) or 0)
            slow = int(cache.get(f"{prefix}:slow", 0) or 0)
            error = int(cache.get(f"{prefix}:error", 0) or 0)

            total_requests += total
            total_slow += slow
            total_errors += error

            rows.append({
                'bucket_minute': bucket,
                'total': total,
                'slow': slow,
                'error': error,
            })

        error_rate_pct = round((total_errors / total_requests) * 100, 2) if total_requests else 0
        slow_rate_pct = round((total_slow / total_requests) * 100, 2) if total_requests else 0

        return Response({
            'window_minutes': minutes,
            'summary': {
                'total': total_requests,
                'slow': total_slow,
                'error': total_errors,
                'slow_rate_pct': slow_rate_pct,
                'error_rate_pct': error_rate_pct,
            },
            'series': rows,
        })
