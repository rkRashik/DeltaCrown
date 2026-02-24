"""
TOC Sprint 11 — Audit & Real-Time Service
===========================================
S11-B1  Audit log middleware — capture all TOC write operations
S11-B2  Audit log API endpoint
S11-B3  WebSocket consumer scaffolding
S11-B4  Real-time event dispatch helpers
"""

import json
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class TOCAuditService:
    """Audit log service for TOC operations."""

    def __init__(self, tournament):
        self.tournament = tournament

    # ------------------------------------------------------------------
    # S11-B1  Write audit entry
    # ------------------------------------------------------------------
    @staticmethod
    def log_action(tournament, user, action, tab="", detail=None, diff=None):
        """
        Record a TOC audit entry.
        Uses the existing AuditLog model from the tournaments app.
        """
        from apps.tournaments.models import AuditLog

        try:
            extra = {}
            if detail:
                extra["detail"] = detail
            if diff:
                extra["diff"] = diff

            AuditLog.objects.create(
                tournament=tournament,
                user=user,
                action=action,
                extra_data=extra,
            )
        except Exception as e:
            logger.warning("Audit log write failed: %s", e)
            # Best-effort — never block the main operation

    # ------------------------------------------------------------------
    # S11-B2  Read audit log with filters
    # ------------------------------------------------------------------
    def get_audit_log(self, filters=None):
        from apps.tournaments.models import AuditLog

        qs = AuditLog.objects.filter(
            tournament=self.tournament
        ).order_by("-created_at")

        if filters:
            if filters.get("action"):
                qs = qs.filter(action__icontains=filters["action"])
            if filters.get("user_id"):
                qs = qs.filter(user_id=filters["user_id"])
            if filters.get("since"):
                qs = qs.filter(created_at__gte=filters["since"])
            if filters.get("tab"):
                qs = qs.filter(extra_data__detail__tab=filters["tab"])

        limit = int(filters.get("limit", 100)) if filters else 100
        qs = qs[:limit]

        return [
            {
                "id": a.pk,
                "user_id": a.user_id,
                "username": getattr(a.user, "username", "") if a.user else "system",
                "action": a.action,
                "detail": a.extra_data.get("detail") if isinstance(a.extra_data, dict) else None,
                "diff": a.extra_data.get("diff") if isinstance(a.extra_data, dict) else None,
                "created_at": str(a.created_at),
            }
            for a in qs
        ]

    # ------------------------------------------------------------------
    # S11-B4  Real-time event dispatch helpers
    # ------------------------------------------------------------------
    @staticmethod
    def dispatch_event(tournament_slug, event_type, payload=None):
        """
        Dispatch a real-time event to all connected WebSocket clients.
        Uses Django Channels if available, otherwise a no-op.
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"toc_{tournament_slug}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "toc.event",
                        "event_type": event_type,
                        "payload": payload or {},
                    },
                )
        except (ImportError, Exception) as e:
            logger.debug("Real-time dispatch unavailable: %s", e)
