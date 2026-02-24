"""
TOC Sprint 11 — Audit Log & Real-Time API Views
=================================================
S11-B2  Audit log endpoint
"""

from rest_framework.response import Response

from .base import TOCBaseView
from .audit_service import TOCAuditService


class AuditLogView(TOCBaseView):
    """GET — filterable audit log for this tournament."""

    def get(self, request, slug):
        svc = TOCAuditService(self.tournament)
        filters = {
            "action": request.query_params.get("action"),
            "user_id": request.query_params.get("user_id"),
            "tab": request.query_params.get("tab"),
            "since": request.query_params.get("since"),
            "limit": request.query_params.get("limit", 100),
        }
        return Response(svc.get_audit_log(filters))
