"""
Format Advisor — light-touch validation + warnings for tournament format vs. participant counts.

Purpose
-------
Catch obviously broken combinations (hard errors) and surface awkward but
technically-supported combinations as soft warnings, so organizers can choose
deliberately rather than getting a degenerate bracket by accident.

Hard errors (raise on form/serializer):
  * Double Elimination with fewer than 4 participants — degenerate bracket.
  * Single Elimination with fewer than 2 max participants — no possible match.
  * Group Stage + Playoff with fewer than 4 participants.

Soft warnings (do not block save):
  * 3-player SE — suggest Round Robin instead.
  * Small DE brackets (< 8) — heavy bye rounds.
  * Non-power-of-2 max in SE/DE — bye round expected.
  * Swiss with very few participants (< 4) — round count won't differentiate.
  * Round Robin with very large max (> 16) — match count grows quadratically.

Format constants come from Tournament.FORMAT_CHOICES.
"""

from __future__ import annotations

from typing import List, Tuple


SINGLE_ELIM = 'single_elimination'
DOUBLE_ELIM = 'double_elimination'
ROUND_ROBIN = 'round_robin'
SWISS = 'swiss'
GROUP_PLAYOFF = 'group_playoff'


def _is_power_of_two(n: int) -> bool:
    return n >= 2 and (n & (n - 1)) == 0


def _next_power_of_two(n: int) -> int:
    p = 2
    while p < n:
        p <<= 1
    return p


def validate_format_participants(
    fmt: str | None,
    min_participants: int | None,
    max_participants: int | None,
) -> Tuple[List[str], List[str]]:
    """
    Inspect a (format, min_participants, max_participants) combination.

    Returns
    -------
    (errors, warnings):
        errors   — hard validation problems; callers should raise.
        warnings — non-fatal advice; callers should surface to the organizer.

    Missing/None inputs short-circuit to ([], []) — other layers handle "required".
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not fmt:
        return errors, warnings

    try:
        max_p = int(max_participants) if max_participants is not None else None
    except (TypeError, ValueError):
        max_p = None
    try:
        min_p = int(min_participants) if min_participants is not None else None
    except (TypeError, ValueError):
        min_p = None

    if max_p is None:
        return errors, warnings

    # ---- Hard errors ----------------------------------------------------
    if fmt == DOUBLE_ELIM:
        if max_p < 4:
            errors.append(
                'Double Elimination needs at least 4 participants — with fewer '
                'the lower bracket collapses into a single rematch. Use Single '
                'Elimination or Round Robin for tiny brackets.'
            )
        elif min_p is not None and min_p < 4:
            warnings.append(
                'Double Elimination is most meaningful from 4 participants up. '
                'Setting a minimum below 4 will block the tournament from going '
                'live until enough teams register.'
            )

    if fmt == SINGLE_ELIM and max_p < 2:
        errors.append('Single Elimination needs at least 2 participants.')

    if fmt == GROUP_PLAYOFF and max_p < 4:
        errors.append(
            'Group Stage + Playoff needs at least 4 participants — usually two '
            'groups of two minimum. For smaller fields use Round Robin.'
        )

    if errors:
        # If we already have hard errors, suppress softer warnings to keep
        # messaging focused.
        return errors, warnings

    # ---- Soft warnings --------------------------------------------------
    if fmt == SINGLE_ELIM and max_p == 3:
        warnings.append(
            '3-player Single Elimination plays only 2 matches and gives one '
            'player a bye into the final. Round Robin (3 matches, no byes) is '
            'usually fairer for 3 participants.'
        )

    if fmt in (SINGLE_ELIM, DOUBLE_ELIM) and max_p >= 2 and not _is_power_of_two(max_p):
        nxt = _next_power_of_two(max_p)
        byes = nxt - max_p
        warnings.append(
            f'Bracket size {max_p} is not a power of two. The bracket will be '
            f'padded to {nxt} slots, producing {byes} bye(s) in round 1. '
            'Consider rounding to 4, 8, 16, 32, 64, 128, or 256.'
        )

    if fmt == DOUBLE_ELIM and 4 <= max_p <= 7:
        warnings.append(
            'Small Double Elimination brackets (under 8) generate several bye '
            'rounds and short matches. Round Robin or a larger DE bracket '
            'usually plays better.'
        )

    if fmt == SWISS and max_p < 4:
        warnings.append(
            'Swiss with fewer than 4 participants does not have enough rounds '
            'to differentiate standings — Round Robin is a better fit.'
        )

    if fmt == ROUND_ROBIN and max_p > 16:
        # n*(n-1)/2 matches grows quickly; surface the cost.
        match_count = max_p * (max_p - 1) // 2
        warnings.append(
            f'Round Robin with {max_p} participants schedules {match_count} '
            'matches. Consider Group Stage + Playoff or Swiss for large fields.'
        )

    return errors, warnings


__all__ = ['validate_format_participants']
