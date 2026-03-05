"""
SwissService — Swiss System pairing engine for DeltaCrown tournaments.

Swiss format rules:
- Players are paired by similar score (wins/points); no repeat pairings.
- Round 1: ranked/seeded pairing (1 vs 2, 3 vs 4, …).
- Subsequent rounds: group by points, pair within group, fold down on odd counts.
- Total rounds recommended: ceil(log2(n_participants)).
- No player is eliminated; final standings by total wins.

Integration:
- `SwissService.generate_round1(tournament)` — creates Bracket + Round 1 BracketNodes.
- `SwissService.generate_next_round(bracket)` — creates the next round using current results.
- `SwissService.get_standings(bracket)` — returns sorted standings dict.
- BracketService.generate_bracket routes to SwissService._generate_swiss for 'swiss' format.
"""

from __future__ import annotations

import math
import itertools
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from django.db import transaction
from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from apps.tournaments.models.tournament import Tournament
    from apps.tournaments.models.bracket import Bracket, BracketNode


class SwissService:
    """Swiss system pairing engine."""

    # ----------------------------------------------------------------
    # Public: Generate Round 1 (initial bracket)
    # ----------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def generate_round1(
        tournament: "Tournament",
        participants: List[Dict],
        seeding_method: str = "slot-order",
        total_rounds: Optional[int] = None,
    ) -> "Bracket":
        """
        Create a new Swiss bracket and generate Round 1 pairings.

        Round 1 pairs participants by seed: 1 vs 2, 3 vs 4, etc.
        If odd count, the lowest-seed participant receives a bye.

        Args:
            tournament:      Tournament instance.
            participants:    Seeded participant list (dicts with 'id', 'name').
            seeding_method:  e.g. 'slot-order', 'random', 'ranked'.
            total_rounds:    Number of Swiss rounds (default: ceil(log2(n))).

        Returns:
            Bracket instance with Round 1 nodes created.
        """
        from apps.tournaments.models.bracket import Bracket, BracketNode

        n = len(participants)
        if n < 2:
            raise ValidationError("Swiss bracket requires at least 2 participants.")

        recommended_rounds = math.ceil(math.log2(n)) if n > 1 else 1
        if total_rounds is None or total_rounds < 1:
            total_rounds = recommended_rounds

        # Swiss-specific structure metadata
        bracket_structure = {
            "format": "swiss",
            "total_participants": n,
            "total_rounds": total_rounds,
            "rounds": [{"round_number": 1, "round_name": "Round 1", "matches": n // 2}],
            "current_round": 1,
        }

        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SWISS,
            total_rounds=total_rounds,
            total_matches=0,  # will increment as rounds are added
            bracket_structure=bracket_structure,
            seeding_method=seeding_method,
            is_finalized=False,
        )

        SwissService._create_round_nodes(bracket, round_number=1, pairings=SwissService._seed_pairings(participants))
        return bracket

    # ----------------------------------------------------------------
    # Public: Advance to next round
    # ----------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def generate_next_round(bracket: "Bracket") -> "Bracket":
        """
        Use current match results to compute pairings for the next Swiss round.

        Rules:
        1. All matches in the *current* round must be completed (COMPLETED or FORFEIT).
        2. Participants are grouped by cumulative wins.
        3. Within each group, participants are paired by seed (highest wins first).
        4. Pairings that recreate a prior head-to-head are avoided (fold-down).
        5. If still odd, lowest-ranked unpaired participant receives a bye.

        Args:
            bracket: Bracket instance (format must be 'swiss').

        Returns:
            Updated Bracket instance with new round nodes added.

        Raises:
            ValidationError: If format is not swiss, all rounds finished, or
                             current round not fully completed.
        """
        from apps.tournaments.models.bracket import Bracket, BracketNode
        from apps.tournaments.models.match import Match

        if bracket.format != Bracket.SWISS:
            raise ValidationError("generate_next_round() is only for Swiss brackets.")

        structure = bracket.bracket_structure or {}
        current_round = structure.get("current_round", 1)
        total_rounds = bracket.total_rounds

        if current_round >= total_rounds:
            raise ValidationError(
                f"Swiss bracket is already on the final round ({current_round}/{total_rounds})."
            )

        # Validate all current-round matches are complete
        current_nodes = BracketNode.objects.filter(
            bracket=bracket, round_number=current_round
        ).select_related("match")

        incomplete = []
        for node in current_nodes:
            if node.match and node.match.state not in (Match.COMPLETED, Match.FORFEIT, Match.CANCELLED):
                incomplete.append(node.match.id)
        if incomplete:
            raise ValidationError(
                f"Cannot advance: {len(incomplete)} match(es) in round {current_round} are not yet complete."
            )

        next_round = current_round + 1
        standings = SwissService._compute_standings(bracket)

        # All participants sorted by wins desc, then by initial seed
        participants_sorted = sorted(
            standings.values(),
            key=lambda p: (-p["wins"], p["seed"]),
        )

        # Prior pairings (to avoid rematches)
        prior_pairings = SwissService._get_prior_pairings(bracket)

        pairings = SwissService._dutch_pairing(participants_sorted, prior_pairings)

        SwissService._create_round_nodes(bracket, round_number=next_round, pairings=pairings)

        # Update bracket structure
        structure["current_round"] = next_round
        rounds_list: list = structure.setdefault("rounds", [])
        rounds_list.append(
            {"round_number": next_round, "round_name": f"Round {next_round}", "matches": len(pairings)}
        )
        bracket.bracket_structure = structure
        bracket.save(update_fields=["bracket_structure"])

        return bracket

    # ----------------------------------------------------------------
    # Public: Standings
    # ----------------------------------------------------------------

    @staticmethod
    def get_standings(bracket: "Bracket") -> List[Dict]:
        """
        Return participants sorted by standings: wins desc, then losses asc, then seed asc.

        Returns:
            List of dicts: {id, name, seed, wins, losses, byes, buchholz}.
            buchholz = sum of opponents' wins (strength-of-schedule tiebreaker).
        """
        standings = SwissService._compute_standings(bracket)
        standings_list = sorted(
            standings.values(),
            key=lambda p: (-p["wins"], p["losses"], p["seed"]),
        )
        # Compute Buchholz score
        for p in standings_list:
            buchholz = 0
            for opp_id in p.get("opponent_ids", []):
                opp = standings.get(opp_id, {})
                buchholz += opp.get("wins", 0)
            p["buchholz"] = buchholz
        return standings_list

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _seed_pairings(participants: List[Dict]) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        Pair participants by seed for Round 1: (1st, 2nd), (3rd, 4th), etc.
        Last participant gets a bye if count is odd.
        """
        pairings = []
        for i in range(0, len(participants) - 1, 2):
            pairings.append((participants[i], participants[i + 1]))
        if len(participants) % 2 == 1:
            pairings.append((participants[-1], None))  # bye
        return pairings

    @staticmethod
    def _dutch_pairing(
        participants: List[Dict],
        prior_pairings: set,
    ) -> List[Tuple[Dict, Optional[Dict]]]:
        """
        Dutch (fold-down) pairing algorithm:
        1. Sort participants by score group.
        2. Within each group, pair top half vs bottom half.
        3. If a pairing would be a rematch, fold down one position.
        4. Odd-one-out gets a bye.
        """
        if not participants:
            return []

        result_pairings: List[Tuple[Dict, Optional[Dict]]] = []
        remaining = list(participants)

        while len(remaining) > 1:
            p1 = remaining.pop(0)
            paired = False
            for idx, p2 in enumerate(remaining):
                key = frozenset([p1["id"], p2["id"]])
                if key not in prior_pairings:
                    result_pairings.append((p1, p2))
                    remaining.pop(idx)
                    paired = True
                    break
            if not paired:
                # Forced rematch (unavoidable in small tournaments)
                p2 = remaining.pop(0)
                result_pairings.append((p1, p2))

        if remaining:  # one participant left → bye
            result_pairings.append((remaining[0], None))

        return result_pairings

    @staticmethod
    def _create_round_nodes(
        bracket: "Bracket",
        round_number: int,
        pairings: List[Tuple[Dict, Optional[Dict]]],
    ) -> None:
        """Create BracketNode objects for a round's pairings."""
        from apps.tournaments.models.bracket import BracketNode

        # Determine position offset (after all prior nodes)
        from apps.tournaments.models.bracket import BracketNode as BN
        position_offset = BN.objects.filter(bracket=bracket).count()

        nodes_to_create = []
        for match_num, (p1, p2) in enumerate(pairings, start=1):
            is_bye = p2 is None
            nodes_to_create.append(BracketNode(
                bracket=bracket,
                position=position_offset + match_num,
                round_number=round_number,
                match_number_in_round=match_num,
                participant1_id=p1["id"],
                participant1_name=p1["name"],
                participant2_id=p2["id"] if p2 else None,
                participant2_name=p2["name"] if p2 else "",
                is_bye=is_bye,
                bracket_type=BracketNode.MAIN,
            ))
        BracketNode.objects.bulk_create(nodes_to_create)

        # Update total_matches on bracket
        bracket.total_matches = (bracket.total_matches or 0) + len(pairings)
        bracket.save(update_fields=["total_matches"])

    @staticmethod
    def _compute_standings(bracket: "Bracket") -> Dict[int, Dict]:
        """
        Build standings dict keyed by participant_id from completed nodes.
        Returns {pid: {id, name, seed, wins, losses, byes, opponent_ids}}.
        """
        from apps.tournaments.models.bracket import BracketNode
        from apps.tournaments.models.match import Match

        nodes = (
            BracketNode.objects.filter(bracket=bracket)
            .select_related("match")
        )

        participants: Dict[int, Dict] = {}

        def _ensure(pid, name, seed=9999):
            if pid not in participants:
                participants[pid] = {
                    "id": pid,
                    "name": name,
                    "seed": seed,
                    "wins": 0,
                    "losses": 0,
                    "byes": 0,
                    "opponent_ids": [],
                }

        for idx, node in enumerate(nodes):
            p1_id = node.participant1_id
            p2_id = node.participant2_id
            p1_name = node.participant1_name or ""
            p2_name = node.participant2_name or ""
            seed1 = (node.position)  # use position as tiebreaker seed

            if p1_id:
                _ensure(p1_id, p1_name, seed=seed1)
            if p2_id:
                _ensure(p2_id, p2_name, seed=seed1 + 1)

            if node.is_bye and p1_id:
                participants[p1_id]["byes"] += 1
                participants[p1_id]["wins"] += 1  # bye counts as win
                continue

            if not node.match:
                continue
            m = node.match
            if m.state not in (Match.COMPLETED, Match.FORFEIT):
                continue

            winner_id = node.winner_id or (m.winner_id if m else None)
            if not winner_id or not p1_id or not p2_id:
                continue

            participants[p1_id]["opponent_ids"].append(p2_id)
            participants[p2_id]["opponent_ids"].append(p1_id)

            if winner_id == p1_id:
                participants[p1_id]["wins"] += 1
                participants[p2_id]["losses"] += 1
            else:
                participants[p2_id]["wins"] += 1
                participants[p1_id]["losses"] += 1

        return participants

    @staticmethod
    def _get_prior_pairings(bracket: "Bracket") -> set:
        """Return a set of frozensets of (p1_id, p2_id) for all historical matches."""
        from apps.tournaments.models.bracket import BracketNode

        prior: set = set()
        for node in BracketNode.objects.filter(bracket=bracket).exclude(participant2_id=None):
            prior.add(frozenset([node.participant1_id, node.participant2_id]))
        return prior
