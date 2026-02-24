"""
TOC API — Alerts Endpoints.

GET  /api/toc/<slug>/alerts/            — List active alerts
POST /api/toc/<slug>/alerts/<id>/dismiss/ — Dismiss/acknowledge an alert

Sprint 1: S1-B6, S1-B7
PRD: §2.5
"""

from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.serializers import AlertSerializer
from apps.tournaments.api.toc.service import TOCService


class AlertListView(TOCBaseView):
    """
    GET — List all active alerts for this tournament.

    Alerts are generated in real-time by CommandCenterService
    (not persisted). Each gets a synthetic `id` for dismiss tracking.
    """

    def get(self, request, slug):
        overview = TOCService.get_overview(self.tournament)
        alerts = overview['alerts']
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)


class AlertDismissView(TOCBaseView):
    """
    POST — Dismiss/acknowledge an alert by synthetic ID.

    Since alerts are generated in real-time (not DB rows), dismissals
    are tracked client-side (localStorage) for Sprint 1.
    Future sprints will persist dismissals.

    Returns: {dismissed: true, alert_id}
    """

    def post(self, request, slug, alert_id):
        # Sprint 1: acknowledgment-only (no server-side persistence yet)
        return Response({
            'dismissed': True,
            'alert_id': alert_id,
        })
