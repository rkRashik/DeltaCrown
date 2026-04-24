"""
Tournament placement / final-standings service.

Wraps WinnerDeterminationService and extends it to produce a full ordered
standings list (1..N) suitable for prize distribution and public display.

Why a separate service:
    * `WinnerDeterminationService.determine_winner()` returns a TournamentResult
      with only winner / runner_up / third_place. Prize tiers and public
      "Top N" panels need 4th place and beyond.
    * This module is an additive layer — it never bypasses the existing
      verification, dispute guards, or audit-trail logic.

Public API:
    PlacementService.build_final_standings(tournament) -> list[dict]
        Build the standings list without persisting.
    PlacementService.persist_standings(tournament, actor=None) -> TournamentResult
        Run determine_winner() if needed, then derive 4th + standings, then
        persist them onto the TournamentResult and return it.
    PlacementService.standings_payload(tournament) -> dict
        Return a serializable snapshot for API consumers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Max, Q

from apps.tournaments.models import (
    Bracket,
    Match,
    Registration,
    Tournament,
    TournamentResult,
)
from apps.tournaments.services.winner_service import WinnerDeterminationService

logger = logging.getLogger(__name__)


def _registration_label(reg: Optional[Registration]) -> str:
    """Best-effort display name for a registration."""
    if not reg:
        return ''
    team = getattr(reg, 'team', None)
    if team and getattr(team, 'name', None):
        return str(team.name)
    user = getattr(reg, 'user', None)
    if user:
        return getattr(user, 'username', '') or getattr(user, 'email', '') or 'Player'
    return f'Registration #{reg.pk}'


class PlacementService:

    @classmethod
    def build_final_standings(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """
        Compute ordered standings for a COMPLETED tournament.

        Returns a list of `{placement, registration_id, team_name, source,
        is_tied, tied_with}` ordered by placement ascending.

        Honest about what it can derive:
          * Single elim / double elim: 1st, 2nd, 3rd, 4th (semifinal losers / LB
            losers) where the bracket exposes them.
          * Round Robin / group_playoff / swiss: best-effort using existing
            standings tables; falls back to top 3 from the existing
            TournamentResult.

        If a TournamentResult does not yet exist, only attempts what can be
        inferred from completed matches without raising.
        """
        result = TournamentResult.objects.filter(
            tournament=tournament, is_deleted=False,
        ).first()

        ordered: List[Dict[str, Any]] = []

        def _entry(rank: int, reg: Optional[Registration], source: str,
                   *, tied_with: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
            if not reg:
                return None
            return {
                'placement': rank,
                'registration_id': reg.pk,
                'team_name': _registration_label(reg),
                'source': source,
                'is_tied': bool(tied_with),
                'tied_with': tied_with or [],
            }

        if result:
            for rank, reg, source in (
                (1, result.winner, 'final_winner'),
                (2, result.runner_up, 'final_loser'),
                (3, result.third_place, 'third_place'),
            ):
                entry = _entry(rank, reg, source)
                if entry:
                    ordered.append(entry)

            fourth = cls._derive_fourth_place(tournament, result)
            entry = _entry(4, fourth, 'semifinal_loser_or_lb_final')
            if entry:
                ordered.append(entry)

        return ordered

    # ── 4th place derivation ────────────────────────────────────────────

    @classmethod
    def _derive_fourth_place(
        cls,
        tournament: Tournament,
        result: TournamentResult,
    ) -> Optional[Registration]:
        """
        Derive 4th-place participant from the bracket, if possible.

        SE: the OTHER semifinal loser (the one that didn't take 3rd).
        DE: the loser of the LB Final (LB last round) when distinct from
            podium.
        Round Robin / Swiss / group_playoff: skipped — cannot reliably derive
        without group standings; left to a follow-up.
        """
        bracket = result.final_bracket
        if not bracket:
            try:
                bracket = tournament.bracket
            except Bracket.DoesNotExist:
                return None
        if not bracket:
            return None

        fmt = (getattr(tournament, 'format', '') or '').lower()
        winner_id = getattr(result.winner, 'pk', None)
        runner_up_id = getattr(result.runner_up, 'pk', None) if result.runner_up else None
        third_id = getattr(result.third_place, 'pk', None) if result.third_place else None
        excluded = {x for x in (winner_id, runner_up_id, third_id) if x}

        if fmt == 'double_elimination':
            return cls._fourth_from_lb_final(tournament, bracket, excluded)
        # SE + group_playoff (knockout phase) — semifinal-loser fallback works.
        return cls._fourth_from_semifinals(tournament, bracket, excluded, winner_id, runner_up_id)

    @staticmethod
    def _fourth_from_lb_final(
        tournament: Tournament,
        bracket: Bracket,
        excluded: set,
    ) -> Optional[Registration]:
        # In our DE structure, the loser of the LB final goes to GF then loses
        # → they're 2nd. The LB R-1 loser is 3rd. The LB R-2 loser is 4th.
        # To stay format-tolerant we check matches where bracket node lives in
        # the LB and pick the second-to-last LB round loser.
        try:
            from apps.brackets.models import BracketNode
        except ImportError:
            BracketNode = None

        if BracketNode is None:
            return None

        lb_nodes = BracketNode.objects.filter(
            bracket=bracket,
            bracket_type__in=['lower', 'losers', 'LB'],
        ).order_by('-round_number', '-position')
        if not lb_nodes.exists():
            return None
        max_lb_round = lb_nodes.first().round_number
        if max_lb_round <= 1:
            return None
        target_round = max_lb_round - 1

        target_matches = Match.objects.filter(
            bracket=bracket,
            is_deleted=False,
            state__in=[Match.COMPLETED, Match.FORFEIT],
            round_number=target_round,
        )
        candidate_id = None
        for m in target_matches:
            loser_id = m.loser_id or (
                m.participant2_id if m.winner_id == m.participant1_id
                else m.participant1_id
            )
            if loser_id and loser_id not in excluded:
                candidate_id = loser_id
                break
        if not candidate_id:
            return None
        return Registration.objects.filter(
            tournament=tournament, pk=candidate_id,
        ).first()

    @staticmethod
    def _fourth_from_semifinals(
        tournament: Tournament,
        bracket: Bracket,
        excluded: set,
        winner_id: Optional[int],
        runner_up_id: Optional[int],
    ) -> Optional[Registration]:
        highest_round = Match.objects.filter(
            bracket=bracket, is_deleted=False,
        ).aggregate(Max('round_number'))['round_number__max']
        if not highest_round or highest_round < 2:
            return None
        # Semifinals are round (final - 1). Both finalists came from there.
        sf_round = highest_round - 1
        sf_matches = Match.objects.filter(
            bracket=bracket,
            is_deleted=False,
            round_number=sf_round,
            state__in=[Match.COMPLETED, Match.FORFEIT],
            winner_id__in=[wid for wid in (winner_id, runner_up_id) if wid],
        )
        candidate_id = None
        for m in sf_matches:
            loser_id = m.loser_id or (
                m.participant2_id if m.winner_id == m.participant1_id
                else m.participant1_id
            )
            if loser_id and loser_id not in excluded:
                candidate_id = loser_id
                # Don't break — we want the LAST SF loser that isn't 3rd.
        if not candidate_id:
            return None
        return Registration.objects.filter(
            tournament=tournament, pk=candidate_id,
        ).first()

    # ── persistence ─────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def persist_standings(
        cls,
        tournament: Tournament,
        actor=None,
    ) -> TournamentResult:
        """
        Ensure a TournamentResult exists, then derive + persist 4th place and
        the full final_standings JSON. Idempotent.
        """
        result = TournamentResult.objects.filter(
            tournament=tournament, is_deleted=False,
        ).first()
        if not result:
            service = WinnerDeterminationService(tournament, created_by=actor)
            result = service.determine_winner()

        ordered = cls.build_final_standings(tournament)
        result.final_standings = ordered

        fourth_entry = next((e for e in ordered if e['placement'] == 4), None)
        if fourth_entry and not result.fourth_place_id:
            result.fourth_place_id = fourth_entry['registration_id']

        result.save(update_fields=['final_standings', 'fourth_place'])
        return result

    # ── public payload ──────────────────────────────────────────────────

    @classmethod
    def standings_payload(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Serializable standings + winners snapshot for HUB/API.

        Always returns a dict; empty when tournament hasn't been finalized.
        """
        result = TournamentResult.objects.filter(
            tournament=tournament, is_deleted=False,
        ).select_related('winner', 'runner_up', 'third_place', 'fourth_place').first()

        if not result:
            return {
                'finalized': False,
                'standings': [],
                'top4': [],
            }

        # Prefer persisted standings; fall back to live derivation.
        ordered = list(result.final_standings or []) or cls.build_final_standings(tournament)

        top4 = ordered[:4] if ordered else []

        return {
            'finalized': True,
            'standings': ordered,
            'top4': top4,
            'winner': {
                'registration_id': result.winner_id,
                'team_name': _registration_label(result.winner),
            } if result.winner_id else None,
            'runner_up': {
                'registration_id': result.runner_up_id,
                'team_name': _registration_label(result.runner_up),
            } if result.runner_up_id else None,
            'third_place': {
                'registration_id': result.third_place_id,
                'team_name': _registration_label(result.third_place),
            } if result.third_place_id else None,
            'fourth_place': {
                'registration_id': result.fourth_place_id,
                'team_name': _registration_label(result.fourth_place),
            } if result.fourth_place_id else None,
            'determination_method': result.determination_method,
            'requires_review': result.requires_review,
        }


__all__ = ['PlacementService']
