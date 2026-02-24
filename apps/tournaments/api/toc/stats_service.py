"""
TOC Sprint 9 — Stats, Certificates & Trust Index Service
=========================================================
Provides tournament stats aggregation, certificate template CRUD + generation,
trophy management, and Trust Index computation.
"""

import logging
import string
from datetime import timedelta
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class TOCStatsService:
    """Service layer for Sprint 9 features."""

    def __init__(self, tournament):
        self.tournament = tournament

    # ------------------------------------------------------------------
    # S9-B1  Tournament stats summary
    # ------------------------------------------------------------------
    def get_tournament_stats(self):
        """Return a comprehensive stats summary across matches, participants, disputes."""
        from apps.tournaments.models import (
            DisputeRecord,
            Match,
            Registration,
        )

        t = self.tournament

        # --- Match stats ---
        matches_qs = Match.objects.filter(
            Q(bracket__tournament=t)
            | Q(group_stage__group__tournament=t)
        )
        total_matches = matches_qs.count()
        completed_matches = matches_qs.filter(status="completed").count()
        in_progress_matches = matches_qs.filter(status="in_progress").count()
        pending_matches = matches_qs.filter(status="pending").count()

        avg_duration = None
        duration_qs = matches_qs.filter(
            status="completed",
            completed_at__isnull=False,
            started_at__isnull=False,
        )
        if duration_qs.exists():
            durations = duration_qs.annotate(
                dur=F("completed_at") - F("started_at")
            ).aggregate(avg_dur=Avg("dur"))
            if durations["avg_dur"]:
                avg_duration = int(durations["avg_dur"].total_seconds() // 60)

        # --- Participant stats ---
        reg_qs = Registration.objects.filter(tournament=t)
        total_registrations = reg_qs.count()
        approved = reg_qs.filter(status="approved").count()
        checked_in = reg_qs.filter(checked_in=True).count()
        disqualified = reg_qs.filter(status="disqualified").count()
        dq_rate = round(disqualified / total_registrations * 100, 1) if total_registrations else 0

        # --- Dispute stats ---
        dispute_qs = DisputeRecord.objects.filter(tournament=t)
        total_disputes = dispute_qs.count()
        open_disputes = dispute_qs.filter(status__in=["open", "under_review"]).count()
        resolved_disputes = dispute_qs.filter(status__in=["resolved", "dismissed"]).count()

        # --- Completion ---
        completion_pct = round(completed_matches / total_matches * 100, 1) if total_matches else 0

        return {
            "matches": {
                "total": total_matches,
                "completed": completed_matches,
                "in_progress": in_progress_matches,
                "pending": pending_matches,
                "completion_pct": completion_pct,
                "avg_duration_minutes": avg_duration,
            },
            "participants": {
                "total_registrations": total_registrations,
                "approved": approved,
                "checked_in": checked_in,
                "disqualified": disqualified,
                "dq_rate_pct": dq_rate,
            },
            "disputes": {
                "total": total_disputes,
                "open": open_disputes,
                "resolved": resolved_disputes,
            },
        }

    # ------------------------------------------------------------------
    # S9-B2  Certificate template CRUD + generate / download
    # ------------------------------------------------------------------
    def list_certificate_templates(self):
        from apps.tournaments.models import CertificateTemplate

        return list(
            CertificateTemplate.objects.filter(tournament=self.tournament)
            .order_by("-is_default", "-created_at")
            .values(
                "id", "name", "is_default",
                "variables", "created_at", "updated_at",
            )
        )

    def create_certificate_template(self, data):
        from apps.tournaments.models import CertificateTemplate

        tpl = CertificateTemplate.objects.create(
            tournament=self.tournament,
            name=data["name"],
            template_html=data.get("template_html", ""),
            variables=data.get("variables", []),
            is_default=data.get("is_default", False),
        )
        if tpl.is_default:
            CertificateTemplate.objects.filter(
                tournament=self.tournament
            ).exclude(pk=tpl.pk).update(is_default=False)
        return {"id": str(tpl.id), "name": tpl.name, "is_default": tpl.is_default}

    def update_certificate_template(self, template_id, data):
        from apps.tournaments.models import CertificateTemplate

        tpl = CertificateTemplate.objects.get(
            pk=template_id, tournament=self.tournament
        )
        for field in ("name", "template_html", "variables", "is_default"):
            if field in data:
                setattr(tpl, field, data[field])
        tpl.save()
        if tpl.is_default:
            CertificateTemplate.objects.filter(
                tournament=self.tournament
            ).exclude(pk=tpl.pk).update(is_default=False)
        return {"id": str(tpl.id), "name": tpl.name}

    def delete_certificate_template(self, template_id):
        from apps.tournaments.models import CertificateTemplate

        CertificateTemplate.objects.filter(
            pk=template_id, tournament=self.tournament
        ).delete()

    def generate_certificate(self, template_id, user_id, extra_context=None):
        """Render a certificate for a single user. Returns CertificateRecord."""
        from apps.tournaments.models import CertificateRecord, CertificateTemplate

        tpl = CertificateTemplate.objects.get(
            pk=template_id, tournament=self.tournament
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(pk=user_id)

        context = {
            "tournament_name": self.tournament.name,
            "participant_name": getattr(user, "display_name", user.username),
            "date": timezone.now().strftime("%B %d, %Y"),
        }
        if extra_context:
            context.update(extra_context)

        rendered = string.Template(tpl.template_html).safe_substitute(context)

        record, created = CertificateRecord.objects.update_or_create(
            user=user,
            tournament=self.tournament,
            template=tpl,
            defaults={
                "rendered_html": rendered,
                "context_data": context,
                "issued_at": timezone.now(),
            },
        )
        return {
            "id": str(record.id),
            "user_id": user.pk,
            "rendered_html": rendered,
            "issued_at": str(record.issued_at),
        }

    def bulk_generate_certificates(self, template_id, user_ids=None):
        """Generate certificates for multiple (or all approved) participants."""
        from apps.tournaments.models import Registration

        if user_ids is None:
            regs = Registration.objects.filter(
                tournament=self.tournament, status="approved"
            ).select_related("user")
            user_ids = list(regs.values_list("user_id", flat=True))

        results = []
        for uid in user_ids:
            try:
                r = self.generate_certificate(template_id, uid)
                results.append(r)
            except Exception as exc:
                logger.warning("Certificate generation failed for user %s: %s", uid, exc)
                results.append({"user_id": uid, "error": str(exc)})
        return {"generated": len([r for r in results if "error" not in r]), "total": len(results), "results": results}

    # ------------------------------------------------------------------
    # S9-B3  Trophy / Achievement endpoints
    # ------------------------------------------------------------------
    def list_trophies(self):
        from apps.tournaments.models import ProfileTrophy

        return list(
            ProfileTrophy.objects.all()
            .order_by("rarity", "name")
            .values("id", "name", "icon", "description", "rarity", "criteria")
        )

    def award_trophy(self, trophy_id, user_id):
        from apps.tournaments.models import ProfileTrophy, UserTrophy

        trophy = ProfileTrophy.objects.get(pk=trophy_id)
        obj, created = UserTrophy.objects.get_or_create(
            user_id=user_id,
            trophy=trophy,
            tournament=self.tournament,
            defaults={"earned_at": timezone.now()},
        )
        return {
            "id": str(obj.id),
            "trophy_name": trophy.name,
            "user_id": user_id,
            "created": created,
        }

    def revoke_trophy(self, trophy_id, user_id):
        from apps.tournaments.models import UserTrophy

        UserTrophy.objects.filter(
            trophy_id=trophy_id,
            user_id=user_id,
            tournament=self.tournament,
        ).delete()

    def get_user_trophies(self, user_id):
        from apps.tournaments.models import UserTrophy

        return list(
            UserTrophy.objects.filter(user_id=user_id)
            .select_related("trophy")
            .values(
                "id", "trophy__name", "trophy__icon", "trophy__rarity",
                "tournament_id", "earned_at",
            )
        )

    # ------------------------------------------------------------------
    # S9-B4  Trust Index read
    # ------------------------------------------------------------------
    def get_trust_index(self, user_id):
        from apps.tournaments.models import TrustEvent

        agg = TrustEvent.objects.filter(user_id=user_id).aggregate(
            total=Sum("delta"),
            event_count=Count("id"),
        )
        score = agg["total"] or 0
        event_count = agg["event_count"] or 0

        # Clamp to 0-100 range with base of 50
        index = max(0, min(100, 50 + score))

        # Rating label
        if index >= 80:
            rating = "excellent"
        elif index >= 60:
            rating = "good"
        elif index >= 40:
            rating = "fair"
        elif index >= 20:
            rating = "poor"
        else:
            rating = "critical"

        return {
            "user_id": user_id,
            "trust_index": index,
            "raw_score": score,
            "event_count": event_count,
            "rating": rating,
        }

    # ------------------------------------------------------------------
    # S9-B5  Trust event log
    # ------------------------------------------------------------------
    def get_trust_events(self, user_id, limit=50):
        from apps.tournaments.models import TrustEvent

        return list(
            TrustEvent.objects.filter(user_id=user_id)
            .order_by("-created_at")[:limit]
            .values("id", "event_type", "delta", "reason", "tournament_id", "created_at")
        )

    def add_trust_event(self, user_id, event_type, delta, reason=""):
        from apps.tournaments.models import TrustEvent

        evt = TrustEvent.objects.create(
            user_id=user_id,
            event_type=event_type,
            delta=delta,
            reason=reason,
            tournament=self.tournament,
        )
        return {
            "id": str(evt.id),
            "event_type": evt.event_type,
            "delta": evt.delta,
            "new_trust_index": self.get_trust_index(user_id)["trust_index"],
        }
