"""
Bracket repair service — idempotent, non-destructive.

Scans a tournament's BracketNodes + Matches and safely links them when the
FKs are missing. Fixes two common legacy artifacts:

  1. `BracketNode.match_id` is NULL but a unique Match exists at the same
     (bracket, round_number, match_number_in_round) coordinate.
  2. `Match.bracket_id` is NULL but the Match is the unique target of a
     BracketNode in this tournament.

Never overwrites scores, winners, or state. Never deletes anything. Safe to
call repeatedly.

Usage
-----

    from apps.tournaments.services.bracket_repair_service import BracketRepairService
    report = BracketRepairService.repair(tournament)
    # report: {
    #   'linked_nodes': int,        # BracketNode.match_id populated
    #   'backfilled_matches': int,  # Match.bracket_id populated
    #   'unresolved_nodes': list[int],
    #   'ambiguous_matches': list[int],
    # }

    # dry-run
    report = BracketRepairService.dry_run(tournament)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from django.db import transaction

logger = logging.getLogger(__name__)


@dataclass
class RepairReport:
    linked_nodes: int = 0
    backfilled_matches: int = 0
    participant_slots_backfilled: int = 0
    winners_backfilled: int = 0
    skipped_non_empty_participants: int = 0
    unresolved_nodes: List[int] = field(default_factory=list)
    ambiguous_matches: List[int] = field(default_factory=list)
    proposed_changes: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self):
        return {
            'linked_nodes': self.linked_nodes,
            'backfilled_matches': self.backfilled_matches,
            'participant_slots_backfilled': self.participant_slots_backfilled,
            'winners_backfilled': self.winners_backfilled,
            'skipped_non_empty_participants': self.skipped_non_empty_participants,
            'unresolved_nodes': list(self.unresolved_nodes),
            'ambiguous_matches': list(self.ambiguous_matches),
            'proposed_changes': list(self.proposed_changes),
            'errors': list(self.errors),
            'dry_run': self.dry_run,
        }


class BracketRepairService:

    @classmethod
    def repair(
        cls,
        tournament,
        *,
        dry_run: bool = False,
        force_participants: bool = False,
    ) -> RepairReport:
        """
        Idempotently repair bracket/match links for a single tournament.

        Args:
            tournament: Tournament model instance or pk.
            dry_run: If True, only report would-be changes without writing.
            force_participants: If True, OVERWRITE non-empty Match participant
                slots from the BracketNode's denormalized slots. Default False
                — only empty slots are backfilled. Dangerous flag; callers must
                opt in.
        """
        from apps.tournaments.models.tournament import Tournament
        from apps.tournaments.models.match import Match
        try:
            from apps.brackets.models import Bracket, BracketNode
        except ImportError:
            return RepairReport(errors=['brackets app unavailable'], dry_run=dry_run)

        if isinstance(tournament, int):
            tournament = Tournament.objects.get(pk=tournament)

        report = RepairReport(dry_run=dry_run)

        bracket = Bracket.objects.filter(tournament=tournament).first()
        if bracket is None:
            return report  # nothing to do

        # ── Phase 1: link BracketNode.match_id where missing ─────────────
        # For each node without match_id, search Matches by coordinate. Prefer
        # (bracket_id, round_number, match_number_in_round), falling back to
        # (tournament_id, round_number, match_number_in_round).
        unlinked_nodes = list(
            BracketNode.objects.filter(bracket=bracket, match__isnull=True)
        )

        for node in unlinked_nodes:
            candidates = list(Match.objects.filter(
                bracket=bracket,
                round_number=node.round_number,
                match_number=node.match_number_in_round,
                is_deleted=False,
            ))
            if not candidates:
                candidates = list(Match.objects.filter(
                    tournament=tournament,
                    bracket__isnull=True,
                    round_number=node.round_number,
                    match_number=node.match_number_in_round,
                    is_deleted=False,
                ))
            if len(candidates) == 1:
                m = candidates[0]
                if not dry_run:
                    try:
                        with transaction.atomic():
                            node.match_id = m.id
                            node.save(update_fields=['match'])
                    except Exception as e:
                        report.errors.append(
                            f'node={node.id}: save failed ({e})'
                        )
                        continue
                report.linked_nodes += 1
            elif len(candidates) == 0:
                report.unresolved_nodes.append(node.id)
            else:
                # Ambiguous — report but don't pick one.
                for c in candidates:
                    if c.id not in report.ambiguous_matches:
                        report.ambiguous_matches.append(c.id)

        # ── Phase 2: backfill Match.bracket_id where missing ────────────
        # A Match should be linked to the bracket when a BracketNode references
        # it. Run this AFTER phase 1 so newly-linked nodes trigger backfill.
        linked_node_match_ids = list(
            BracketNode.objects.filter(
                bracket=bracket, match__isnull=False,
            ).values_list('match_id', flat=True)
        )
        if linked_node_match_ids:
            orphan_match_qs = Match.objects.filter(
                pk__in=linked_node_match_ids, bracket__isnull=True,
            )
            if dry_run:
                report.backfilled_matches = orphan_match_qs.count()
            else:
                try:
                    with transaction.atomic():
                        updated = orphan_match_qs.update(bracket=bracket)
                    report.backfilled_matches = updated
                except Exception as e:
                    report.errors.append(f'bracket backfill failed: {e}')

        # ── Phase 3: backfill Match participant slots from BracketNode ──
        # For each BracketNode that has a linked match AND denormalized
        # participant slots, copy empty Match slots from the node. Skip
        # non-empty Match slots unless force_participants=True.
        # Collect proposed changes first; ONLY mutate the Match object when
        # we're going to save it. Keeps dry_run a true no-op.
        for node in BracketNode.objects.filter(
            bracket=bracket, match__isnull=False,
        ).select_related('match'):
            m = node.match
            if not m or m.is_deleted:
                continue
            proposed = {}  # field_name -> new_value
            slot_count = 0
            for idx in (1, 2):
                node_id = getattr(node, f'participant{idx}_id', None)
                node_name = (getattr(node, f'participant{idx}_name', '') or '').strip()
                if not node_id and not node_name:
                    continue  # node slot is TBD — nothing to copy
                match_id = getattr(m, f'participant{idx}_id', None)
                match_name = (getattr(m, f'participant{idx}_name', '') or '').strip()
                match_slot_empty = not match_id and not match_name
                slot_changed = False
                if match_slot_empty or force_participants:
                    if node_id and node_id != match_id:
                        proposed[f'participant{idx}_id'] = node_id
                        slot_changed = True
                    if node_name and node_name != match_name:
                        proposed[f'participant{idx}_name'] = node_name
                        slot_changed = True
                elif not match_slot_empty and (node_id != match_id or node_name != match_name):
                    report.skipped_non_empty_participants += 1
                if slot_changed:
                    slot_count += 1
            # ── Winner backfill (only when Match.winner_id is null) ──
            # Confirm node winner is one of the *post-backfill* participant
            # IDs so we don't insert an orphan winner_id.
            node_winner = getattr(node, 'winner_id', None)
            match_winner = getattr(m, 'winner_id', None)
            winner_changed = False
            if node_winner and not match_winner:
                final_p1 = proposed.get('participant1_id', m.participant1_id)
                final_p2 = proposed.get('participant2_id', m.participant2_id)
                if node_winner in (final_p1, final_p2):
                    proposed['winner_id'] = node_winner
                    winner_changed = True

            if not proposed:
                continue

            change_record = {
                'match_id': m.id,
                'node_id': node.id,
                'changes': [
                    f'{k}: {getattr(m, k, None)!r} → {v!r}'
                    for k, v in proposed.items()
                ],
            }
            if dry_run:
                report.participant_slots_backfilled += slot_count
                if winner_changed:
                    report.winners_backfilled += 1
                report.proposed_changes.append(change_record)
            else:
                try:
                    with transaction.atomic():
                        for field, value in proposed.items():
                            setattr(m, field, value)
                        m.save(update_fields=list(proposed.keys()))
                    report.participant_slots_backfilled += slot_count
                    if winner_changed:
                        report.winners_backfilled += 1
                    report.proposed_changes.append(change_record)
                except Exception as e:
                    report.errors.append(
                        f'match={m.id}: participant/winner backfill failed ({e})'
                    )

        logger.info(
            'BracketRepairService: tournament=%s linked=%s backfilled=%s '
            'slots_backfilled=%s winners_backfilled=%s skipped=%s '
            'unresolved=%s ambiguous=%s errors=%s '
            '(dry_run=%s force_participants=%s)',
            tournament.pk, report.linked_nodes, report.backfilled_matches,
            report.participant_slots_backfilled, report.winners_backfilled,
            report.skipped_non_empty_participants,
            len(report.unresolved_nodes), len(report.ambiguous_matches),
            len(report.errors), dry_run, force_participants,
        )
        return report

    @classmethod
    def dry_run(cls, tournament) -> RepairReport:
        return cls.repair(tournament, dry_run=True)


__all__ = ['BracketRepairService', 'RepairReport']
