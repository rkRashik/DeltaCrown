"""
Battle Royale Scoring Service.

Aggregates per-lobby placement + kills into the global Leaderboard
(GroupStanding rows under the single "Leaderboard" Group created by
``BattleRoyaleStrategy.generate_fixtures``).

Match.lobby_info  = {'br_session': True, 'session_number': N, 'map_name': '...'}
Match.game_scores = {'br_results': [
    {'participant_id': X, 'placement': 1, 'kills': 12},
    {'participant_id': Y, 'placement': 2, 'kills': 8},
    ...
]}

After ``apply_lobby_results(match)`` runs:
    - Match.state         → COMPLETED
    - Match.completed_at  → now
    - Match.winner_id     → participant who placed #1 in this lobby
    - GroupStanding rows updated:
        matches_played    +=1 per participating team
        placement_points  += matrix[placement] (default 0 outside the table)
        total_kills       += kills
        points            = placement_points + total_kills * kill_points
        average_placement = sum(placements) / matches_played

Tiebreakers are stored in ``Group.config['tiebreaker_rules']`` and
applied by TOCStandingsService when sorting.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class BRScoringService:
    """Service for applying Battle Royale lobby results to a leaderboard."""

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_scoring_matrix(group) -> Dict[str, Any]:
        """Return scoring matrix for a Group, or sensible defaults."""
        cfg = group.config if isinstance(group.config, dict) else {}
        matrix = cfg.get('scoring_matrix') or {}
        if not isinstance(matrix, dict):
            matrix = {}
        # Defensive defaults
        if 'placement_points' not in matrix or not isinstance(matrix['placement_points'], dict):
            matrix['placement_points'] = {
                '1': 15, '2': 12, '3': 10, '4': 8, '5': 6,
                '6': 4, '7': 2, '8': 1,
            }
        if 'kill_points' not in matrix:
            matrix['kill_points'] = 1
        return matrix

    @staticmethod
    def _placement_pts(matrix: Dict[str, Any], placement: int) -> int:
        """Look up placement points for a given finish position. 0 outside the table."""
        table = matrix.get('placement_points') or {}
        # Keys may be strings or ints depending on JSON round-trip
        return int(table.get(str(placement), table.get(placement, 0)) or 0)

    # ── Validation ───────────────────────────────────────────────────────────

    @staticmethod
    def validate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and normalize a list of result rows.

        Each row must have:
            participant_id  : int
            placement       : int >= 1
            kills           : int >= 0  (default 0)
        """
        if not isinstance(results, list) or not results:
            raise ValidationError("results must be a non-empty list of result rows.")

        cleaned: List[Dict[str, Any]] = []
        seen_pids = set()
        seen_placements = []
        for idx, row in enumerate(results):
            if not isinstance(row, dict):
                raise ValidationError(f"Result row {idx} must be an object.")
            try:
                pid = int(row.get('participant_id'))
            except (TypeError, ValueError):
                raise ValidationError(f"Result row {idx} has invalid participant_id.")
            try:
                placement = int(row.get('placement'))
            except (TypeError, ValueError):
                raise ValidationError(f"Result row {idx} has invalid placement.")
            if placement < 1:
                raise ValidationError(f"Result row {idx}: placement must be >= 1.")
            try:
                kills = int(row.get('kills') or 0)
            except (TypeError, ValueError):
                raise ValidationError(f"Result row {idx} has invalid kills.")
            if kills < 0:
                raise ValidationError(f"Result row {idx}: kills cannot be negative.")
            if pid in seen_pids:
                raise ValidationError(f"Duplicate participant_id={pid} in results.")
            seen_pids.add(pid)
            seen_placements.append(placement)
            cleaned.append({'participant_id': pid, 'placement': placement, 'kills': kills})

        # Soft check: placements should be roughly contiguous from 1
        if 1 not in seen_placements:
            logger.warning("BR lobby results submitted without a 1st-place entry.")
        return cleaned

    # ── Apply / Recalculate ──────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def apply_lobby_results(match, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply per-team placement + kills for a single lobby session.

        Side effects:
            * Updates Match.state, completed_at, winner_id, game_scores
            * Recalculates the Leaderboard's GroupStanding rows from scratch
              by replaying every COMPLETED lobby in the tournament. This is
              O(L * P) where L = lobby count and P = participants — cheap for
              typical BR (L ≤ 50, P ≤ 100), and avoids drift from partial
              updates.

        Returns:
            stats dict with summary counts.
        """
        from apps.tournaments.models.match import Match
        from apps.tournaments.models.group import Group, GroupStanding

        cleaned = BRScoringService.validate_results(results)

        # Resolve the Leaderboard group for this tournament.
        group = (
            Group.objects.filter(tournament=match.tournament, is_deleted=False)
            .order_by('display_order', 'id')
            .first()
        )
        if not group:
            raise ValidationError(
                "No Leaderboard group exists for this tournament. "
                "Generate lobby sessions first."
            )

        # Cross-check: every participant_id must exist in the leaderboard.
        valid_pids = set(
            GroupStanding.objects.filter(group=group, is_deleted=False)
            .values_list('team_id', flat=True)
        ) | set(
            GroupStanding.objects.filter(group=group, is_deleted=False)
            .values_list('user_id', flat=True)
        )
        valid_pids.discard(None)
        for row in cleaned:
            if row['participant_id'] not in valid_pids:
                raise ValidationError(
                    f"participant_id={row['participant_id']} is not on the "
                    f"leaderboard for this tournament."
                )

        # Persist results onto the match.
        match.game_scores = {'br_results': cleaned}
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        # Winner = #1 placement
        winner_row = next((r for r in cleaned if r['placement'] == 1), None)
        if winner_row:
            match.winner_id = winner_row['participant_id']
        match.save(update_fields=['game_scores', 'state', 'completed_at', 'winner_id'])

        # Replay all COMPLETED lobbies and recompute the leaderboard from zero.
        BRScoringService.recalculate_leaderboard(match.tournament_id)

        return {
            'status': 'applied',
            'match_id': match.id,
            'session_number': (match.lobby_info or {}).get('session_number'),
            'rows_applied': len(cleaned),
            'winner_id': match.winner_id,
        }

    @staticmethod
    @transaction.atomic
    def recalculate_leaderboard(tournament_id: int) -> Dict[str, Any]:
        """Replay every completed lobby and recompute every GroupStanding row."""
        from apps.tournaments.models.match import Match
        from apps.tournaments.models.group import Group, GroupStanding

        group = (
            Group.objects.filter(tournament_id=tournament_id, is_deleted=False)
            .order_by('display_order', 'id')
            .first()
        )
        if not group:
            return {'status': 'noop', 'reason': 'no_leaderboard_group'}

        matrix = BRScoringService._get_scoring_matrix(group)
        kill_points = int(matrix.get('kill_points') or 1)

        # Reset all standings under this group.
        standings = list(GroupStanding.objects.filter(group=group, is_deleted=False))
        agg: Dict[int, Dict[str, Any]] = {}
        for s in standings:
            pid = s.team_id or s.user_id
            if pid is None:
                continue
            agg[pid] = {
                'standing':         s,
                'matches_played':   0,
                'placement_points': 0,
                'total_kills':      0,
                'placements':       [],
                'wins':             0,
            }

        # Replay completed BR lobbies.
        completed_lobbies = Match.objects.filter(
            tournament_id=tournament_id,
            bracket__isnull=True,
            is_deleted=False,
            state__in=[Match.COMPLETED, Match.FORFEIT],
        )
        replay_count = 0
        for m in completed_lobbies:
            info = m.lobby_info or {}
            if not info.get('br_session'):
                continue
            scores = m.game_scores or {}
            rows = scores.get('br_results') or []
            if not isinstance(rows, list):
                continue
            replay_count += 1
            for row in rows:
                pid = int(row.get('participant_id') or 0)
                if pid not in agg:
                    continue
                placement = int(row.get('placement') or 99)
                kills = int(row.get('kills') or 0)
                pts = BRScoringService._placement_pts(matrix, placement)
                agg[pid]['matches_played']   += 1
                agg[pid]['placement_points'] += pts
                agg[pid]['total_kills']      += kills
                agg[pid]['placements'].append(placement)
                if placement == 1:
                    agg[pid]['wins'] += 1

        # Persist computed totals onto each GroupStanding.
        for pid, data in agg.items():
            s = data['standing']
            mp = data['matches_played']
            avg_p = (sum(data['placements']) / mp) if mp else 0
            s.matches_played   = mp
            s.placement_points = data['placement_points']
            s.total_kills      = data['total_kills']
            s.matches_won      = data['wins']  # using 1st-place finishes as "wins"
            s.matches_lost     = max(0, mp - data['wins'])
            s.average_placement = Decimal(str(round(avg_p, 2))) if mp else Decimal("0.00")
            # Total points = placement_pts + kills * kill_points
            s.points = data['placement_points'] + data['total_kills'] * kill_points
            s.total_score = s.points
            s.save(update_fields=[
                'matches_played', 'placement_points', 'total_kills',
                'matches_won', 'matches_lost', 'average_placement',
                'points', 'total_score',
            ])

        # Re-rank: highest points first, then placement_points, total_kills,
        # then average_placement (lower is better).
        ordered = sorted(
            agg.values(),
            key=lambda d: (
                -d['standing'].points,
                -d['placement_points'],
                -d['total_kills'],
                # Average placement: convert None/0 to large number so they sort last
                float(d['standing'].average_placement or 99),
            ),
        )
        for rank, data in enumerate(ordered, start=1):
            s = data['standing']
            if s.rank != rank:
                s.rank = rank
                s.save(update_fields=['rank'])

        # Bust standings cache so TOC + HUB pick up fresh data.
        try:
            from apps.tournaments.api.toc.cache_utils import bump_toc_scope
            bump_toc_scope('standings', tournament_id)
            bump_toc_scope('overview', tournament_id)
        except Exception:
            pass

        logger.info(
            "BRScoringService.recalculate_leaderboard tournament=%s replayed=%d "
            "participants=%d",
            tournament_id, replay_count, len(agg),
        )
        return {
            'status':       'recalculated',
            'replayed':     replay_count,
            'participants': len(agg),
        }
