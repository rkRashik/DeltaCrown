"""
Canonical match classification + label resolution.

This is the single source of truth shared by every TOC, HUB, and public
surface that needs to answer:
  * What round label should we show for this match?
  * Is this match a knockout, group_stage, or swiss match?
  * What total_rounds value should the labeller use?
  * Which canonical Match record corresponds to a given BracketNode?

If you find yourself computing any of those independently, route through
this module instead. Drift between TOC, HUB, and public always traces back
to two callers computing the same thing.

Public API
----------

  * `is_pure_knockout(format)` → bool
  * `tournament_total_rounds(tournament, *, bracket=None)` → int
  * `compute_round_label(tournament, match, *, bracket=None, total_rounds=None)` → str
  * `classify_stage(tournament, match)` → 'knockout' | 'group_stage' | 'swiss'
  * `resolve_match_for_node(node, *, tournament=None)` → Match | None
  * `stage_filter_q(tournament_format, stage)` → Q  (canonical filter that
    matches the truth contract — does NOT exclude matches missing bracket FK
    in pure-knockout formats)

Truth contract:
  * `single_elimination` / `double_elimination` → always knockout
  * `round_robin` → always group_stage
  * `swiss` → always swiss
  * `group_playoff` → bracket FK is the source of truth
  * Other / unknown → bracket FK heuristic
"""

from __future__ import annotations

from typing import Optional

from django.db.models import Q

from apps.tournaments.services.round_naming import knockout_round_label


PURE_KNOCKOUT_FORMATS = frozenset({'single_elimination', 'double_elimination'})
HYBRID_KNOCKOUT_FORMATS = frozenset({'group_playoff'})


def _fmt(tournament) -> str:
    return (getattr(tournament, 'format', '') or '').lower()


def is_pure_knockout(format_str: str) -> bool:
    return (format_str or '').lower() in PURE_KNOCKOUT_FORMATS


def tournament_total_rounds(tournament, *, bracket=None) -> int:
    """
    Authoritative total_rounds for canonical labelling.

    Order of preference:
      1. `bracket.total_rounds` if non-zero
      2. MAX `Match.round_number` for the tournament
    """
    if bracket is None:
        try:
            from apps.brackets.models import Bracket as _Bracket
            bracket = _Bracket.objects.filter(tournament=tournament).first()
        except Exception:
            bracket = None
    if bracket is not None:
        total = int(getattr(bracket, 'total_rounds', 0) or 0)
        if total > 0:
            return total
    try:
        from apps.tournaments.models.match import Match as _Match
        rows = _Match.objects.filter(
            tournament=tournament, is_deleted=False,
        ).values_list('round_number', flat=True)
        return max((int(r or 0) for r in rows), default=0)
    except Exception:
        return 0


def compute_round_label(
    tournament,
    match,
    *,
    bracket=None,
    total_rounds: Optional[int] = None,
) -> str:
    """
    Canonical round label for a single Match.

    Pure-knockout formats: ALWAYS use the canonical knockout labeller — the
    persisted `bracket_structure.rounds[].round_name` is ignored because
    older tournaments hold stale plural forms ("Quarter Finals") that
    disagree with the canonical singular forms ("Quarterfinal").
    """
    fmt = _fmt(tournament)
    rn = int(getattr(match, 'round_number', 0) or 0)
    if not rn:
        return ''

    if fmt in PURE_KNOCKOUT_FORMATS:
        if total_rounds is None:
            total_rounds = tournament_total_rounds(tournament, bracket=bracket)
        return knockout_round_label(rn, total_rounds) or f'Round {rn}'

    if fmt == 'swiss':
        return f'Round {rn}'

    if fmt == 'round_robin':
        return f'Round {rn}'

    # group_playoff and unknown: prefer persisted bracket label when match
    # is bracket-linked, else generic.
    bracket_id = getattr(match, 'bracket_id', None)
    if bracket_id:
        if bracket is None:
            try:
                from apps.brackets.models import Bracket as _Bracket
                bracket = _Bracket.objects.filter(tournament=tournament).first()
            except Exception:
                bracket = None
        if bracket is not None and hasattr(bracket, 'get_round_name'):
            try:
                label = bracket.get_round_name(rn)
                if label:
                    return label
            except Exception:
                pass
    return f'Round {rn}'


def classify_stage(tournament, match) -> str:
    """Return one of 'knockout' / 'group_stage' / 'swiss'."""
    fmt = _fmt(tournament)
    if fmt in PURE_KNOCKOUT_FORMATS:
        return 'knockout'
    if fmt == 'round_robin':
        return 'group_stage'
    if fmt == 'swiss':
        return 'swiss'
    bracket_id = getattr(match, 'bracket_id', None)
    return 'knockout' if bracket_id else 'group_stage'


def stage_filter_q(tournament_format: str, stage: str) -> Optional[Q]:
    """
    Canonical Q-filter for the stage tab.

    Returns None when no filtering should apply.
    For pure-knockout formats, every match counts as knockout regardless of
    bracket FK presence — so requesting `stage=knockout` returns all matches
    and `stage=group_stage` returns NONE (the format has no group stage).

    For group_playoff, bracket FK presence decides.
    """
    fmt = (tournament_format or '').lower()
    s = (stage or '').lower()
    if not s:
        return None

    if fmt in PURE_KNOCKOUT_FORMATS:
        if s in ('knockout', 'knockout_stage'):
            return Q()  # accept everything
        if s == 'group_stage':
            return Q(pk__in=[])  # match nothing
        if s == 'swiss':
            return Q(pk__in=[])
        return None

    if fmt == 'round_robin':
        if s == 'group_stage':
            return Q()
        return Q(pk__in=[])

    if fmt == 'swiss':
        if s == 'swiss':
            return Q()
        return Q(pk__in=[])

    # group_playoff and unknown — bracket FK heuristic.
    if s == 'group_stage':
        return Q(bracket__isnull=True)
    if s in ('knockout', 'knockout_stage'):
        return Q(bracket__isnull=False)
    return None


def resolve_match_for_node(node, *, tournament=None):
    """
    Find the canonical Match for a BracketNode whose `match` FK is missing.

    Lookup order:
      1. `node.match` if present (pre-fetched).
      2. (bracket_id, round_number, match_number_in_round)
      3. (tournament_id, round_number, match_number_in_round)

    Returns Match instance or None.
    """
    direct = getattr(node, 'match', None)
    if direct:
        return direct
    try:
        from apps.tournaments.models.match import Match as _Match
    except Exception:
        return None

    rn = getattr(node, 'round_number', None)
    mn = getattr(node, 'match_number_in_round', None)
    if not rn or not mn:
        return None

    bracket_id = getattr(node, 'bracket_id', None)
    if bracket_id:
        m = _Match.objects.filter(
            bracket_id=bracket_id,
            round_number=rn,
            match_number=mn,
            is_deleted=False,
        ).first()
        if m:
            return m

    if tournament is None:
        bracket = getattr(node, 'bracket', None)
        tournament = getattr(bracket, 'tournament', None) if bracket else None
    tournament_id = getattr(tournament, 'pk', None) if tournament else None
    if tournament_id:
        return _Match.objects.filter(
            tournament_id=tournament_id,
            round_number=rn,
            match_number=mn,
            is_deleted=False,
        ).first()
    return None


__all__ = [
    'PURE_KNOCKOUT_FORMATS',
    'HYBRID_KNOCKOUT_FORMATS',
    'is_pure_knockout',
    'tournament_total_rounds',
    'compute_round_label',
    'classify_stage',
    'stage_filter_q',
    'resolve_match_for_node',
]
