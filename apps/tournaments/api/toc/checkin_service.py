"""
TOC Check-in Hub Service — Sprint 29.

Real-time check-in dashboard, countdown timer, auto-DQ engine,
per-round check-in, captain confirmation, and notification blasts.

Enriches participant data with team logos, game IDs (from GameProfile),
profile slugs, coordinator info for a production-quality UI.
"""

import logging
from datetime import timedelta
from django.db.models import Q, Count, Case, When, BooleanField, Value
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.checkin")


def _lazy_org_team():
    try:
        from apps.organizations.models.team import Team as OrgTeam
        return OrgTeam
    except ImportError:
        return None


class TOCCheckinService:
    """All read/write operations for the Check-in Hub tab."""

    @staticmethod
    def get_checkin_dashboard(tournament: Tournament, round_number: int = 0) -> dict:
        """Full check-in dashboard data with enriched participant info."""
        from apps.tournaments.models.registration import Registration

        qs = Registration.objects.filter(
            tournament=tournament,
            status__in=["confirmed", "auto_approved", "pending"],
        ).select_related("user")

        total = qs.count()
        checked_in = qs.filter(checked_in=True).count()
        pending = total - checked_in

        # ── Config ──
        config = tournament.config or {}
        checkin_config = config.get("checkin", {})
        checkin_open = checkin_config.get("is_open", False)
        checkin_deadline = checkin_config.get("deadline", None)
        auto_dq_enabled = checkin_config.get("auto_dq", False)
        checkin_window_minutes = checkin_config.get("window_minutes", 30)
        per_round_checkin = checkin_config.get("per_round", False)

        # ── Time calculations ──
        deadline_dt = None
        time_remaining = None
        if checkin_deadline:
            try:
                from django.utils.dateparse import parse_datetime
                deadline_dt = parse_datetime(checkin_deadline)
                if deadline_dt and deadline_dt > timezone.now():
                    delta = deadline_dt - timezone.now()
                    time_remaining = int(delta.total_seconds())
            except Exception:
                pass

        # ── Game meta ──
        game_meta = {}
        game_dn = ""
        try:
            g = tournament.game
            game_dn = getattr(g, "display_name", "") or ""
            game_meta = {
                "display_name": game_dn,
                "game_id_label": getattr(g, "game_id_label", "Game ID") or "Game ID",
            }
        except Exception:
            pass

        # ── Batch-load team metadata ──
        all_team_ids = list({r.team_id for r in qs if r.team_id})
        team_meta: dict[int, dict] = {}
        if all_team_ids:
            OrgTeam = _lazy_org_team()
            if OrgTeam:
                try:
                    for obj in OrgTeam.objects.filter(id__in=all_team_ids).only(
                        "id", "name", "tag", "slug", "logo", "primary_color",
                    ):
                        logo_url = ""
                        try:
                            logo_url = obj.logo.url if obj.logo else ""
                        except Exception:
                            pass
                        team_meta[obj.id] = {
                            "name": obj.name or f"Team {obj.id}",
                            "tag": getattr(obj, "tag", "") or "",
                            "slug": obj.slug or "",
                            "logo_url": logo_url,
                            "primary_color": getattr(obj, "primary_color", "") or "",
                        }
                except Exception:
                    pass

        # ── Batch-load lineup snapshots for player counts ──
        lineup_counts: dict[int, int] = {}
        for reg in qs:
            if reg.team_id and reg.lineup_snapshot:
                lineup_counts[reg.team_id] = len(reg.lineup_snapshot)

        # ── Per-round check-in ──
        round_checkin = {}
        if per_round_checkin and round_number > 0:
            matches = Match.objects.filter(
                tournament=tournament,
                round_number=round_number,
            ).exclude(state__in=["completed", "cancelled", "forfeit"])
            for m in matches:
                round_checkin[m.id] = {
                    "match_id": m.id,
                    "match_number": getattr(m, "match_number", m.id),
                    "round": m.round_number,
                    "p1_name": getattr(m, "participant1_name", "") or "TBD",
                    "p2_name": getattr(m, "participant2_name", "") or "TBD",
                    "p1_checked_in": getattr(m, "participant1_checked_in", False),
                    "p2_checked_in": getattr(m, "participant2_checked_in", False),
                    "scheduled_time": m.scheduled_time.isoformat()
                        if hasattr(m, "scheduled_time") and m.scheduled_time else None,
                }

        # ── Build enriched participant list ──
        participants = []
        for reg in qs.order_by("-checked_in", "-updated_at"):
            username = "Unknown"
            display_name = ""
            team_name = ""
            team_slug = ""
            team_tag = ""
            team_logo = ""
            team_color = ""
            player_count = 0

            if reg.user:
                username = reg.user.username
                display_name = getattr(reg.user, "display_name", "") or username

            if reg.team_id:
                meta = team_meta.get(reg.team_id, {})
                team_name = meta.get("name", f"Team #{reg.team_id}")
                team_slug = meta.get("slug", "")
                team_tag = meta.get("tag", "")
                team_logo = meta.get("logo_url", "")
                team_color = meta.get("primary_color", "")
                player_count = lineup_counts.get(reg.team_id, 0)

            # For team regs, reg.user is None — use team name as display
            if not display_name and team_name:
                username = team_name
                display_name = team_name

            participants.append({
                "id": reg.id,
                "name": display_name or username,
                "username": username,
                "display_name": display_name or username,
                "team_name": team_name,
                "team_id": reg.team_id,
                "team_slug": team_slug,
                "team_tag": team_tag,
                "team_logo": team_logo,
                "team_color": team_color,
                "player_count": player_count,
                "user_id": reg.user_id,
                "checked_in": reg.checked_in,
                "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
                "status": reg.status,
                "registered_at": reg.registered_at.isoformat() if reg.registered_at else None,
            })

        return {
            "config": {
                "open": checkin_open,
                "is_open": checkin_open,
                "deadline": checkin_deadline,
                "auto_dq": auto_dq_enabled,
                "window_minutes": checkin_window_minutes,
                "per_round": per_round_checkin,
            },
            "game_meta": game_meta,
            "summary": {
                "total": total,
                "checked_in": checked_in,
                "pending": pending,
                "not_checked_in": pending,
                "pct": round(checked_in / total * 100) if total > 0 else 0,
                "time_remaining": time_remaining,
            },
            "participants": participants,
            "round_checkin": list(round_checkin.values()) if round_checkin else [],
        }

    @staticmethod
    def open_checkin(tournament: Tournament, window_minutes: int = 30) -> dict:
        """Open the check-in window."""
        config = tournament.config or {}
        deadline = timezone.now() + timedelta(minutes=window_minutes)
        config["checkin"] = {
            "is_open": True,
            "deadline": deadline.isoformat(),
            "window_minutes": window_minutes,
            "auto_dq": config.get("checkin", {}).get("auto_dq", False),
            "per_round": config.get("checkin", {}).get("per_round", False),
            "opened_at": timezone.now().isoformat(),
        }
        tournament.config = config
        tournament.save(update_fields=["config"])
        logger.info(f"Check-in opened for {tournament.slug}, deadline={deadline}")
        # Fire auto-notification for check-in open
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "checkin_open")
        except Exception:
            pass
        return {"status": "open", "deadline": deadline.isoformat(), "window_minutes": window_minutes}

    @staticmethod
    def close_checkin(tournament: Tournament) -> dict:
        """Close the check-in window."""
        config = tournament.config or {}
        checkin = config.get("checkin", {})
        checkin["is_open"] = False
        checkin["closed_at"] = timezone.now().isoformat()
        config["checkin"] = checkin
        tournament.config = config
        tournament.save(update_fields=["config"])
        logger.info(f"Check-in closed for {tournament.slug}")
        # Fire auto-notification for check-in close
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "checkin_closed")
        except Exception:
            pass
        return {"status": "closed"}

    @staticmethod
    def force_checkin(tournament: Tournament, participant_id: int) -> dict:
        """Admin force check-in for a specific participant."""
        from apps.tournaments.models.registration import Registration

        try:
            reg = Registration.objects.get(id=participant_id, tournament=tournament)
        except Registration.DoesNotExist:
            return {"error": "Participant not found"}

        reg.checked_in = True
        reg.checked_in_at = timezone.now()
        reg.save(update_fields=["checked_in", "checked_in_at"])
        logger.info(f"Force check-in: participant {participant_id} in {tournament.slug}")
        return {"status": "checked_in", "participant_id": participant_id}

    @staticmethod
    def force_checkin_match(tournament: Tournament, match_id: int, side: str) -> dict:
        """Force check-in for a match participant (side = 'p1' or 'p2')."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return {"error": "Match not found"}

        if side == "p1":
            match.participant1_checked_in = True
        elif side == "p2":
            match.participant2_checked_in = True
        else:
            return {"error": "Invalid side, use 'p1' or 'p2'"}

        match.save(update_fields=[f"participant{'1' if side == 'p1' else '2'}_checked_in"])
        return {"status": "checked_in", "match_id": match_id, "side": side}

    @staticmethod
    def auto_dq(tournament: Tournament) -> dict:
        """Auto-disqualify teams that haven't checked in after deadline."""
        from apps.tournaments.models.registration import Registration

        config = tournament.config or {}
        checkin = config.get("checkin", {})
        if checkin.get("is_open"):
            return {"error": "Check-in is still open. Close it before running auto-DQ."}

        not_checked_in = Registration.objects.filter(
            tournament=tournament,
            checked_in=False,
            status__in=["confirmed", "auto_approved", "pending"],
        )
        count = not_checked_in.count()
        not_checked_in.update(status="no_show")
        logger.info(f"Auto-DQ: {count} participants marked no-show in {tournament.slug}")
        return {"dq_count": count, "disqualified": count}

    @staticmethod
    def update_checkin_config(tournament: Tournament, data: dict) -> dict:
        """Update check-in configuration."""
        config = tournament.config or {}
        checkin = config.get("checkin", {})

        if "auto_dq" in data:
            checkin["auto_dq"] = bool(data["auto_dq"])
        if "per_round" in data:
            checkin["per_round"] = bool(data["per_round"])
        if "window_minutes" in data:
            checkin["window_minutes"] = int(data["window_minutes"])

        config["checkin"] = checkin
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"config": checkin}

    @staticmethod
    def blast_reminder(tournament: Tournament) -> dict:
        """Send a check-in reminder to all participants who haven't checked in yet."""
        from apps.tournaments.models.registration import Registration

        pending_regs = Registration.objects.filter(
            tournament=tournament,
            checked_in=False,
            status__in=["confirmed", "auto_approved", "pending"],
        ).select_related("user")

        count = pending_regs.count()
        if count == 0:
            return {"sent": 0, "message": "Everyone has already checked in!"}

        # Build recipient IDs
        user_ids = list(pending_regs.values_list("user_id", flat=True).distinct())

        # Fire via notifications service
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "checkin_reminder")
        except Exception:
            pass

        # Discord blast
        try:
            from apps.tournaments.services.discord_webhook import DiscordWebhookService
            DiscordWebhookService.send_event(tournament, "checkin_reminder", {
                "tournament_name": tournament.name,
                "pending_count": count,
            })
        except Exception:
            pass

        logger.info(f"Blast reminder sent to {count} pending check-in participants in {tournament.slug}")
        return {"sent": count, "user_ids": user_ids, "message": f"Reminder sent to {count} participants"}

    @staticmethod
    def get_checkin_stats(tournament: Tournament) -> dict:
        """Analytics for check-in performance."""
        from apps.tournaments.models.registration import Registration
        qs = Registration.objects.filter(tournament=tournament)

        total = qs.filter(status__in=["confirmed", "auto_approved", "pending"]).count()
        checked_in = qs.filter(checked_in=True).count()
        no_show_count = qs.filter(status="no_show").count()

        # Avg time to check-in
        checked = qs.filter(checked_in=True, checked_in_at__isnull=False)
        avg_time = None
        if checked.exists():
            config = tournament.config or {}
            opened_at = config.get("checkin", {}).get("opened_at")
            if opened_at:
                from django.utils.dateparse import parse_datetime
                opened_dt = parse_datetime(opened_at)
                if opened_dt:
                    total_seconds = 0
                    count = 0
                    for r in checked.values("checked_in_at"):
                        if r["checked_in_at"] and r["checked_in_at"] > opened_dt:
                            total_seconds += (r["checked_in_at"] - opened_dt).total_seconds()
                            count += 1
                    if count > 0:
                        avg_time = round(total_seconds / count)

        return {
            "total_eligible": total,
            "checked_in": checked_in,
            "missed": total - checked_in,
            "no_show": no_show_count,
            "pct": round(checked_in / total * 100) if total > 0 else 0,
            "avg_checkin_seconds": avg_time,
        }
