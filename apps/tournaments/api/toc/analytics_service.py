"""
TOC Analytics & Insights Service — Sprint 28.

Tournament analytics dashboard, registration funnel, revenue analytics,
match analytics, engagement metrics, comparison charts, and export reports.
"""

import logging
import time
from datetime import timedelta
from collections import defaultdict
from django.db.models import Q, Count, Sum, Avg, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.analytics")


class TOCAnalyticsService:
    """All read operations for the Analytics & Insights tab."""

    @staticmethod
    def get_analytics_dashboard(tournament: Tournament) -> dict:
        """Comprehensive analytics dashboard."""
        t0 = time.perf_counter()
        t = t0

        registration = TOCAnalyticsService.get_registration_analytics(tournament)
        t_registration = time.perf_counter()

        matches = TOCAnalyticsService.get_match_analytics(tournament)
        t_matches = time.perf_counter()

        revenue = TOCAnalyticsService.get_revenue_analytics(tournament)
        t_revenue = time.perf_counter()

        engagement = TOCAnalyticsService.get_engagement_analytics(tournament)
        t_engagement = time.perf_counter()

        # Keep dashboard payload lighter; full timeline remains available via timeline endpoint.
        timeline = TOCAnalyticsService.get_activity_timeline(tournament, limit=25)
        t_timeline = time.perf_counter()

        result = {
            "generated_at": timezone.now().isoformat(),
            "registration": registration,
            "matches": matches,
            "revenue": revenue,
            "engagement": engagement,
            "timeline": timeline,
        }
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if elapsed_ms >= 250:
            logger.info(
                "TOC analytics dashboard timings tournament_id=%s elapsed_ms=%.2f registration_ms=%.2f matches_ms=%.2f revenue_ms=%.2f engagement_ms=%.2f timeline_ms=%.2f",
                tournament.id,
                elapsed_ms,
                (t_registration - t) * 1000.0,
                (t_matches - t_registration) * 1000.0,
                (t_revenue - t_matches) * 1000.0,
                (t_engagement - t_revenue) * 1000.0,
                (t_timeline - t_engagement) * 1000.0,
            )
        return result

    @staticmethod
    def get_registration_analytics(tournament: Tournament) -> dict:
        """Registration funnel and demographics."""
        from apps.tournaments.models.registration import Registration

        qs = Registration.objects.filter(tournament=tournament)
        status_rows = list(
            qs.values("status").annotate(count=Count("id")).filter(count__gt=0)
        )
        by_status = {
            row["status"]: row["count"]
            for row in status_rows
            if row.get("status")
        }
        total = sum(row.get("count") or 0 for row in status_rows)

        # Registration trend (daily count)
        trend = []
        if total > 0:
            daily_rows = (
                qs.exclude(created_at__isnull=True)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )
            cumulative = 0
            for row in daily_rows:
                day = row.get("day")
                count = row.get("count") or 0
                if day is None:
                    continue
                cumulative += count
                trend.append({"date": day.strftime("%Y-%m-%d"), "count": count, "cumulative": cumulative})

        # Capacity
        capacity = tournament.max_participants or 0
        fill_rate = round(total / capacity * 100) if capacity > 0 else 0

        return {
            "total": total,
            "by_status": by_status,
            "capacity": capacity,
            "fill_rate": fill_rate,
            "trend": trend,
            "active": by_status.get("confirmed", 0) + by_status.get("auto_approved", 0),
            # Aliases for JS funnel: approved/pending/rejected
            "approved": by_status.get("confirmed", 0) + by_status.get("auto_approved", 0),
            "pending": by_status.get("pending", 0) + by_status.get("submitted", 0) + by_status.get("needs_review", 0),
            "rejected": by_status.get("rejected", 0) + by_status.get("cancelled", 0),
        }

    @staticmethod
    def get_match_analytics(tournament: Tournament) -> dict:
        """Match performance analytics."""
        matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        agg = matches.aggregate(
            total=Count("id"),
            scheduled=Count("id", filter=Q(state="scheduled")),
            check_in=Count("id", filter=Q(state="check_in")),
            ready=Count("id", filter=Q(state="ready")),
            live=Count("id", filter=Q(state="live")),
            pending_result=Count("id", filter=Q(state="pending_result")),
            completed=Count("id", filter=Q(state="completed")),
            disputed=Count("id", filter=Q(state="disputed")),
            forfeit=Count("id", filter=Q(state="forfeit")),
            cancelled=Count("id", filter=Q(state="cancelled")),
        )
        by_state = {
            "scheduled": agg.get("scheduled") or 0,
            "check_in": agg.get("check_in") or 0,
            "ready": agg.get("ready") or 0,
            "live": agg.get("live") or 0,
            "pending_result": agg.get("pending_result") or 0,
            "completed": agg.get("completed") or 0,
            "disputed": agg.get("disputed") or 0,
            "forfeit": agg.get("forfeit") or 0,
            "cancelled": agg.get("cancelled") or 0,
        }
        for state_val in ["scheduled", "check_in", "ready", "live", "pending_result", "completed", "disputed", "forfeit", "cancelled"]:
            by_state.setdefault(state_val, 0)

        total = agg.get("total") or sum(by_state.values())
        # JS-friendly aliases
        by_state["in_progress"] = by_state.get("live", 0)
        by_state["forfeited"] = by_state.get("forfeit", 0)

        completed = matches.filter(state="completed")
        completed_count = by_state.get("completed", 0)

        # Average match duration
        avg_duration = None
        avg_dur = completed.filter(
            started_at__isnull=False,
            completed_at__isnull=False,
        ).aggregate(avg=Avg(F("completed_at") - F("started_at"))).get("avg")
        if avg_dur:
            avg_minutes = avg_dur.total_seconds() / 60
            if avg_minutes > 0:
                avg_duration = round(avg_minutes, 1)

        # Forfeit rate
        forfeit_count = by_state.get("forfeit", 0)
        forfeit_rate = round(forfeit_count / total * 100, 1) if total > 0 else 0

        # Dispute rate
        dispute_count = by_state.get("disputed", 0)
        dispute_rate = round(dispute_count / total * 100, 1) if total > 0 else 0

        # Matches per round
        rounds_data = []
        rounds = matches.values("round_number").annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(state="completed")),
        ).order_by("round_number")
        for r in rounds:
            rn = r["round_number"]
            round_completed = r.get("completed", 0)
            rounds_data.append({
                "round": rn,
                "total": r["total"],
                "completed": round_completed,
                "pct": round(round_completed / r["total"] * 100) if r["total"] > 0 else 0,
            })

        # Closest matches (smallest score difference)
        closest = []
        for m in completed.order_by("id").values(
            "id",
            "match_number",
            "participant1_name",
            "participant2_name",
            "participant1_score",
            "participant2_score",
        )[:40]:
            p1_score = m.get("participant1_score")
            p2_score = m.get("participant2_score")
            if p1_score is not None and p2_score is not None:
                diff = abs(p1_score - p2_score)
                closest.append({
                    "match_id": m["id"],
                    "match_number": m.get("match_number"),
                    "p1": m.get("participant1_name") or "TBD",
                    "p2": m.get("participant2_name") or "TBD",
                    "score": f"{p1_score}-{p2_score}",
                    "diff": diff,
                })
        closest.sort(key=lambda x: x["diff"])

        # T2-6: Stage segmentation for GROUP_PLAYOFF tournaments
        stage_breakdown = None
        if tournament.format == Tournament.GROUP_PLAYOFF:
            group_qs = matches.filter(bracket__isnull=True)
            ko_qs = matches.filter(bracket__isnull=False)
            g_total = group_qs.count()
            g_completed = group_qs.filter(state="completed").count()
            k_total = ko_qs.count()
            k_completed = ko_qs.filter(state="completed").count()
            stage_breakdown = {
                "group_stage": {
                    "total": g_total,
                    "completed": g_completed,
                    "pct": round(g_completed / g_total * 100) if g_total > 0 else 0,
                },
                "knockout": {
                    "total": k_total,
                    "completed": k_completed,
                    "pct": round(k_completed / k_total * 100) if k_total > 0 else 0,
                },
            }

        return {
            "total": total,
            "by_state": by_state,
            "completed": completed_count,
            "completion_pct": round(completed_count / total * 100) if total > 0 else 0,
            "avg_duration_minutes": avg_duration,
            "forfeit_rate": forfeit_rate,
            "dispute_rate": dispute_rate,
            "rounds": rounds_data,
            "closest_matches": closest[:5],
            "stage_breakdown": stage_breakdown,
            # JS aliases: in_progress for live, forfeited for forfeit
            "in_progress": by_state.get("live", 0),
            "forfeited": by_state.get("forfeit", 0),
        }

    @staticmethod
    def get_revenue_analytics(tournament: Tournament) -> dict:
        """Revenue and financial analytics."""
        config = tournament.config or {}
        entry_fee = tournament.entry_fee_amount or 0
        currency = tournament.entry_fee_currency or "USD"
        prize_pool = tournament.prize_pool or 0

        from apps.tournaments.models.registration import Registration
        agg = Registration.objects.filter(tournament=tournament).aggregate(
            paid_count=Count("id", filter=Q(status="confirmed")),
            refund_count=Count("id", filter=Q(status="cancelled")),
        )
        paid_count = agg.get("paid_count") or 0

        total_revenue = paid_count * float(entry_fee)
        # Cancelled registrations may represent refunds
        refund_count = agg.get("refund_count") or 0
        refund_amount = refund_count * float(entry_fee)
        net_revenue = total_revenue - refund_amount

        return {
            "entry_fee": float(entry_fee),
            "currency": currency,
            "prize_pool": float(prize_pool),
            "paid_count": paid_count,
            "total_revenue": total_revenue,
            "refund_count": refund_count,
            "refund_amount": refund_amount,
            "net_revenue": net_revenue,
            "avg_revenue_per_participant": round(net_revenue / paid_count, 2) if paid_count > 0 else 0,
            "profit_margin": round((net_revenue - float(prize_pool)) / net_revenue * 100, 1) if net_revenue > 0 else 0,
        }

    @staticmethod
    def get_engagement_analytics(tournament: Tournament) -> dict:
        """Engagement and activity metrics."""
        matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        agg = matches.aggregate(
            total=Count("id"),
            streamed=Count("id", filter=~Q(stream_url__isnull=True) & ~Q(stream_url="")),
        )
        streamed = agg.get("streamed") or 0
        total_matches = agg.get("total") or 0

        config = tournament.config or {}
        engagement = config.get("engagement_stats", {})

        return {
            "streamed_matches": streamed,
            "total_matches": total_matches,
            "stream_coverage": round(streamed / total_matches * 100) if total_matches > 0 else 0,
            "page_views": engagement.get("page_views", 0),
            "bracket_views": engagement.get("bracket_views", 0),
            "unique_visitors": engagement.get("unique_visitors", 0),
        }

    @staticmethod
    def get_activity_timeline(tournament: Tournament, limit: int = 50) -> list:
        """Global activity feed across all domains."""
        activities = []

        # Recent matches
        recent_matches = Match.objects.filter(
            tournament=tournament,
            state="completed",
        ).order_by("-completed_at").values(
            "match_number",
            "participant1_name",
            "participant2_name",
            "participant1_score",
            "participant2_score",
            "completed_at",
        )[:10]

        for m in recent_matches:
            p1_name = m.get("participant1_name") or "TBD"
            p2_name = m.get("participant2_name") or "TBD"
            p1_score = m.get("participant1_score") or 0
            p2_score = m.get("participant2_score") or 0
            match_number = m.get("match_number")
            completed_at = m.get("completed_at")
            desc = f"Match #{match_number}: {p1_name} vs {p2_name} — Score: {p1_score}-{p2_score}"
            activities.append({
                "type": "match",
                "icon": "check-circle",
                "title": f"Match #{match_number}: {p1_name} vs {p2_name}",
                "detail": f"Score: {p1_score}-{p2_score}",
                "description": desc,
                "timestamp": completed_at.isoformat() if completed_at else None,
            })

        # Recent registrations
        from apps.tournaments.models.registration import Registration
        recent_regs = Registration.objects.filter(
            tournament=tournament,
        ).select_related("user").order_by("-created_at").values(
            "id",
            "status",
            "created_at",
            "user__username",
        )[:10]

        for r in recent_regs:
            reg_id = r.get("id")
            status = r.get("status")
            created_at = r.get("created_at")
            username = r.get("user__username")
            name = username if username else f"Registration #{reg_id}"
            desc = f"{name} registered — Status: {status}"
            activities.append({
                "type": "registration",
                "icon": "user-plus",
                "title": f"{name} registered",
                "detail": f"Status: {status}",
                "description": desc,
                "timestamp": created_at.isoformat() if created_at else None,
            })

        # Sort by timestamp
        activities.sort(key=lambda a: a.get("timestamp") or "", reverse=True)
        return activities[:limit]

    @staticmethod
    def export_report(tournament: Tournament, format: str = "csv") -> dict:
        """Generate exportable tournament report."""
        data = TOCAnalyticsService.get_analytics_dashboard(tournament)

        report = {
            "tournament": tournament.name,
            "slug": tournament.slug,
            "generated_at": timezone.now().isoformat(),
            "registration": data["registration"],
            "matches": data["matches"],
            "revenue": data["revenue"],
        }
        return report
