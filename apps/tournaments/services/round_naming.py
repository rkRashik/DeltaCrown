"""
Canonical round / stage naming for tournament brackets.

Single source of truth for human-readable round labels across:
  * BracketService (during generation, persists into bracket_structure)
  * TOC matches API (matches_service)
  * Public schedule / live views
  * Frontend display

Two label flavours intentionally exist:

  * `short_label`   — compact, used in lists and badges. Singular form.
                      e.g. "Final", "Semifinal", "Quarterfinal", "Round of 16",
                      "Round 1", "WB Final", "LB R3", "Grand Final",
                      "Grand Final Reset".

  * `long_label`    — prose form, used in headers / details. Same labels but
                      pluralised for top-of-bracket rounds when more than one
                      match exists in the round (e.g. "Quarterfinals").

Brackets store `short_label` in their bracket_structure JSON under
`rounds[].round_name` so callers can read it back without re-deriving.
"""

from __future__ import annotations

from typing import Dict


_KNOCKOUT_BY_DISTANCE: Dict[int, tuple[str, str]] = {
    # rounds_from_end: (short, long)
    0: ('Final', 'Final'),
    1: ('Semifinal', 'Semifinals'),
    2: ('Quarterfinal', 'Quarterfinals'),
    3: ('Round of 16', 'Round of 16'),
    4: ('Round of 32', 'Round of 32'),
    5: ('Round of 64', 'Round of 64'),
    6: ('Round of 128', 'Round of 128'),
    7: ('Round of 256', 'Round of 256'),
}


def knockout_round_label(round_number: int, total_rounds: int, *, long: bool = False) -> str:
    """
    Canonical knockout round label for single-elim or upper-bracket rounds.

    `total_rounds` is the count of rounds in the bracket; the final is the last.
    For round_number == total_rounds the label is "Final". Earlier rounds derive
    a label from the distance to the final (Semi/Quarter/Round of N), and very
    early rounds fall back to "Round N".
    """
    if not round_number:
        return ''
    if total_rounds <= 0:
        return f'Round {round_number}'
    rounds_from_end = int(total_rounds) - int(round_number)
    if rounds_from_end < 0:
        return f'Round {round_number}'
    pair = _KNOCKOUT_BY_DISTANCE.get(rounds_from_end)
    if pair:
        return pair[1] if long else pair[0]
    return f'Round {round_number}'


def double_elim_round_label(
    bracket_type: str,
    round_number: int,
    total_wb_rounds: int,
    total_lb_rounds: int,
    *,
    long: bool = False,
) -> str:
    """
    Round label for double-elim winner / loser / grand-final stages.

    `bracket_type` is the BracketNode.bracket_type value:
      * 'main' / 'WB' / 'winners'  → upper bracket
      * 'lower' / 'LB' / 'losers'  → lower bracket
      * 'grand_final' / 'GF'       → grand final
      * 'grand_final_reset' / 'GFR' → bracket reset

    Falls through to a generic round label when the type is unknown.
    """
    bt = (bracket_type or '').strip().lower()

    if bt in ('grand_final', 'gf', 'grand_finals'):
        return 'Grand Final'
    if bt in ('grand_final_reset', 'gfr', 'reset', 'grand_finals_reset'):
        return 'Grand Final Reset'

    if bt in ('lower', 'lb', 'losers', 'loser', 'losers_bracket'):
        # LB rounds are numbered 1..total_lb_rounds; the LB final is the last.
        if total_lb_rounds and round_number == total_lb_rounds:
            return 'LB Final'
        if total_lb_rounds and round_number == total_lb_rounds - 1:
            return 'LB Semifinal'
        return f'LB R{round_number}' if not long else f'Lower Bracket Round {round_number}'

    # Upper / winners bracket
    if total_wb_rounds and round_number == total_wb_rounds:
        return 'WB Final'
    if total_wb_rounds and round_number == total_wb_rounds - 1:
        return 'WB Semifinals' if long else 'WB Semifinal'
    if total_wb_rounds and round_number == total_wb_rounds - 2:
        return 'WB Quarterfinals' if long else 'WB Quarterfinal'
    return f'WB R{round_number}' if not long else f'Winners Bracket Round {round_number}'


def round_robin_round_label(round_number: int, total_rounds: int) -> str:
    """RR rounds are just numbered. Total rounds = participants - 1 (or n)."""
    if not round_number:
        return ''
    return f'Round {round_number}'


def swiss_round_label(round_number: int, total_rounds: int) -> str:
    """Swiss rounds are numbered + show total when known."""
    if not round_number:
        return ''
    if total_rounds:
        return f'Swiss R{round_number}/{total_rounds}'
    return f'Swiss R{round_number}'


def stage_label_for_node(node, total_rounds_by_type: Dict[str, int] | None = None) -> str:
    """
    Best-effort label for a BracketNode-like object.

    `node` must expose `round_number` and `bracket_type` (string).
    `total_rounds_by_type` optionally overrides per-type round totals, e.g.
    `{'main': 4, 'lower': 6, 'grand_final': 1}`.
    """
    rt = (getattr(node, 'bracket_type', '') or '').strip().lower()
    rn = int(getattr(node, 'round_number', 0) or 0)
    totals = total_rounds_by_type or {}
    wb_total = int(totals.get('main', totals.get('WB', 0)) or 0)
    lb_total = int(totals.get('lower', totals.get('LB', 0)) or 0)

    if rt in ('grand_final', 'gf', 'grand_final_reset', 'gfr',
              'lower', 'lb', 'losers', 'loser', 'main', 'wb', 'winners'):
        return double_elim_round_label(rt, rn, wb_total, lb_total)

    # Single elimination / unknown — use straight knockout naming.
    return knockout_round_label(rn, wb_total)


__all__ = [
    'knockout_round_label',
    'double_elim_round_label',
    'round_robin_round_label',
    'swiss_round_label',
    'stage_label_for_node',
]
