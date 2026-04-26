"""
Tournament Completion Truth — single source of truth for "is this tournament
over?" used by TOC, HUB, public detail, badges, and lifecycle steppers.

Why a separate module:
    * `Tournament.get_effective_status()` is correct, but it's a model method
      whose definition lives next to a hundred other fields — surfaces that
      need the *full* completion picture (winner names, runner-up, third,
      placements payload, whether post-finalization has already run) end up
      duplicating logic.
    * We need an idempotent "auto-converge" hook that every overview view can
      call on render: if the bracket is finished but `Tournament.status` has
      drifted to LIVE, run the post-finalization pipeline and proceed with the
      converged data. Page loads must never be blocked by service errors.

Public API:
    is_tournament_effectively_completed(tournament) -> bool
    get_tournament_completion_payload(tournament) -> dict
    ensure_post_finalization(tournament, *, actor=None) -> dict
        Convenience: detect-and-converge in one call, returns the payload.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── Truth predicate ─────────────────────────────────────────────────────────


def is_tournament_effectively_completed(tournament) -> bool:
    """
    Return True when the tournament should be treated as completed by every
    surface. The rule is intentionally permissive — better to render
    "Completed" once when the bracket is done than to render "Live" after
    the fact.

    Truth conditions (any one of):
      * Tournament.status is COMPLETED or ARCHIVED.
      * A non-deleted ``TournamentResult`` exists with a winner_id.

    Never raises — defensive defaults to False on any unexpected error.
    """
    try:
        status = (getattr(tournament, 'status', '') or '').lower()
        if status in ('completed', 'archived'):
            return True
    except Exception:
        return False

    try:
        from apps.tournaments.models.result import TournamentResult
        return TournamentResult.objects.filter(
            tournament_id=getattr(tournament, 'pk', None),
            is_deleted=False,
        ).exclude(winner_id__isnull=True).exists()
    except Exception:
        return False


# ── Completion payload ─────────────────────────────────────────────────────


def get_tournament_completion_payload(tournament) -> Dict[str, Any]:
    """
    Serializable snapshot suitable for templates / DRF responses.

    Returns:
        {
            'completed': bool,
            'has_winner': bool,
            'winner': {'team_name': str, 'registration_id': int} | None,
            'runner_up': {...} | None,
            'third_place': {...} | None,
            'fourth_place': {...} | None,
            'standings': [...],   # full final_standings (1..N)
            'top4': [...],
            'finalized': bool,    # standings persisted on TournamentResult
            'requires_review': bool,
        }

    Always returns a complete dict — never None.
    """
    completed = is_tournament_effectively_completed(tournament)
    payload: Dict[str, Any] = {
        'completed': completed,
        'has_winner': False,
        'winner': None,
        'runner_up': None,
        'third_place': None,
        'fourth_place': None,
        'standings': [],
        'top4': [],
        'finalized': False,
        'requires_review': False,
    }
    if not completed:
        return payload

    try:
        from apps.tournaments.services.placement_service import PlacementService
        snapshot = PlacementService.standings_payload(tournament) or {}
        payload['finalized'] = bool(snapshot.get('finalized'))
        payload['standings'] = snapshot.get('standings') or []
        payload['top4'] = snapshot.get('top4') or []
        payload['winner'] = snapshot.get('winner')
        payload['runner_up'] = snapshot.get('runner_up')
        payload['third_place'] = snapshot.get('third_place')
        payload['fourth_place'] = snapshot.get('fourth_place')
        payload['requires_review'] = bool(snapshot.get('requires_review'))
        payload['has_winner'] = bool(payload['winner'])
    except Exception:
        logger.warning(
            'completion_payload: PlacementService snapshot failed for %s',
            getattr(tournament, 'pk', '?'),
            exc_info=True,
        )
    return payload


# ── Auto-convergence ───────────────────────────────────────────────────────


def ensure_post_finalization(tournament, *, actor=None) -> Dict[str, Any]:
    """
    Idempotent detect-and-converge entry point for overview surfaces.

    Behaviour:
      1. If the tournament is not effectively completed, return an early
         payload (no convergence required).
      2. If the tournament is effectively completed but ``Tournament.status``
         is still LIVE *or* the post-finalization sentinel hasn't fired,
         run ``PostFinalizationService`` synchronously. The service is
         idempotent — calling it twice is safe.
      3. Always return a fresh ``completion_payload`` reflecting the converged
         state.

    Errors from the post-finalization service are logged but never raised —
    overview pages must continue rendering even if a downstream step fails.

    Returns:
        The completion payload (same shape as
        ``get_tournament_completion_payload``) plus a ``converged`` boolean
        that records whether this call actually triggered a service run.
    """
    payload = get_tournament_completion_payload(tournament)
    payload['converged'] = False
    if not payload['completed']:
        return payload

    needs_convergence = False
    try:
        raw_status = (getattr(tournament, 'status', '') or '').lower()
        if raw_status not in ('completed', 'archived'):
            needs_convergence = True
        else:
            # Sentinel check: post-finalization hasn't completed yet.
            config = getattr(tournament, 'config', {}) or {}
            pf = config.get('post_finalization')
            if not (isinstance(pf, dict) and pf.get('ran_at')):
                needs_convergence = True
    except Exception:
        needs_convergence = False

    if not needs_convergence:
        return payload

    try:
        from apps.tournaments.services.post_finalization_service import (
            PostFinalizationService,
        )
        PostFinalizationService.run(tournament, actor=actor)
        payload['converged'] = True
    except Exception:
        logger.exception(
            'ensure_post_finalization: PostFinalizationService failed for %s',
            getattr(tournament, 'pk', '?'),
        )

    # Refresh tournament + payload after convergence so callers see fresh
    # status / config.
    try:
        if hasattr(tournament, 'refresh_from_db'):
            tournament.refresh_from_db()
    except Exception:
        pass
    refreshed = get_tournament_completion_payload(tournament)
    refreshed['converged'] = payload['converged']
    return refreshed


__all__ = [
    'is_tournament_effectively_completed',
    'get_tournament_completion_payload',
    'ensure_post_finalization',
]
