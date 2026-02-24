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

    # ── Bracket generation / management ────────────────────────

    @staticmethod
    def generate_bracket(tournament, user) -> Dict[str, Any]:
        """Generate bracket from confirmed registrations + seeding."""
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=tournament.id,
            requested_by=user,
        )
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

        return {
            "exists": True,
            "bracket": TOCBracketsService._serialize_bracket(bracket),
            "visualization": viz,
            "nodes": [TOCBracketsService._serialize_node(n) for n in nodes],
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

        groups = Group.objects.filter(tournament=tournament).order_by(
            "display_order"
        )
        result_groups = []
        for g in groups:
            standings = GroupStanding.objects.filter(group=g).order_by("rank")
            result_groups.append({
                "id": str(g.id),
                "name": g.name,
                "display_order": g.display_order,
                "max_participants": g.max_participants,
                "advancement_count": g.advancement_count,
                "is_finalized": g.is_finalized,
                "standings": [
                    TOCBracketsService._serialize_standing(s) for s in standings
                ],
            })

        return {
            "exists": True,
            "stage": {
                "id": str(stage.id),
                "name": stage.name,
                "num_groups": stage.num_groups,
                "group_size": stage.group_size,
                "format": stage.format,
                "state": stage.state,
                "advancement_count_per_group": stage.advancement_count_per_group,
            },
            "groups": result_groups,
        }

    @staticmethod
    def configure_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Configure group stage settings."""
        stage = GroupStageService.configure_groups(
            tournament_id=tournament.id,
            num_groups=data.get("num_groups", 4),
            group_size=data.get("group_size", 4),
            format_type=data.get("format", "round_robin"),
            advancement_count=data.get("advancement_count", 2),
        )
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def draw_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Execute group draw."""
        draw_method = data.get("method", "random")
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("Configure groups first.")

        GroupStageService.draw_groups(
            stage_id=stage.id,
            draw_method=draw_method,
        )
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def get_group_standings(tournament) -> Dict[str, Any]:
        """Get all group standings."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            return {"groups": []}
        try:
            standings = GroupStageService.calculate_group_standings(stage.id)
        except Exception:
            standings = {}
        return {"groups": standings}

    # ── Schedule ──────────────────────────────────────────────

    @staticmethod
    def get_schedule(tournament) -> Dict[str, Any]:
        """Full schedule: all matches with times, stations, status."""
        matches = (
            Match.objects.filter(tournament=tournament)
            .select_related("bracket")
            .order_by("scheduled_time", "round_number", "match_number")
        )

        rounds = {}
        for m in matches:
            rn = m.round_number or 0
            if rn not in rounds:
                rounds[rn] = []
            rounds[rn].append(TOCBracketsService._serialize_match_schedule(m))

        return {
            "total_matches": matches.count(),
            "rounds": [
                {"round": rn, "matches": ms}
                for rn, ms in sorted(rounds.items())
            ],
        }

    @staticmethod
    def auto_schedule(tournament, data: Dict, user) -> Dict[str, Any]:
        """Auto-schedule matches with given parameters."""
        from datetime import timedelta

        start_time = data.get("start_time")
        match_duration = int(data.get("match_duration_minutes", 30))
        break_between = int(data.get("break_minutes", 10))
        max_concurrent = int(data.get("max_concurrent", 1))
        round_filter = data.get("round_number")

        matches = Match.objects.filter(
            tournament=tournament, state="scheduled"
        ).order_by("round_number", "match_number")

        if round_filter is not None:
            matches = matches.filter(round_number=round_filter)

        if start_time:
            from django.utils.dateparse import parse_datetime
            current_time = parse_datetime(start_time)
            if not current_time:
                current_time = timezone.now()
        else:
            current_time = timezone.now()

        slot_counter = 0
        scheduled = 0
        delta = timedelta(minutes=match_duration + break_between)

        for match in matches:
            match.scheduled_time = current_time
            match.save(update_fields=["scheduled_time"])
            scheduled += 1
            slot_counter += 1
            if slot_counter >= max_concurrent:
                current_time += delta
                slot_counter = 0

        return {"scheduled": scheduled, "message": f"{scheduled} matches scheduled"}

    @staticmethod
    def bulk_shift(tournament, data: Dict, user) -> Dict[str, Any]:
        """Bulk shift match times by a delta."""
        from datetime import timedelta

        shift_minutes = int(data.get("shift_minutes", 0))
        round_number = data.get("round_number")

        if shift_minutes == 0:
            raise ValueError("shift_minutes must be non-zero.")

        matches = Match.objects.filter(
            tournament=tournament,
            scheduled_time__isnull=False,
        )
        if round_number is not None:
            matches = matches.filter(round_number=round_number)

        delta = timedelta(minutes=shift_minutes)
        count = 0
        for m in matches:
            m.scheduled_time = m.scheduled_time + delta
            m.save(update_fields=["scheduled_time"])
            count += 1

        return {"shifted": count, "delta_minutes": shift_minutes}

    @staticmethod
    def add_break(tournament, data: Dict, user) -> Dict[str, Any]:
        """Insert a break after a specific round — shifts subsequent matches."""
        from datetime import timedelta

        after_round = int(data.get("after_round", 1))
        break_minutes = int(data.get("break_minutes", 15))
        label = data.get("label", "Break")

        matches = Match.objects.filter(
            tournament=tournament,
            round_number__gt=after_round,
            scheduled_time__isnull=False,
        )
        delta = timedelta(minutes=break_minutes)
        count = 0
        for m in matches:
            m.scheduled_time = m.scheduled_time + delta
            m.save(update_fields=["scheduled_time"])
            count += 1

        return {
            "label": label,
            "after_round": after_round,
            "break_minutes": break_minutes,
            "matches_shifted": count,
        }

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
    def _serialize_node(node) -> Dict:
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
            }
        return {
            "id": node.id,
            "position": node.position,
            "round_number": node.round_number,
            "match_number": node.match_number_in_round,
            "bracket_type": node.bracket_type,
            "participant1_id": node.participant1_id,
            "participant1_name": node.participant1_name,
            "participant2_id": node.participant2_id,
            "participant2_name": node.participant2_name,
            "winner_id": node.winner_id,
            "is_bye": node.is_bye,
            "match": match_data,
        }

    @staticmethod
    def _serialize_standing(s) -> Dict:
        return {
            "id": s.id,
            "rank": s.rank,
            "team_id": s.team_id,
            "user_id": s.user_id if hasattr(s, "user_id") else None,
            "matches_played": s.matches_played,
            "wins": s.matches_won,
            "draws": s.matches_drawn,
            "losses": s.matches_lost,
            "points": s.points,
            "goals_for": s.goals_for,
            "goals_against": s.goals_against,
            "goal_difference": s.goals_difference,
            "is_advancing": s.is_advancing,
            "is_eliminated": s.is_eliminated,
        }

    @staticmethod
    def _serialize_match_schedule(m) -> Dict:
        return {
            "id": m.id,
            "round_number": m.round_number,
            "match_number": m.match_number,
            "participant1_name": m.participant1_name,
            "participant2_name": m.participant2_name,
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
