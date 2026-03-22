"""
TOC Analytics & Insights Service — Sprint 28.

Tournament analytics dashboard, registration funnel, revenue analytics,
match analytics, engagement metrics, comparison charts, and export reports.
"""

import logging
from datetime import timedelta
from collections import defaultdict
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.analytics")


class TOCAnalyticsService:
    """All read operations for the Analytics & Insights tab."""

    @staticmethod
    def get_analytics_dashboard(tournament: Tournament) -> dict:
        """Comprehensive analytics dashboard."""
        return {
            "generated_at": timezone.now().isoformat(),
            "registration": TOCAnalyticsService.get_registration_analytics(tournament),
            "matches": TOCAnalyticsService.get_match_analytics(tournament),
            "revenue": TOCAnalyticsService.get_revenue_analytics(tournament),
            "engagement": TOCAnalyticsService.get_engagement_analytics(tournament),
            "timeline": TOCAnalyticsService.get_activity_timeline(tournament),
        }

    @staticmethod
    def get_registration_analytics(tournament: Tournament) -> dict:
        """Registration funnel and demographics."""
        from apps.tournaments.models.registration import Registration

        qs = Registration.objects.filter(tournament=tournament)
        total = qs.count()
        by_status = {
            row["status"]: row["count"]
            for row in qs.values("status").annotate(count=Count("id")).filter(count__gt=0)
            if row.get("status")
        }

        # Registration trend (daily count)
        trend = []
        if total > 0:
            regs = qs.order_by("created_at").values("created_at")
            daily = defaultdict(int)
            for r in regs:
                if r["created_at"]:
                    day = r["created_at"].strftime("%Y-%m-%d")
                    daily[day] += 1
            cumulative = 0
            for day in sorted(daily.keys()):
                cumulative += daily[day]
                trend.append({"date": day, "count": daily[day], "cumulative": cumulative})

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
        matches = Match.objects.filter(tournament=tournament)
        state_rows = matches.values("state").annotate(count=Count("id"))
        by_state = {row["state"]: row["count"] for row in state_rows if row.get("state")}
        for state_val in ["scheduled", "check_in", "ready", "live", "pending_result", "completed", "disputed", "forfeit", "cancelled"]:
            by_state.setdefault(state_val, 0)

        total = sum(by_state.values())
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
        for m in completed.order_by("id")[:100]:
            if m.participant1_score is not None and m.participant2_score is not None:
                diff = abs(m.participant1_score - m.participant2_score)
                closest.append({
                    "match_id": m.id,
                    "match_number": m.match_number,
                    "p1": m.participant1_name or "TBD",
                    "p2": m.participant2_name or "TBD",
                    "score": f"{m.participant1_score}-{m.participant2_score}",
                    "diff": diff,
                })
        closest.sort(key=lambda x: x["diff"])

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
        # Confirmed registrations are considered paid
        paid_count = Registration.objects.filter(
            tournament=tournament,
            status="confirmed",
        ).count()

        total_revenue = paid_count * float(entry_fee)
        # Cancelled registrations may represent refunds
        refund_count = Registration.objects.filter(
            tournament=tournament,
            status="cancelled",
        ).count()
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
        matches = Match.objects.filter(tournament=tournament)
        streamed = matches.exclude(stream_url__isnull=True).exclude(stream_url="").count()
        total_matches = matches.count()

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
        ).order_by("-completed_at")[:10]

        for m in recent_matches:
            desc = f"Match #{m.match_number}: {m.participant1_name or 'TBD'} vs {m.participant2_name or 'TBD'} — Score: {m.participant1_score or 0}-{m.participant2_score or 0}"
            activities.append({
                "type": "match",
                "icon": "check-circle",
                "title": f"Match #{m.match_number}: {m.participant1_name or 'TBD'} vs {m.participant2_name or 'TBD'}",
                "detail": f"Score: {m.participant1_score or 0}-{m.participant2_score or 0}",
                "description": desc,
                "timestamp": m.completed_at.isoformat() if m.completed_at else None,
            })

        # Recent registrations
        from apps.tournaments.models.registration import Registration
        recent_regs = Registration.objects.filter(
            tournament=tournament,
        ).select_related("user").order_by("-created_at")[:10]

        for r in recent_regs:
            name = r.user.username if r.user else f"Registration #{r.pk}"
            desc = f"{name} registered — Status: {r.status}"
            activities.append({
                "type": "registration",
                "icon": "user-plus",
                "title": f"{name} registered",
                "detail": f"Status: {r.status}",
                "description": desc,
                "timestamp": r.created_at.isoformat() if r.created_at else None,
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
