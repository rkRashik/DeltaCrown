"""
TOC Sprint 8 — Announcements Service

Wraps the existing TournamentAnnouncement model and adds
broadcast, Quick Comms, and recipient-targeting helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.tournaments.models import Tournament, TournamentAnnouncement

logger = logging.getLogger("toc.announcements")


class TOCAnnouncementsService:
    """All read/write operations for the Announcements tab."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def list_announcements(
        tournament: Tournament,
        search: str = "",
        pinned_only: bool = False,
    ) -> list[dict]:
        qs = TournamentAnnouncement.objects.filter(tournament=tournament)
        if pinned_only:
            qs = qs.filter(is_pinned=True)
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(message__icontains=search)
        rows = qs.order_by("-is_pinned", "-created_at").values(
            "id", "title", "message", "created_by__username",
            "created_at", "updated_at", "is_pinned", "is_important",
        )
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "message": r["message"],
                "author": r["created_by__username"] or "System",
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                "is_pinned": r["is_pinned"],
                "is_important": r["is_important"],
            }
            for r in rows
        ]

    @staticmethod
    def create_announcement(tournament: Tournament, data: dict, user=None) -> dict:
        ann = TournamentAnnouncement.objects.create(
            tournament=tournament,
            title=data["title"],
            message=data.get("message", ""),
            created_by=user,
            is_pinned=data.get("is_pinned", False),
            is_important=data.get("is_important", False),
        )
        return {
            "id": ann.id,
            "title": ann.title,
            "created_at": ann.created_at.isoformat(),
        }

    @staticmethod
    def update_announcement(announcement_id: int, data: dict) -> dict:
        ann = TournamentAnnouncement.objects.get(pk=announcement_id)
        for field in ("title", "message", "is_pinned", "is_important"):
            if field in data:
                setattr(ann, field, data[field])
        ann.save()
        return {"id": ann.id, "updated": True}

    @staticmethod
    def delete_announcement(announcement_id: int) -> dict:
        TournamentAnnouncement.objects.filter(pk=announcement_id).delete()
        return {"deleted": True}

    # ------------------------------------------------------------------
    # Broadcast / Quick Comms
    # ------------------------------------------------------------------

    @staticmethod
    def broadcast(tournament: Tournament, data: dict, user=None) -> dict:
        """
        Create an announcement and optionally push notifications.

        data keys:
          - title (str, required)
          - message (str)
          - is_important (bool)
          - targets (str): "all" | "registered" | "checked_in" | "staff"
        """
        ann = TournamentAnnouncement.objects.create(
            tournament=tournament,
            title=data["title"],
            message=data.get("message", ""),
            created_by=user,
            is_pinned=False,
            is_important=data.get("is_important", False),
        )

        # Best-effort notification push
        target = data.get("targets", "all")
        notified = 0
        try:
            from apps.notifications.models import Notification

            recipient_ids = TOCAnnouncementsService._resolve_recipients(
                tournament, target,
            )
            notifications = [
                Notification(
                    recipient_id=uid,
                    title=f"[{tournament.name}] {ann.title}",
                    body=ann.message[:300],
                    category="tournament",
                    url=f"/tournaments/{tournament.slug}/",
                )
                for uid in recipient_ids
            ]
            Notification.objects.bulk_create(notifications, ignore_conflicts=True)
            notified = len(notifications)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Notification push failed: %s", exc)

        return {"id": ann.id, "notified": notified}

    @staticmethod
    def quick_comms(tournament: Tournament, template_key: str, user=None) -> dict:
        """
        Send a pre-built Quick Comms template.

        Template keys: match_starting, check_in_reminder, schedule_update,
                       bracket_published, results_finalized
        """
        templates = {
            "match_starting": {
                "title": "Matches Starting Soon",
                "message": "Matches are about to begin. Make sure your team is ready!",
                "is_important": True,
            },
            "check_in_reminder": {
                "title": "Check-In Reminder",
                "message": "Check-in is now open. Don't forget to check in before the deadline.",
                "is_important": True,
            },
            "schedule_update": {
                "title": "Schedule Updated",
                "message": "The tournament schedule has been updated. Please review the latest times.",
                "is_important": False,
            },
            "bracket_published": {
                "title": "Bracket Published",
                "message": "The tournament bracket is now live. Check your seeding and matchups!",
                "is_important": True,
            },
            "results_finalized": {
                "title": "Results Finalized",
                "message": "Tournament results have been finalized. Thank you for participating!",
                "is_important": True,
            },
        }
        tpl = templates.get(template_key)
        if not tpl:
            return {"error": f"Unknown template: {template_key}"}

        return TOCAnnouncementsService.broadcast(
            tournament,
            {**tpl, "targets": "all"},
            user=user,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_recipients(tournament: Tournament, target: str) -> list[int]:
        """Return user IDs based on targeting string."""
        from apps.tournaments.models import Registration

        if target == "staff":
            from apps.tournaments.models import TournamentStaffAssignment
            return list(
                TournamentStaffAssignment.objects.filter(tournament=tournament)
                .values_list("user_id", flat=True)
            )

        qs = Registration.objects.filter(tournament=tournament)
        if target == "checked_in":
            qs = qs.filter(checked_in=True)
        elif target == "registered":
            qs = qs.filter(status="approved")

        return list(qs.values_list("user_id", flat=True).distinct())

    @staticmethod
    def get_stats(tournament: Tournament) -> dict:
        qs = TournamentAnnouncement.objects.filter(tournament=tournament)
        return {
            "total": qs.count(),
            "pinned": qs.filter(is_pinned=True).count(),
            "important": qs.filter(is_important=True).count(),
        }
