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

from apps.tournaments.models import Registration, Payment, PaymentVerification

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
            metadata = {}
            if detail:
                metadata["detail"] = detail
            elif tab:
                metadata["detail"] = {"tab": tab}

            if diff:
                metadata["diff"] = diff

            AuditLog.objects.create(
                user=user,
                action=action,
                tournament_id=getattr(tournament, "id", None),
                metadata=metadata,
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
            tournament_id=self.tournament.id
        ).order_by("-timestamp")

        if filters:
            if filters.get("action"):
                qs = qs.filter(action__icontains=filters["action"])
            if filters.get("user_id"):
                qs = qs.filter(user_id=filters["user_id"])
            if filters.get("since"):
                qs = qs.filter(timestamp__gte=filters["since"])
            if filters.get("tab"):
                qs = qs.filter(metadata__detail__tab=filters["tab"])

        limit = int(filters.get("limit", 100)) if filters else 100
        qs = qs[:limit]

        return [
            {
                "id": a.pk,
                "user_id": a.user_id,
                "username": getattr(a.user, "username", "") if a.user else "system",
                "action": a.action,
                "detail": a.metadata.get("detail") if isinstance(a.metadata, dict) else None,
                "diff": a.metadata.get("diff") if isinstance(a.metadata, dict) else None,
                "created_at": str(a.timestamp),
            }
            for a in qs
        ]

    def get_anomaly_summary(self):
        """Return critical tournament integrity anomalies for TOC Logs."""
        items = []

        try:
            active_count = self.tournament.active_registration_count()
            max_participants = int(self.tournament.max_participants or 0)
            overflow = max(0, active_count - max_participants)
            if max_participants > 0 and overflow > 0:
                items.append(
                    {
                        "code": "capacity_overflow",
                        "severity": "critical",
                        "title": "Active registrations exceed configured capacity",
                        "detail": f"Active {active_count} > Max {max_participants} (overflow {overflow})",
                        "count": overflow,
                    }
                )
        except Exception as e:
            logger.debug("Anomaly check capacity_overflow failed: %s", e)

        try:
            stale_slots = Registration.objects.filter(
                tournament=self.tournament,
                status__in=[Registration.REJECTED, Registration.CANCELLED, Registration.NO_SHOW],
                is_deleted=False,
            ).filter(Q(slot_number__isnull=False) | Q(checked_in=True)).count()
            if stale_slots > 0:
                items.append(
                    {
                        "code": "inactive_slot_leak",
                        "severity": "critical",
                        "title": "Inactive/disqualified registrations still hold slot or check-in state",
                        "detail": f"{stale_slots} registration(s) need slot/check-in cleanup",
                        "count": stale_slots,
                    }
                )
        except Exception as e:
            logger.debug("Anomaly check inactive_slot_leak failed: %s", e)

        try:
            inactive_qs = Registration.objects.filter(
                tournament=self.tournament,
                status__in=[Registration.REJECTED, Registration.CANCELLED, Registration.NO_SHOW],
                is_deleted=False,
            )
            pv_conflicts = inactive_qs.filter(
                payment_verification__status=PaymentVerification.Status.VERIFIED
            ).count()
            legacy_payment_conflicts = inactive_qs.filter(
                payment_verification__isnull=True,
                payment__status__in=[Payment.VERIFIED, Payment.WAIVED],
            ).count()
            total_conflicts = pv_conflicts + legacy_payment_conflicts
            if total_conflicts > 0:
                items.append(
                    {
                        "code": "inactive_verified_payment",
                        "severity": "critical",
                        "title": "Inactive/disqualified registrations have verified payment state",
                        "detail": f"{total_conflicts} registration(s) have verified/waived payment while inactive",
                        "count": total_conflicts,
                    }
                )
        except Exception as e:
            logger.debug("Anomaly check inactive_verified_payment failed: %s", e)

        critical_count = sum(int(i.get("count") or 0) for i in items if i.get("severity") == "critical")
        return {
            "critical_count": critical_count,
            "items": items,
            "is_clean": critical_count == 0,
        }

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
