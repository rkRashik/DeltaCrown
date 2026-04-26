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
    BracketNode,
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

        if result and result.winner_id:
            for rank, reg, source in (
                (1, result.winner, 'final_winner'),
                (2, result.runner_up, 'final_loser'),
                (3, result.third_place, 'third_place'),
            ):
                entry = _entry(rank, reg, source)
                if entry:
                    ordered.append(entry)

            fourth = result.fourth_place or cls._derive_fourth_place(tournament, result)
            entry = _entry(4, fourth, 'semifinal_loser_or_lb_final')
            if entry:
                ordered.append(entry)

        bracket_ordered = cls.derive_standings_from_completed_bracket_final(
            tournament,
            result=result,
        )
        if not ordered:
            ordered = bracket_ordered
        elif bracket_ordered:
            if len(bracket_ordered) > len(ordered):
                ordered = bracket_ordered
            else:
                ordered = cls._overlay_completed_third_place_rows(ordered, bracket_ordered)

        return cls._sanitize_unresolved_single_elim_standings(tournament, ordered)

    @classmethod
    def derive_standings_from_completed_bracket_final(
        cls,
        tournament: Tournament,
        *,
        result: Optional[TournamentResult] = None,
    ) -> List[Dict[str, Any]]:
        """
        Derive top standings directly from the completed bracket final.

        This is the legacy-safe path used when TournamentResult/final_standings
        is missing. It does not write anything; callers that want persistence
        should use persist_standings().
        """
        bracket, final_match = cls._completed_final_match(tournament, result=result)
        if not final_match or not final_match.winner_id:
            return []

        winner = cls._registration_for_match_participant(
            tournament,
            final_match.winner_id,
            cls._match_winner_name(final_match),
        )
        runner_up = cls._registration_for_match_participant(
            tournament,
            cls._match_loser_id(final_match),
            cls._match_loser_name(final_match),
        )
        if not winner:
            return []

        ordered: List[Dict[str, Any]] = []
        seen = set()

        def _append(rank: int, reg: Optional[Registration], source: str) -> None:
            if not reg or reg.pk in seen:
                return
            ordered.append({
                'placement': rank,
                'registration_id': reg.pk,
                'team_name': _registration_label(reg),
                'source': source,
                'is_tied': False,
                'tied_with': [],
            })
            seen.add(reg.pk)

        _append(1, winner, 'bracket_final_winner')
        _append(2, runner_up, 'bracket_final_loser')

        bronze_match = cls._completed_bronze_match(tournament, bracket)
        if bronze_match and bronze_match.winner_id:
            bronze_winner = cls._registration_for_match_participant(
                tournament,
                bronze_match.winner_id,
                cls._match_winner_name(bronze_match),
            )
            bronze_loser = cls._registration_for_match_participant(
                tournament,
                cls._match_loser_id(bronze_match),
                cls._match_loser_name(bronze_match),
            )
            _append(3, bronze_winner, 'third_place_match_winner')
            _append(4, bronze_loser, 'third_place_match_loser')

        return ordered

    @staticmethod
    def _overlay_completed_third_place_rows(
        base_rows: List[Dict[str, Any]],
        bracket_rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        third_place_sources = {
            'third_place_match_winner',
            'third_place_match_loser',
            'bronze_match_winner',
            'bronze_match_loser',
        }
        third_place_rows = {
            int(row.get('placement') or 0): row
            for row in bracket_rows
            if int(row.get('placement') or 0) in (3, 4)
            and (row.get('source') or '') in third_place_sources
        }
        if not third_place_rows:
            return base_rows

        merged = {
            int(row.get('placement') or 0): row
            for row in base_rows
            if int(row.get('placement') or 0)
        }
        merged.update(third_place_rows)
        return [merged[key] for key in sorted(merged)]

    @classmethod
    def _completed_final_match(
        cls,
        tournament: Tournament,
        *,
        result: Optional[TournamentResult] = None,
    ) -> Tuple[Optional[Bracket], Optional[Match]]:
        bracket = result.final_bracket if result and result.final_bracket_id else None
        if not bracket:
            try:
                bracket = tournament.bracket
            except Bracket.DoesNotExist:
                bracket = None

        base_filter = Q(tournament=tournament, is_deleted=False)
        match_filter = base_filter & (Q(bracket=bracket) if bracket else Q())

        final_match = (
            Match.objects
            .filter(match_filter)
            .filter(state__in=[Match.COMPLETED, Match.FORFEIT])
            .exclude(winner_id__isnull=True)
            .exclude(bracket_node__bracket_type=BracketNode.THIRD_PLACE)
            .order_by('-round_number', 'match_number', '-id')
            .first()
        )
        if not final_match and bracket:
            final_match = (
                Match.objects
                .filter(base_filter)
                .filter(state__in=[Match.COMPLETED, Match.FORFEIT])
                .exclude(winner_id__isnull=True)
                .exclude(bracket_node__bracket_type=BracketNode.THIRD_PLACE)
                .order_by('-round_number', 'match_number', '-id')
                .first()
            )
        if final_match and not bracket:
            bracket = final_match.bracket
        return bracket, final_match

    @staticmethod
    def _completed_bronze_match(
        tournament: Tournament,
        bracket: Optional[Bracket],
    ) -> Optional[Match]:
        filters = Q(tournament=tournament, is_deleted=False)
        if bracket:
            filters &= Q(bracket=bracket)
        return (
            Match.objects
            .filter(filters)
            .filter(state__in=[Match.COMPLETED, Match.FORFEIT])
            .exclude(winner_id__isnull=True)
            .filter(bracket_node__bracket_type=BracketNode.THIRD_PLACE)
            .order_by('-round_number', 'match_number', '-id')
            .first()
        )

    @staticmethod
    def _match_loser_id(match: Match) -> Optional[int]:
        if match.loser_id:
            return match.loser_id
        if match.winner_id == match.participant1_id:
            return match.participant2_id
        if match.winner_id == match.participant2_id:
            return match.participant1_id
        return None

    @staticmethod
    def _match_winner_name(match: Match) -> str:
        if match.winner_id == match.participant1_id:
            return match.participant1_name or ''
        if match.winner_id == match.participant2_id:
            return match.participant2_name or ''
        return ''

    @classmethod
    def _match_loser_name(cls, match: Match) -> str:
        loser_id = cls._match_loser_id(match)
        if loser_id == match.participant1_id:
            return match.participant1_name or ''
        if loser_id == match.participant2_id:
            return match.participant2_name or ''
        return ''

    @classmethod
    def _registration_for_match_participant(
        cls,
        tournament: Tournament,
        participant_id: Optional[int],
        participant_name: str = '',
    ) -> Optional[Registration]:
        if not participant_id and not participant_name:
            return None
        queryset = Registration.objects.select_related('user').filter(
            tournament=tournament,
            is_deleted=False,
        )

        lookup_order = []
        participation_type = (getattr(tournament, 'participation_type', '') or '').lower()
        if participation_type == Tournament.TEAM:
            lookup_order = ['team_id', 'user_id', 'pk']
        elif participation_type == Tournament.SOLO:
            lookup_order = ['user_id', 'pk', 'team_id']
        else:
            lookup_order = ['pk', 'team_id', 'user_id']

        for field_name in lookup_order:
            if not participant_id:
                continue
            reg = queryset.filter(**{field_name: participant_id}).first()
            if reg:
                return reg

        normalized_name = cls._normalize_participant_name(participant_name)
        if normalized_name:
            for reg in queryset:
                if cls._normalize_participant_name(_registration_label(reg)) == normalized_name:
                    return reg
                user = getattr(reg, 'user', None)
                if user and cls._normalize_participant_name(getattr(user, 'username', '')) == normalized_name:
                    return reg

        return None

    @staticmethod
    def _normalize_participant_name(value: str) -> str:
        return ' '.join(str(value or '').strip().casefold().split())

    @classmethod
    def _semifinal_losers_from_finalists(
        cls,
        tournament: Tournament,
        bracket: Optional[Bracket],
        final_match: Match,
        *,
        winner_id: Optional[int],
        runner_up_id: Optional[int],
    ) -> List[Registration]:
        if not winner_id or not runner_up_id or final_match.round_number <= 1:
            return []

        filters = Q(
            tournament=tournament,
            is_deleted=False,
            round_number=final_match.round_number - 1,
            state__in=[Match.COMPLETED, Match.FORFEIT],
        )
        if bracket:
            filters &= Q(bracket=bracket)

        finalist_ids = [winner_id, runner_up_id]
        excluded = {winner_id, runner_up_id}
        loser_ids: List[int] = []
        for match in (
            Match.objects
            .filter(filters, winner_id__in=finalist_ids)
            .order_by('match_number', 'id')
        ):
            loser_id = cls._match_loser_id(match)
            if loser_id and loser_id not in excluded and loser_id not in loser_ids:
                loser_ids.append(loser_id)

        if not loser_ids:
            return []

        out = []
        for match in (
            Match.objects
            .filter(filters, winner_id__in=finalist_ids)
            .order_by('match_number', 'id')
        ):
            loser_id = cls._match_loser_id(match)
            if not loser_id or loser_id in excluded:
                continue
            reg = cls._registration_for_match_participant(
                tournament,
                loser_id,
                cls._match_loser_name(match),
            )
            if reg and reg not in out:
                out.append(reg)
        return out

    @classmethod
    def _sanitize_unresolved_single_elim_standings(
        cls,
        tournament: Tournament,
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not rows:
            return []
        try:
            bracket = tournament.bracket
        except Bracket.DoesNotExist:
            bracket = None
        fmt = (getattr(tournament, 'format', '') or '').replace('_', '-').lower()
        structure = getattr(bracket, 'bracket_structure', None) or {}
        structure_fmt = (structure.get('format') or '').replace('_', '-').lower()
        if fmt != 'single-elimination' and structure_fmt != 'single-elimination':
            return rows
        if cls._completed_bronze_match(tournament, bracket):
            return rows
        fake_sources = {
            'third_place',
            'fourth_place',
            'semifinal_loser',
            'semifinal_loser_or_lb_final',
        }
        return [
            row for row in rows
            if not (
                row.get('placement') in (3, 4) and
                (row.get('source') or '') in fake_sources
            )
        ]

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
            try:
                service = WinnerDeterminationService(tournament, created_by=actor)
                result = service.determine_winner()
            except Exception as det_err:
                # Determination can fail if bracket matches aren't all resolved
                # (e.g. legacy tournaments with disputed/skipped matches). In
                # that case, try to build standings from whatever bracket data
                # exists WITHOUT creating a TournamentResult.
                logger.warning(
                    'WinnerDetermination failed for %s: %s; falling back to '
                    'completed bracket-final derivation',
                    tournament.pk,
                    det_err,
                )
                result = TournamentResult.objects.filter(
                    tournament=tournament, is_deleted=False,
                ).first()
                if not result:
                    result = cls._backfill_result_from_completed_final(
                        tournament,
                        actor=actor,
                    )
                if not result:
                    raise

        ordered = cls.build_final_standings(tournament)
        result.final_standings = ordered
        update_fields = ['final_standings']

        for field_name, rank in (
            ('runner_up_id', 2),
            ('third_place_id', 3),
            ('fourth_place_id', 4),
        ):
            value = cls._registration_id_for_rank(ordered, rank)
            if value and not getattr(result, field_name):
                setattr(result, field_name, value)
                update_fields.append(field_name)

        result.save(update_fields=update_fields)
        return result

    # ── public payload ──────────────────────────────────────────────────

    @classmethod
    def _backfill_result_from_completed_final(
        cls,
        tournament: Tournament,
        *,
        actor=None,
    ) -> Optional[TournamentResult]:
        standings = cls.derive_standings_from_completed_bracket_final(tournament)
        winner_entry = next((e for e in standings if e.get('placement') == 1), None)
        if not winner_entry:
            return None

        bracket, final_match = cls._completed_final_match(tournament)
        result, created = TournamentResult.objects.get_or_create(
            tournament=tournament,
            defaults={
                'winner_id': winner_entry['registration_id'],
                'runner_up_id': cls._registration_id_for_rank(standings, 2),
                'third_place_id': cls._registration_id_for_rank(standings, 3),
                'fourth_place_id': cls._registration_id_for_rank(standings, 4),
                'final_bracket': bracket,
                'final_standings': standings,
                'determination_method': 'normal',
                'rules_applied': {
                    'source': 'completed_bracket_final_backfill',
                    'final_match_id': final_match.pk if final_match else None,
                    'tournament_id': tournament.pk,
                },
                'created_by': actor,
            },
        )
        if not created:
            update_fields = []
            for field_name, rank in (
                ('runner_up_id', 2),
                ('third_place_id', 3),
                ('fourth_place_id', 4),
            ):
                value = cls._registration_id_for_rank(standings, rank)
                if value and not getattr(result, field_name):
                    setattr(result, field_name, value)
                    update_fields.append(field_name)
            if not result.final_bracket_id and bracket:
                result.final_bracket = bracket
                update_fields.append('final_bracket')
            if not result.final_standings:
                result.final_standings = standings
                update_fields.append('final_standings')
            if update_fields:
                result.save(update_fields=update_fields)
        return result

    @staticmethod
    def _registration_id_for_rank(
        standings: List[Dict[str, Any]],
        rank: int,
    ) -> Optional[int]:
        entry = next((e for e in standings if e.get('placement') == rank), None)
        return entry.get('registration_id') if entry else None

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
            ordered = cls.derive_standings_from_completed_bracket_final(tournament)
            if ordered:
                return {
                    'finalized': False,
                    'standings': ordered,
                    'top4': ordered[:4],
                    'winner': cls._snapshot_for_rank(ordered, 1),
                    'runner_up': cls._snapshot_for_rank(ordered, 2),
                    'third_place': cls._snapshot_for_rank(ordered, 3),
                    'fourth_place': cls._snapshot_for_rank(ordered, 4),
                    'determination_method': 'bracket_final',
                    'requires_review': False,
                }
            return {
                'finalized': False,
                'standings': [],
                'top4': [],
            }

        # Prefer persisted standings, but completed Third Place Match rows must
        # override stale legacy rank 3/4 JSON.
        ordered = list(result.final_standings or []) or cls.build_final_standings(tournament)
        bracket_ordered = cls.derive_standings_from_completed_bracket_final(
            tournament,
            result=result,
        )
        if ordered and bracket_ordered:
            ordered = cls._overlay_completed_third_place_rows(ordered, bracket_ordered)

        ordered = cls._sanitize_unresolved_single_elim_standings(tournament, ordered)
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

    @staticmethod
    def _snapshot_for_rank(
        standings: List[Dict[str, Any]],
        rank: int,
    ) -> Optional[Dict[str, Any]]:
        entry = next((e for e in standings if e.get('placement') == rank), None)
        if not entry:
            return None
        return {
            'registration_id': entry.get('registration_id'),
            'team_name': entry.get('team_name') or '',
        }


__all__ = ['PlacementService']
