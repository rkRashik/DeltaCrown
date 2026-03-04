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

from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.analytics_service import TOCAnalyticsService


class AnalyticsDashboardView(TOCBaseView):
    """Full analytics dashboard."""

    def get(self, request, slug):
        result = TOCAnalyticsService.get_analytics_dashboard(self.tournament)
        return Response(result)


class AnalyticsRegistrationView(TOCBaseView):
    """Registration funnel analytics."""

    def get(self, request, slug):
        result = TOCAnalyticsService.get_registration_analytics(self.tournament)
        return Response(result)


class AnalyticsMatchesView(TOCBaseView):
    """Match analytics."""

    def get(self, request, slug):
        result = TOCAnalyticsService.get_match_analytics(self.tournament)
        return Response(result)


class AnalyticsRevenueView(TOCBaseView):
    """Revenue analytics."""

    def get(self, request, slug):
        result = TOCAnalyticsService.get_revenue_analytics(self.tournament)
        return Response(result)


class AnalyticsEngagementView(TOCBaseView):
    """Engagement analytics."""

    def get(self, request, slug):
        result = TOCAnalyticsService.get_engagement_analytics(self.tournament)
        return Response(result)


class AnalyticsTimelineView(TOCBaseView):
    """Activity timeline."""

    def get(self, request, slug):
        limit = int(request.query_params.get("limit", 50))
        result = TOCAnalyticsService.get_activity_timeline(
            self.tournament, limit=limit,
        )
        return Response(result)


class AnalyticsExportView(TOCBaseView):
    """Export full analytics report."""

    def get(self, request, slug):
        result = TOCAnalyticsService.export_report(self.tournament)
        return Response(result)
