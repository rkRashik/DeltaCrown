"""
TOC API Views — Sprint 28: Analytics & Insights tab.

GET  analytics/                — Full analytics dashboard
GET  analytics/registration/   — Registration funnel analytics
GET  analytics/matches/        — Match analytics
GET  analytics/revenue/        — Revenue analytics
GET  analytics/engagement/     — Engagement analytics
GET  analytics/timeline/       — Activity timeline
GET  analytics/export/         — Export full report
"""

from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.analytics_service import TOCAnalyticsService
from apps.tournaments.api.toc.cache_utils import toc_cache_key


class AnalyticsDashboardView(TOCBaseView):
    """Full analytics dashboard."""

    def get(self, request, slug):
        bucket = int(timezone.now().timestamp() // 15)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'dashboard', bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_analytics_dashboard(self.tournament)
        cache.set(cache_key, result, timeout=20)
        return Response(result)


class AnalyticsRegistrationView(TOCBaseView):
    """Registration funnel analytics."""

    def get(self, request, slug):
        bucket = int(timezone.now().timestamp() // 20)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'registration', bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_registration_analytics(self.tournament)
        cache.set(cache_key, result, timeout=25)
        return Response(result)


class AnalyticsMatchesView(TOCBaseView):
    """Match analytics."""

    def get(self, request, slug):
        bucket = int(timezone.now().timestamp() // 15)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'matches', bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_match_analytics(self.tournament)
        cache.set(cache_key, result, timeout=20)
        return Response(result)


class AnalyticsRevenueView(TOCBaseView):
    """Revenue analytics."""

    def get(self, request, slug):
        bucket = int(timezone.now().timestamp() // 30)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'revenue', bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_revenue_analytics(self.tournament)
        cache.set(cache_key, result, timeout=35)
        return Response(result)


class AnalyticsEngagementView(TOCBaseView):
    """Engagement analytics."""

    def get(self, request, slug):
        bucket = int(timezone.now().timestamp() // 20)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'engagement', bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_engagement_analytics(self.tournament)
        cache.set(cache_key, result, timeout=25)
        return Response(result)


class AnalyticsTimelineView(TOCBaseView):
    """Activity timeline."""

    def get(self, request, slug):
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))

        bucket = int(timezone.now().timestamp() // 15)
        cache_key = toc_cache_key('analytics', self.tournament.id, 'timeline', limit, bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCAnalyticsService.get_activity_timeline(
            self.tournament, limit=limit,
        )
        cache.set(cache_key, result, timeout=20)
        return Response(result)


class AnalyticsExportView(TOCBaseView):
    """Export full analytics report."""

    def get(self, request, slug):
        result = TOCAnalyticsService.export_report(self.tournament)
        return Response(result)
