"""
TOC Brackets & Competition Engine Service — Sprint 5

Wraps BracketService, GroupStageService, and BracketEditorService
to provide TOC-level bracket operations.
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.tournaments.models import (
    Bracket,
    BracketNode,
    Group,
    GroupStage,
    GroupStanding,
    Match,
    Registration,
    TournamentStage,
)
from apps.tournaments.models.qualifier_pipeline import (
    PipelineStage,
    PromotionRule,
    QualifierPipeline,
)
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.group_stage_service import GroupStageService

logger = logging.getLogger(__name__)


class TOCBracketsService:
    """TOC-level bracket, group-stage, and qualifier operations."""

    @staticmethod
    def _coerce_group_id(raw_group_id: Any) -> Optional[int]:
        """Normalize group_id from JSON payloads to int when possible."""
        if raw_group_id is None:
            return None
        try:
            return int(raw_group_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _group_stage_match_stats(tournament, group_ids: set[int]) -> Dict[int, Dict[str, int]]:
        """Return per-group totals for bracket-less matches that are tagged with lobby_info.group_id."""
        stats = {
            gid: {"total": 0, "completed": 0}
            for gid in group_ids
        }
        if not group_ids:
            return stats

        matches = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).only("id", "state", "lobby_info")

        for match in matches.iterator():
            group_id = TOCBracketsService._coerce_group_id((match.lobby_info or {}).get("group_id"))
            if group_id not in stats:
                continue
            stats[group_id]["total"] += 1
            if match.state in (Match.COMPLETED, Match.FORFEIT):
                stats[group_id]["completed"] += 1

        return stats

    @staticmethod
    def _group_stage_match_ids(tournament, group_ids: set[int]) -> List[int]:
        """Collect IDs of bracket-less matches that belong to the given groups via lobby_info.group_id."""
        if not group_ids:
            return []

        ids: List[int] = []
        matches = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).only("id", "lobby_info")

        for match in matches.iterator():
            group_id = TOCBracketsService._coerce_group_id((match.lobby_info or {}).get("group_id"))
            if group_id in group_ids:
                ids.append(match.id)

        return ids

    # ── Bracket generation / management ────────────────────────

    @staticmethod
    def generate_bracket(tournament, user) -> Dict[str, Any]:
        """Generate bracket from confirmed registrations + seeding.

        Sprint 29: Added re-generation guard — prevents accidental
        destruction of an existing bracket. Must reset first.
        """
        existing = Bracket.objects.filter(tournament=tournament).first()
        if existing:
            raise ValueError(
                "A bracket already exists. Reset the current bracket "
                "before generating a new one."
            )
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=tournament.id,
        )
        # Fire auto-notification for bracket generation
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "bracket_generated")
        except Exception:
            pass
        return TOCBracketsService._serialize_bracket(bracket)

    @staticmethod
    def reset_bracket(tournament, user) -> Dict[str, Any]:
        """Reset bracket — deletes existing and regenerates."""
        # Delete existing bracket + matches
        Bracket.objects.filter(tournament=tournament).delete()
        Match.objects.filter(
            tournament=tournament, bracket__isnull=False
        ).delete()
        return {"status": "reset", "message": "Bracket reset. Generate a new one."}

    @staticmethod
    def publish_bracket(tournament, user) -> Dict[str, Any]:
        """Finalize and publish bracket to participants."""
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            raise ValueError("No bracket to publish.")
        if bracket.is_finalized:
            raise ValueError("Bracket already published.")
        bracket = BracketService.finalize_bracket(
            bracket_id=bracket.id, finalized_by=user
        )
        # Fire auto-notification for bracket publication
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "bracket_published")
        except Exception:
            pass
        return TOCBracketsService._serialize_bracket(bracket)

    @staticmethod
    def get_bracket(tournament) -> Dict[str, Any]:
        """Current bracket state as tree structure."""
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            return {"exists": False, "bracket": None, "nodes": []}

        try:
            viz = BracketService.get_bracket_visualization_data(bracket.id)
        except Exception:
            viz = {}

        nodes = BracketNode.objects.filter(bracket=bracket).select_related(
            "match"
        ).order_by("round_number", "match_number_in_round")

        # Batch-resolve team names & logos for all participant IDs in nodes
        is_team = tournament.participation_type != 'solo'
        team_map = {}
        if is_team:
            participant_ids = set()
            for n in nodes:
                if n.participant1_id:
                    participant_ids.add(n.participant1_id)
                if n.participant2_id:
                    participant_ids.add(n.participant2_id)
            if participant_ids:
                try:
                    from apps.organizations.models.team import Team as OrgTeam
                    teams = OrgTeam.objects.filter(
                        id__in=participant_ids
                    ).select_related('organization')
                    for t in teams:
                        logo_url = ''
                        try:
                            if t.logo:
                                logo_url = t.logo.url
                            elif t.organization and getattr(t.organization, 'enforce_brand', False) and getattr(t.organization, 'logo', None):
                                logo_url = t.organization.logo.url
                        except (ValueError, Exception):
                            pass
                        team_map[t.id] = {
                            'name': t.name,
                            'tag': t.tag or '',
                            'logo_url': logo_url,
                        }
                except Exception:
                    pass

        # For double elimination, annotate GF / GFR nodes so the frontend
        # can render them with special labels and visual treatment.
        is_double_elim = (bracket.format == Bracket.DOUBLE_ELIMINATION)
        gf_round = gfr_round = None
        if is_double_elim:
            bstruct = bracket.bracket_structure or {}
            wb_rounds = bstruct.get("wb_rounds", 0)
            if wb_rounds:
                gf_round = wb_rounds + 1
                gfr_round = wb_rounds + 2

        def _annotate(n):
            data = TOCBracketsService._serialize_node(n, team_map=team_map, is_team=is_team)
            if gf_round and n.bracket_type == BracketNode.MAIN:
                data["is_gf"] = n.round_number == gf_round
                data["is_gf_reset"] = n.round_number == gfr_round
            else:
                data["is_gf"] = False
                data["is_gf_reset"] = False
            return data

        return {
            "exists": True,
            "bracket": TOCBracketsService._serialize_bracket(bracket),
            "visualization": viz,
            "nodes": [_annotate(n) for n in nodes],
        }

    @staticmethod
    def reorder_seeds(tournament, seeds: List[Dict], user) -> Dict[str, Any]:
        """Reorder seeding — expects [{registration_id, seed}] list."""
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            raise ValueError("No bracket exists. Generate first.")
        if bracket.is_finalized:
            raise ValueError("Cannot reorder seeds on a published bracket.")

        seed_map = {s["registration_id"]: s["seed"] for s in seeds}
        BracketService.apply_seeding(
            tournament_id=tournament.id,
            seeding_map=seed_map,
        )
        return {"status": "reordered", "count": len(seeds)}

    # ── Group Stage ────────────────────────────────────────────

    @staticmethod
    def get_groups(tournament) -> Dict[str, Any]:
        """Get group stage configuration and groups."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            return {"exists": False, "stage": None, "groups": []}

        groups = list(Group.objects.filter(
            tournament=tournament, is_deleted=False
        ).order_by("display_order"))
        group_ids = {g.id for g in groups}
        match_stats = TOCBracketsService._group_stage_match_stats(tournament, group_ids)

        result_groups = []
        total_matches = 0
        total_completed = 0
        has_drawn_assignments = False
        for g in groups:
            standings = GroupStanding.objects.filter(
                group=g, is_deleted=False
            ).order_by("rank")
            if standings.exists():
                has_drawn_assignments = True

            g_stats = match_stats.get(g.id, {"total": 0, "completed": 0})
            g_total = int(g_stats.get("total") or 0)
            g_completed = int(g_stats.get("completed") or 0)
            is_completed = g_total > 0 and g_completed == g_total
            total_matches += g_total
            total_completed += g_completed

            result_groups.append({
                "id": str(g.id),
                "name": g.name,
                "display_order": g.display_order,
                "max_participants": g.max_participants,
                "advancement_count": g.advancement_count,
                "is_finalized": is_completed,
                "is_drawn": g.is_finalized,
                "matches_total": g_total,
                "matches_completed": g_completed,
                "standings": [
                    TOCBracketsService._serialize_standing(s) for s in standings
                ],
            })

        stage_state = stage.state
        # Backfill draw state if standings exist but stage flag is stale (e.g. legacy/live-draw flows).
        if stage_state not in ("active", "completed") and has_drawn_assignments:
            stage_state = "active"

        return {
            "exists": True,
            "stage": {
                "id": str(stage.id),
                "name": stage.name,
                "num_groups": stage.num_groups,
                "group_size": stage.group_size,
                "format": stage.format,
                "state": stage_state,
                "advancement_count_per_group": stage.advancement_count_per_group,
                "draw_audit": (stage.config or {}).get("draw_audit"),
                "matches_total": total_matches,
                "matches_completed": total_completed,
            },
            "matches_total": total_matches,
            "matches_completed": total_completed,
            "groups": result_groups,
        }

    @staticmethod
    def configure_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Configure group stage settings."""
        num_groups = data.get("num_groups", 4)
        group_size = data.get("group_size", 4)
        match_format = data.get("format", "round_robin")
        advancement_count = data.get("advancement_count", 2)

        groups = GroupStageService.configure_groups(
            tournament_id=tournament.id,
            num_groups=num_groups,
            match_format=match_format,
            advancement_count=advancement_count,
        )

        # Create or update GroupStage record (the TOC UI queries this)
        stage, _ = GroupStage.objects.update_or_create(
            tournament=tournament,
            defaults={
                'name': 'Group Stage',
                'num_groups': num_groups,
                'group_size': group_size,
                'format': match_format,
                'state': 'pending',
                'advancement_count_per_group': advancement_count,
            }
        )
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def draw_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Execute group draw.

        Sprint 29: Added re-draw guard — prevents accidental
        destruction of already-drawn groups.
        """
        draw_method = data.get("method", "random")
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("Configure groups first.")
        if stage.state in ('active', 'completed'):
            raise ValueError(
                "Groups have already been drawn (stage is "
                f"'{stage.state}'). Reset the group stage before "
                "re-drawing."
            )

        GroupStageService.draw_groups(
            tournament_id=tournament.id,
            draw_method=draw_method,
        )
        # Update stage state
        stage.state = 'active'
        stage.save(update_fields=['state'])
        # Fire auto-notification for group draw completion
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "group_draw_complete")
        except Exception:
            pass
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def generate_group_matches(tournament, data: Dict, user) -> Dict[str, Any]:
        """Generate round-robin matches for drawn groups."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("Configure groups first.")

        groups_snapshot = TOCBracketsService.get_groups(tournament)
        groups = groups_snapshot.get("groups", [])
        if not groups:
            raise ValueError("No groups configured.")

        stage_snapshot = groups_snapshot.get("stage") or {}
        stage_state = str(stage_snapshot.get("state") or stage.state or "").lower()
        has_drawn_assignments = any(bool(g.get("standings")) for g in groups)
        if stage_state not in ("active", "completed") and not has_drawn_assignments:
            raise ValueError("Draw groups first, then generate matches.")

        stage_group_ids = {
            TOCBracketsService._coerce_group_id(g.get("id"))
            for g in groups
            if g.get("id") is not None
        }
        stage_group_ids.discard(None)
        existing_group_match_ids = TOCBracketsService._group_stage_match_ids(tournament, stage_group_ids)
        existing_total = len(existing_group_match_ids)

        allow_regenerate = bool(data.get("allow_regenerate", False))
        if existing_total > 0:
            if not allow_regenerate:
                raise ValueError(
                    "Group matches already exist. Use Re-Generate Matches to replace the current schedule."
                )
            Match.objects.filter(id__in=existing_group_match_ids).delete()

        default_rounds = 2 if (stage.format or "").lower() == "double_round_robin" else 1
        rounds = int(data.get("rounds") or default_rounds)
        if rounds not in (1, 2):
            raise ValueError("rounds must be 1 or 2.")

        generated = GroupStageService.generate_group_matches(stage.id, rounds=rounds)
        if generated <= 0:
            raise ValueError(
                "No matches were generated. Make sure groups are drawn and each group has at least 2 participants."
            )

        if stage.state != "active":
            stage.state = "active"
            stage.save(update_fields=["state"])

        return {
            "status": "generated",
            "generated_matches": generated,
            "rounds": rounds,
            "groups": TOCBracketsService.get_groups(tournament).get("groups", []),
        }

    @staticmethod
    def reset_groups(tournament, user) -> Dict[str, Any]:
        """Reset group draw — clears standings and returns stage to pending.

        Sprint 29: Allows re-drawing groups after reset.
        """
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("No group stage configured.")

        # Clear all standings
        GroupStanding.objects.filter(
            group__tournament=tournament,
        ).delete()

        # Reset group draw markers on active groups.
        Group.objects.filter(tournament=tournament, is_deleted=False).update(is_finalized=False)

        # Clear only generated group-stage matches tied to current groups.
        group_ids = set(
            Group.objects.filter(tournament=tournament, is_deleted=False).values_list("id", flat=True)
        )
        group_match_ids = TOCBracketsService._group_stage_match_ids(tournament, group_ids)
        if group_match_ids:
            Match.objects.filter(id__in=group_match_ids).delete()

        # Reset stage state
        stage.state = 'pending'
        stage.config = {
            k: v for k, v in (stage.config or {}).items()
            if k != 'draw_audit'
        }
        stage.save(update_fields=['state', 'config'])

        return {
            "status": "reset",
            "message": "Group draw reset. You can now re-draw.",
        }

    @staticmethod
    def get_group_standings(tournament) -> Dict[str, Any]:
        """Get all group standings."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            return {"groups": []}
        try:
            standings = GroupStageService.calculate_group_standings(stage.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"calculate_group_standings failed for stage {stage.id}: {e}"
            )
            standings = {}
        return {"groups": standings}

    # ── Schedule ──────────────────────────────────────────────

    @staticmethod
    def get_schedule(tournament) -> Dict[str, Any]:
        """
        Full schedule: all matches with times, stations, status,
        group names, conflict detection, and summary statistics.

        Sprint 27: Enhanced with conflict detection, group info,
        per-day breakdown, and estimated completion time.
        """
        matches_qs = (
            Match.objects.filter(tournament=tournament)
            .select_related("bracket")
            .order_by("scheduled_time", "round_number", "match_number")
        )
        matches = list(matches_qs)

        # ── Build group lookup (match → group name) ──
        group_lookup = {}
        try:
            standings = GroupStanding.objects.filter(
                group__tournament=tournament,
            ).select_related('group').only('team_id', 'group__name')
            for standing in standings:
                if standing.team_id:
                    group_lookup[standing.team_id] = standing.group.name
        except Exception:
            pass

        # ── Batch-resolve team names & logos ──
        is_team = tournament.participation_type != 'solo'
        team_map = {}
        if is_team:
            participant_ids = set()
            for m in matches:
                if m.participant1_id:
                    participant_ids.add(m.participant1_id)
                if m.participant2_id:
                    participant_ids.add(m.participant2_id)
            if participant_ids:
                try:
                    from apps.organizations.models.team import Team as OrgTeam
                    teams = OrgTeam.objects.filter(
                        id__in=participant_ids
                    ).select_related('organization')
                    for t in teams:
                        logo_url = ''
                        try:
                            if t.logo:
                                logo_url = t.logo.url
                            elif t.organization and getattr(t.organization, 'enforce_brand', False) and getattr(t.organization, 'logo', None):
                                logo_url = t.organization.logo.url
                        except (ValueError, Exception):
                            pass
                        team_map[t.id] = {
                            'name': t.name,
                            'tag': t.tag or '',
                            'logo_url': logo_url,
                        }
                except Exception:
                    pass

        # ── Serialize matches by round ──
        rounds = {}
        all_serialized = []
        for m in matches:
            rn = m.round_number or 0
            if rn not in rounds:
                rounds[rn] = []
            serialized = TOCBracketsService._serialize_match_schedule(
                m, team_map=team_map, is_team=is_team
            )
            # Attach group name from participant lookup
            gname = group_lookup.get(m.participant1_id) or group_lookup.get(m.participant2_id) or ""
            serialized["group_name"] = gname
            rounds[rn].append(serialized)
            all_serialized.append(serialized)

        # ── Conflict detection ──
        conflicts = TOCBracketsService._detect_schedule_conflicts(matches)

        # ── Summary statistics ──
        total = len(matches)
        scheduled = sum(1 for m in matches if m.state in ("scheduled", "check_in", "ready"))
        live = sum(1 for m in matches if m.state == "live")
        completed = sum(1 for m in matches if m.state in ("completed", "forfeit"))
        pending = sum(1 for m in matches if m.state == "pending_result")
        disputed = sum(1 for m in matches if m.state == "disputed")

        # Estimated end time (latest scheduled + 1h buffer)
        scheduled_times = [m.scheduled_time for m in matches if m.scheduled_time]
        est_end = None
        if scheduled_times:
            from datetime import timedelta
            est_end = (max(scheduled_times) + timedelta(hours=1)).isoformat()

        # Per-day breakdown
        day_counts = {}
        for m in matches:
            if m.scheduled_time:
                day_key = m.scheduled_time.strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + 1

        # Context flags so the frontend can show smarter empty states
        has_bracket = Bracket.objects.filter(tournament=tournament).exists()
        has_groups = Group.objects.filter(tournament=tournament, is_deleted=False).exists()

        return {
            "total_matches": total,
            "matches": all_serialized,
            "rounds": [
                {"round": rn, "matches": ms}
                for rn, ms in sorted(rounds.items())
            ],
            "summary": {
                "total": total,
                "total_matches": total,
                "scheduled": scheduled,
                "live": live,
                "completed": completed,
                "pending": pending,
                "disputed": disputed,
                "estimated_end": est_end,
                "conflicts": len(conflicts),
                "per_day": [
                    {"date": d, "count": c}
                    for d, c in sorted(day_counts.items())
                ],
            },
            "conflicts": conflicts,
            "context": {
                "has_bracket": has_bracket,
                "has_groups": has_groups,
            },
        }

    @staticmethod
    def auto_schedule(tournament, data: Dict, user) -> Dict[str, Any]:
        """
        Auto-schedule matches with smart defaults and round-aware boundaries.

        Parameters:
            start_time           — ISO datetime string
            match_duration_minutes — minutes per match (default 60)
            break_minutes        — break between matches (default 15)
            max_concurrent       — parallel matches per slot (default 1)
            round_break_minutes  — extra break between rounds (default 30)
            round_number         — only schedule this round (optional)
            reschedule_existing  — if True, reschedule already-scheduled matches too
        """
        from datetime import timedelta
        from django.utils.dateparse import parse_datetime

        start_time_str = data.get("start_time")
        match_duration = int(data.get("match_duration_minutes", 60))
        break_between = int(data.get("break_minutes", 15))
        max_concurrent = max(1, int(data.get("max_concurrent", 1)))
        round_break = int(data.get("round_break_minutes", 30))
        round_filter = data.get("round_number")
        reschedule_existing = data.get("reschedule_existing", False)

        # Parse start time with validation
        if start_time_str:
            current_time = parse_datetime(start_time_str)
            if not current_time:
                raise ValueError(f"Invalid start_time format: {start_time_str}. Use ISO 8601 (e.g., 2026-03-15T10:00:00Z).")
            if timezone.is_naive(current_time):
                from django.utils.timezone import make_aware
                current_time = make_aware(current_time)
        else:
            # Default: next full hour from now
            now = timezone.now()
            current_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # Query matches
        states = ["scheduled"]
        if reschedule_existing:
            states.extend(["check_in", "ready"])

        matches = Match.objects.filter(
            tournament=tournament, state__in=states
        ).order_by("round_number", "match_number")

        if round_filter is not None:
            matches = matches.filter(round_number=round_filter)

        if not matches.exists():
            return {"scheduled": 0, "message": "No matches to schedule. Generate brackets first."}

        match_delta = timedelta(minutes=match_duration + break_between)
        round_delta = timedelta(minutes=round_break)

        slot_counter = 0
        scheduled = 0
        prev_round = None
        round_starts = {}

        for match in matches:
            # Add round break when transitioning to a new round
            if prev_round is not None and match.round_number != prev_round:
                # Finish current slot row
                if slot_counter > 0:
                    current_time += match_delta
                    slot_counter = 0
                # Add round break
                current_time += round_delta
                round_starts[match.round_number] = current_time.isoformat()

            if prev_round is None:
                round_starts[match.round_number] = current_time.isoformat()

            match.scheduled_time = current_time
            match.save(update_fields=["scheduled_time"])
            scheduled += 1
            slot_counter += 1

            if slot_counter >= max_concurrent:
                current_time += match_delta
                slot_counter = 0

            prev_round = match.round_number

        # Compute estimated end
        est_end = current_time + timedelta(minutes=match_duration)

        return {
            "scheduled": scheduled,
            "start_time": round_starts.get(min(round_starts.keys())) if round_starts else None,
            "estimated_end": est_end.isoformat(),
            "round_starts": round_starts,
            "message": f"{scheduled} matches scheduled across {len(round_starts)} round(s).",
        }

    @staticmethod
    def manual_schedule_match(tournament, match_id: int, data: Dict, user) -> Dict[str, Any]:
        """
        Manually schedule a single match — sets time + optional check-in deadline.
        Sprint 27: Distinct from reschedule (no state restriction for unscheduled matches).
        """
        from datetime import timedelta
        from django.utils.dateparse import parse_datetime

        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            raise ValueError("Match not found.")

        new_time_str = data.get("scheduled_time")
        if not new_time_str:
            raise ValueError("scheduled_time is required.")

        new_time = parse_datetime(new_time_str)
        if not new_time:
            raise ValueError("Invalid datetime format.")

        if timezone.is_naive(new_time):
            from django.utils.timezone import make_aware
            new_time = make_aware(new_time)

        match.scheduled_time = new_time

        # Optionally set check-in deadline (e.g., 15 min before)
        check_in_minutes = data.get("check_in_minutes")
        if check_in_minutes and int(check_in_minutes) > 0:
            match.check_in_deadline = new_time - timedelta(minutes=int(check_in_minutes))

        match.save(update_fields=["scheduled_time", "check_in_deadline"])

        return {
            "match_id": match.id,
            "scheduled_time": new_time.isoformat(),
            "check_in_deadline": match.check_in_deadline.isoformat() if match.check_in_deadline else None,
            "message": f"Match #{match.match_number} (R{match.round_number}) scheduled.",
        }

    @staticmethod
    def bulk_shift(tournament, data: Dict, user) -> Dict[str, Any]:
        """Bulk shift match times by a delta. Uses single SQL UPDATE."""
        from datetime import timedelta
        from django.db.models import F

        shift_minutes = int(data.get("shift_minutes", 0))
        round_number = data.get("round_number")

        if shift_minutes == 0:
            raise ValueError("shift_minutes must be non-zero.")

        qs = Match.objects.filter(
            tournament=tournament,
            scheduled_time__isnull=False,
        )
        if round_number is not None:
            qs = qs.filter(round_number=round_number)

        delta = timedelta(minutes=shift_minutes)
        count = qs.update(scheduled_time=F('scheduled_time') + delta)

        return {"shifted": count, "delta_minutes": shift_minutes}

    @staticmethod
    def add_break(tournament, data: Dict, user) -> Dict[str, Any]:
        """Insert a break after a specific round — shifts subsequent matches. Single SQL UPDATE."""
        from datetime import timedelta
        from django.db.models import F

        after_round = int(data.get("after_round", 1))
        break_minutes = int(data.get("break_minutes", 15))
        label = data.get("label", "Break")

        delta = timedelta(minutes=break_minutes)
        count = Match.objects.filter(
            tournament=tournament,
            round_number__gt=after_round,
            scheduled_time__isnull=False,
        ).update(scheduled_time=F('scheduled_time') + delta)

        return {
            "label": label,
            "after_round": after_round,
            "break_minutes": break_minutes,
            "matches_shifted": count,
        }

    # ── Per-match reschedule ──────────────────────────────────

    @staticmethod
    def reschedule_match(tournament, match_id: int, data: Dict, user) -> Dict[str, Any]:
        """Reschedule a single match to a new time. Sprint 27."""
        from django.utils.dateparse import parse_datetime

        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            raise ValueError("Match not found.")

        if match.state in ("completed", "forfeit", "cancelled"):
            raise ValueError(f"Cannot reschedule a match in '{match.state}' state.")

        new_time_str = data.get("scheduled_time")
        if not new_time_str:
            raise ValueError("scheduled_time is required.")

        new_time = parse_datetime(new_time_str)
        if not new_time:
            raise ValueError("Invalid datetime format.")

        old_time = match.scheduled_time
        match.scheduled_time = new_time
        match.save(update_fields=["scheduled_time"])

        return {
            "match_id": match.id,
            "old_time": old_time.isoformat() if old_time else None,
            "new_time": new_time.isoformat(),
            "message": f"Match #{match.match_number} rescheduled.",
        }

    # ── Conflict detection helper ──────────────────────────────

    @staticmethod
    def _detect_schedule_conflicts(matches) -> List[Dict]:
        """
        Detect schedule conflicts where the same team appears in
        two overlapping time slots. Assumes ~60 min match duration.
        Sprint 27.
        """
        from datetime import timedelta

        DEFAULT_DURATION = timedelta(minutes=60)
        conflicts = []
        by_participant = {}

        for m in matches:
            if not m.scheduled_time:
                continue
            start = m.scheduled_time
            end = start + DEFAULT_DURATION
            for pid in [m.participant1_id, m.participant2_id]:
                if pid:
                    by_participant.setdefault(pid, []).append({
                        "match_id": m.id,
                        "match_number": m.match_number,
                        "round_number": m.round_number,
                        "start": start,
                        "end": end,
                    })

        seen_pairs = set()
        for participant_id, slots in by_participant.items():
            slots.sort(key=lambda s: s["start"])
            prev = None
            for current in slots:
                if prev is None:
                    prev = current
                    continue

                if prev["match_id"] != current["match_id"] and prev["end"] > current["start"]:
                    pair_key = tuple(sorted([prev["match_id"], current["match_id"]]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        conflicts.append({
                            "match_a": prev["match_id"],
                            "match_b": current["match_id"],
                            "participant_id": participant_id,
                            "overlap_start": max(prev["start"], current["start"]).isoformat(),
                            "overlap_end": min(prev["end"], current["end"]).isoformat(),
                        })

                # Keep the interval that extends furthest right for next overlap checks.
                if current["end"] > prev["end"]:
                    prev = current

        return conflicts

    # ── Qualifier Pipelines ────────────────────────────────────

    @staticmethod
    def list_pipelines(tournament) -> List[Dict]:
        """List qualifier pipelines for a tournament."""
        pipelines = QualifierPipeline.objects.filter(
            tournament=tournament
        ).prefetch_related("stages", "stages__promotion_rules_out")

        return [TOCBracketsService._serialize_pipeline(p) for p in pipelines]

    @staticmethod
    def create_pipeline(tournament, data: Dict, user) -> Dict:
        pipeline = QualifierPipeline.objects.create(
            tournament=tournament,
            name=data["name"],
            description=data.get("description", ""),
        )
        return TOCBracketsService._serialize_pipeline(pipeline)

    @staticmethod
    def update_pipeline(tournament, pipeline_id: str, data: Dict) -> Dict:
        pipeline = QualifierPipeline.objects.get(
            id=pipeline_id, tournament=tournament
        )
        for field in ("name", "description", "status"):
            if field in data:
                setattr(pipeline, field, data[field])
        pipeline.save()
        return TOCBracketsService._serialize_pipeline(pipeline)

    @staticmethod
    def delete_pipeline(tournament, pipeline_id: str):
        QualifierPipeline.objects.filter(
            id=pipeline_id, tournament=tournament
        ).delete()

    # ── Serializers ───────────────────────────────────────────

    @staticmethod
    def _serialize_bracket(bracket) -> Dict:
        return {
            "id": str(bracket.id) if hasattr(bracket.id, "hex") else bracket.id,
            "format": bracket.format,
            "total_rounds": bracket.total_rounds,
            "total_matches": bracket.total_matches,
            "seeding_method": bracket.seeding_method,
            "is_finalized": bracket.is_finalized,
            "generated_at": (
                bracket.generated_at.isoformat() if bracket.generated_at else None
            ),
        }

    @staticmethod
    def _serialize_node(node, team_map=None, is_team=False) -> Dict:
        match_data = None
        if node.match:
            match_data = {
                "id": node.match.id,
                "state": node.match.state,
                "participant1_score": node.match.participant1_score,
                "participant2_score": node.match.participant2_score,
                "winner_id": node.match.winner_id,
                "scheduled_time": (
                    node.match.scheduled_time.isoformat()
                    if node.match.scheduled_time
                    else None
                ),
                "best_of": getattr(node.match, "best_of", 1) or 1,
                "game_scores": TOCBracketsService._safe_game_scores(node.match),
            }

        # Resolve participant names & logos from team_map (overrides denormalized names)
        p1_name = node.participant1_name
        p2_name = node.participant2_name
        p1_logo = ''
        p2_logo = ''
        p1_tag = ''
        p2_tag = ''
        if is_team and team_map:
            if node.participant1_id and node.participant1_id in team_map:
                info = team_map[node.participant1_id]
                p1_name = info['name']
                p1_logo = info['logo_url']
                p1_tag = info['tag']
            if node.participant2_id and node.participant2_id in team_map:
                info = team_map[node.participant2_id]
                p2_name = info['name']
                p2_logo = info['logo_url']
                p2_tag = info['tag']

        return {
            "id": node.id,
            "position": node.position,
            "round_number": node.round_number,
            "match_number": node.match_number_in_round,
            "bracket_type": node.bracket_type,
            "participant1_id": node.participant1_id,
            "participant1_name": p1_name,
            "participant1_logo": p1_logo,
            "participant1_tag": p1_tag,
            "participant2_id": node.participant2_id,
            "participant2_name": p2_name,
            "participant2_logo": p2_logo,
            "participant2_tag": p2_tag,
            "winner_id": node.winner_id,
            "is_bye": node.is_bye,
            "match": match_data,
        }

    @staticmethod
    def _serialize_standing(s) -> Dict:
        # Sprint 29: Resolve team or user name via OrgTeam (not legacy Team stub)
        display_name = None
        if s.team_id:
            try:
                from apps.organizations.models.team import Team as OrgTeam
                team = OrgTeam.objects.filter(id=s.team_id).values_list('name', flat=True).first()
                display_name = team
            except Exception:
                pass
            if not display_name:
                # Fallback: check Registration for display_name_override
                try:
                    reg = Registration.objects.filter(
                        team_id=s.team_id,
                        tournament=s.group.tournament
                    ).values_list('display_name_override', flat=True).first()
                    display_name = reg
                except Exception:
                    pass
            if not display_name:
                display_name = f'Team {s.team_id}'
        elif hasattr(s, 'user') and s.user:
            display_name = s.user.get_display_name() if hasattr(s.user, 'get_display_name') else str(s.user)
        else:
            display_name = '—'

        return {
            "id": s.id,
            "rank": s.rank,
            "team_id": s.team_id,
            "team_name": display_name,
            "user_id": s.user_id if hasattr(s, "user_id") else None,
            "matches_played": s.matches_played,
            "wins": s.matches_won,
            "draws": s.matches_drawn,
            "losses": s.matches_lost,
            "points": float(s.points) if s.points else 0,
            "goals_for": s.goals_for,
            "goals_against": s.goals_against,
            "goal_difference": s.goal_difference,
            "is_advancing": s.is_advancing,
            "is_eliminated": s.is_eliminated,
        }

    @staticmethod
    def _safe_game_scores(m):
        """
        Always return a normalised list of game-score dicts for the frontend.
        The DB can store either:
          - A list of dicts: [{p1_score, p2_score, ...}]     (canonical)
          - A Valorant-style dict: {"maps": [{team1_rounds, team2_rounds, ...}]}
          - A JSON string of either shape
          - None
        Frontend expects:  [{p1_score: int, p2_score: int, map_name: str, ...}, ...]
        """
        import json as _json
        raw = getattr(m, 'game_scores', None)
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                raw = _json.loads(raw)
            except (ValueError, TypeError):
                return []
        # Dict with "maps" key → normalise to list
        if isinstance(raw, dict):
            maps = raw.get('maps', [])
            if not isinstance(maps, list):
                return []
            result = []
            for i, mp in enumerate(maps):
                result.append({
                    'game': i + 1,
                    'map_name': mp.get('map_name', ''),
                    'p1_score': mp.get('team1_rounds', 0),
                    'p2_score': mp.get('team2_rounds', 0),
                    'winner_side': mp.get('winner_side', 0),
                })
            return result
        if isinstance(raw, list):
            return raw
        return []

    @staticmethod
    def _serialize_match_schedule(m, team_map=None, is_team=False) -> Dict:
        p1_name = m.participant1_name
        p2_name = m.participant2_name
        p1_logo = ''
        p2_logo = ''
        if is_team and team_map:
            if m.participant1_id and m.participant1_id in team_map:
                p1_name = team_map[m.participant1_id]['name']
                p1_logo = team_map[m.participant1_id]['logo_url']
            if m.participant2_id and m.participant2_id in team_map:
                p2_name = team_map[m.participant2_id]['name']
                p2_logo = team_map[m.participant2_id]['logo_url']
        return {
            "id": m.id,
            "round_number": m.round_number,
            "match_number": m.match_number,
            "participant1_id": m.participant1_id,
            "participant1_name": p1_name,
            "participant1_logo": p1_logo,
            "participant2_id": m.participant2_id,
            "participant2_name": p2_name,
            "participant2_logo": p2_logo,
            "participant1_score": m.participant1_score,
            "participant2_score": m.participant2_score,
            "state": m.state,
            "winner_id": m.winner_id,
            "scheduled_time": (
                m.scheduled_time.isoformat() if m.scheduled_time else None
            ),
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "completed_at": (
                m.completed_at.isoformat() if m.completed_at else None
            ),
            "stream_url": m.stream_url or "",
            "best_of": getattr(m, 'best_of', 1) or 1,
            "game_scores": TOCBracketsService._safe_game_scores(m),
        }

    @staticmethod
    def _serialize_pipeline(pipeline) -> Dict:
        stages = []
        for s in pipeline.stages.all().order_by("order"):
            rules_out = []
            for r in s.promotion_rules_out.all():
                rules_out.append({
                    "id": str(r.id),
                    "to_stage_id": str(r.to_stage_id),
                    "criteria": r.criteria,
                    "value": r.value,
                    "auto_promote": r.auto_promote,
                })
            stages.append({
                "id": str(s.id),
                "name": s.name,
                "format": s.format,
                "max_teams": s.max_teams,
                "order": s.order,
                "tournament_stage_id": (
                    str(s.tournament_stage_id) if s.tournament_stage_id else None
                ),
                "promotion_rules": rules_out,
            })

        return {
            "id": str(pipeline.id),
            "name": pipeline.name,
            "description": pipeline.description,
            "status": pipeline.status,
            "stages": stages,
            "created_at": pipeline.created_at.isoformat(),
        }
