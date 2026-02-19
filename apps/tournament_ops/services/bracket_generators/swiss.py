"""
Swiss System Bracket Generator.

Phase 3, Epic 3.1 + Phase 2, Task 2.3: Complete Swiss implementation.

Generates Swiss-system tournament brackets with pairing based on current standings.

Features:
- Fixed number of rounds (typically log2(N) or log2(N)+1)
- First round: Seeded pairing (top half vs bottom half)
- Subsequent rounds: Record-based grouping, repeat avoidance, tiebreakers
- No elimination — all teams play all rounds
- Bye handling for odd participant counts

Architecture:
- DTO-only: No ORM imports, works purely with DTOs
- Pure function: Deterministic output for given inputs
- First-round: Seeded pairing (1v(N/2+1))
- Rounds 2+: Score bracket grouping with sliding pair algorithm
"""

from typing import List, Dict, Any

from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.stage import StageDTO

from .base import BracketGenerator


class SwissSystemGenerator:
    """
    Swiss-system bracket generator.
    
    Tournament Structure:
    - Fixed number of rounds (not elimination-based)
    - Round 1: Seeded pairing (1v(N/2+1), 2v(N/2+2), etc.)
    - Rounds 2+: Pair teams with same/similar records, avoid repeats
    - All teams play all rounds
    - Final standings by total wins/points
    
    Pairing Algorithm:
    - First round: Top half vs bottom half by seed
    - Subsequent rounds: Score-bracket grouping + sliding pair with repeat avoidance
    - Handle odd counts with byes (lowest-ranked unpaired gets bye)
    
    Example (8 teams, 3 rounds):
        Round 1: 1v5, 2v6, 3v7, 4v8
        Round 2: Pair 2-0 teams, 1-1 teams, 0-2 teams
        Round 3: Final pairings based on standings
    """
    
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate Swiss-system bracket.
        
        Currently generates first-round pairings only. Subsequent rounds
        will be generated dynamically based on match results.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration (must include rounds_count in metadata)
            participants: Ordered list of teams (seeding order)
        
        Returns:
            List of MatchDTO instances for round 1
        
        Raises:
            ValueError: If configuration invalid or rounds_count missing
        
        TODO (Epic 3.5): Generate all rounds with standings-based pairing
        """
        is_valid, errors = self.validate_configuration(tournament, stage, len(participants))
        if not is_valid:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        rounds_count = self._get_rounds_count(stage)
        participant_count = len(participants)
        
        # Generate first round pairings
        first_round_matches = self._generate_first_round(
            participants=participants,
            stage_id=stage.id if stage.id else 0,
            tournament_id=tournament.id if tournament.id else 0,
            rounds_count=rounds_count,
        )
        
        # TODO (Epic 3.5): Generate subsequent rounds
        # For now, only return first round
        # Subsequent rounds will be generated after scoring integration
        return first_round_matches
    
    def _generate_first_round(
        self,
        participants: List[TeamDTO],
        stage_id: int,
        tournament_id: int,
        rounds_count: int,
    ) -> List[MatchDTO]:
        """
        Generate first round pairings (top half vs bottom half).
        
        Standard Swiss pairing: divide by seed, pair across halves:
        - Seed 1 vs Seed (N/2 + 1)
        - Seed 2 vs Seed (N/2 + 2)
        - etc.
        
        Args:
            participants: Ordered teams (seeding order)
            stage_id: Stage identifier
            tournament_id: Tournament identifier
            rounds_count: Total rounds in Swiss system
        
        Returns:
            List of MatchDTO instances for round 1
        """
        matches = []
        participant_count = len(participants)
        half = participant_count // 2
        
        # Handle odd count with bye
        has_bye = participant_count % 2 == 1
        
        for i in range(half):
            team1 = participants[i]
            team2_idx = half + i
            
            # Last team gets bye if odd count
            if has_bye and team2_idx >= participant_count:
                team2 = None
            else:
                team2 = participants[team2_idx]
            
            match = MatchDTO(
                id=None,
                tournament_id=tournament_id,
                stage_id=stage_id,
                round_number=1,
                match_number=i + 1,
                stage_type="main",
                team_a_id=team1.id,
                team_b_id=team2.id if team2 else None,
                team1_name=team1.name,
                team2_name=team2.name if team2 else "BYE",
                state="pending",
                metadata={
                    "bracket_type": "swiss",
                    "total_rounds": rounds_count,
                    "pairing_method": "first_round_seeded",
                    "has_bye": team2 is None,
                },
            )
            matches.append(match)
        
        # If odd count, add bye match for last team
        if has_bye:
            bye_team = participants[-1]
            bye_match = MatchDTO(
                id=None,
                tournament_id=tournament_id,
                stage_id=stage_id,
                round_number=1,
                match_number=half + 1,
                stage_type="main",
                team1_id=bye_team.id,
                team2_id=None,
                team1_name=bye_team.name,
                team2_name="BYE",
                status="pending",
                metadata={
                    "bracket_type": "swiss",
                    "total_rounds": rounds_count,
                    "pairing_method": "bye",
                    "has_bye": True,
                },
            )
            matches.append(bye_match)
        
        return matches
    
    def generate_subsequent_round(
        self,
        round_number: int,
        standings: List[Dict[str, Any]],
        previous_pairings: List[tuple[int, int]],
    ) -> List[tuple[int, int]]:
        """
        Generate pairings for rounds 2+ based on current standings.
        
        Algorithm (standard Swiss):
        1. Sort teams by record (wins desc, then points desc as tiebreaker)
        2. Group teams by win count (score bracket)
        3. Within each score bracket, pair top vs next available
        4. Avoid repeat pairings from previous rounds (slide down if needed)
        5. Handle odd counts with a bye (lowest-ranked unpaired player)
        
        Args:
            round_number: Current round number (2+)
            standings: List of team standings dicts with:
                - team_id: Team identifier
                - wins: Number of wins
                - losses: Number of losses
                - points: Total points scored (tiebreaker)
                - buchholz: (optional) sum of opponents' wins (SOS tiebreaker)
            previous_pairings: List of (team1_id, team2_id) tuples from prior rounds
        
        Returns:
            List of (team1_id, team2_id) tuples for this round.
            A tuple (team_id, None) indicates a bye.
        
        Reference: https://en.wikipedia.org/wiki/Swiss-system_tournament#Pairing_algorithm
        """
        if not standings:
            return []
        
        # Build set of previous pairings for O(1) lookup (unordered)
        paired_before: set[frozenset[int]] = set()
        for t1, t2 in previous_pairings:
            paired_before.add(frozenset((t1, t2)))
        
        def _already_paired(a: int, b: int) -> bool:
            return frozenset((a, b)) in paired_before
        
        # Sort standings: primary = wins (desc), secondary = points (desc),
        # tertiary = buchholz (desc) for tie-breaking
        sorted_standings = sorted(
            standings,
            key=lambda s: (
                s.get("wins", 0),
                s.get("points", 0),
                s.get("buchholz", 0),
            ),
            reverse=True,
        )
        
        # Group teams by win count (score bracket)
        from itertools import groupby
        
        score_brackets: List[List[Dict[str, Any]]] = []
        for _key, group in groupby(sorted_standings, key=lambda s: s.get("wins", 0)):
            score_brackets.append(list(group))
        
        # Flatten into ordered list of team_ids for pairing
        ordered_ids = [s["team_id"] for s in sorted_standings]
        
        # Pair using sliding algorithm within score brackets
        pairings: List[tuple[int, int]] = []
        used: set[int] = set()
        
        # Process each score bracket
        for bracket_teams in score_brackets:
            bracket_ids = [t["team_id"] for t in bracket_teams if t["team_id"] not in used]
            
            i = 0
            while i < len(bracket_ids):
                team_a = bracket_ids[i]
                if team_a in used:
                    i += 1
                    continue
                
                # Find best opponent: first unpaired, non-repeat in this bracket
                paired = False
                for j in range(i + 1, len(bracket_ids)):
                    team_b = bracket_ids[j]
                    if team_b in used:
                        continue
                    if not _already_paired(team_a, team_b):
                        pairings.append((team_a, team_b))
                        used.add(team_a)
                        used.add(team_b)
                        paired = True
                        break
                
                if not paired:
                    # No valid opponent in this bracket — defer to cross-bracket pairing below
                    pass
                
                i += 1
        
        # Cross-bracket pairing for any remaining unpaired teams
        remaining = [tid for tid in ordered_ids if tid not in used]
        i = 0
        while i < len(remaining) - 1:
            team_a = remaining[i]
            paired = False
            for j in range(i + 1, len(remaining)):
                team_b = remaining[j]
                if not _already_paired(team_a, team_b):
                    pairings.append((team_a, team_b))
                    used.add(team_a)
                    used.add(team_b)
                    remaining = [tid for tid in remaining if tid not in used]
                    paired = True
                    break
            if not paired:
                # Last resort: pair even if it's a repeat (Swiss allows rare repeats)
                if i + 1 < len(remaining):
                    pairings.append((remaining[i], remaining[i + 1]))
                    used.add(remaining[i])
                    used.add(remaining[i + 1])
                    remaining = [tid for tid in remaining if tid not in used]
                else:
                    break
            i = 0  # restart from beginning of remaining
        
        # Handle bye for odd participant count
        final_remaining = [tid for tid in ordered_ids if tid not in used]
        if final_remaining:
            # Lowest-ranked unpaired team gets bye
            pairings.append((final_remaining[-1], None))
        
        return pairings
    
    def _get_rounds_count(self, stage: StageDTO) -> int:
        """
        Extract rounds count from stage metadata.
        
        Args:
            stage: Stage configuration
        
        Returns:
            Number of Swiss rounds
        
        Raises:
            ValueError: If rounds_count not specified
        """
        if not stage.metadata:
            raise ValueError("Swiss system requires 'rounds_count' in stage metadata")
        
        rounds_count = stage.metadata.get("rounds_count")
        if not rounds_count:
            raise ValueError("Swiss system requires 'rounds_count' in stage metadata")
        
        return int(rounds_count)
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participant_count: int
    ) -> tuple[bool, List[str]]:
        """
        Validate Swiss system configuration.
        
        Requirements:
        - At least 4 participants (minimum meaningful Swiss)
        - rounds_count specified in stage metadata
        - Reasonable round count (typically 3-10)
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participant_count: Number of participants
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if participant_count < 4:
            errors.append("Swiss system requires at least 4 participants")
        
        if participant_count > 64:
            errors.append("Swiss system supports maximum 64 participants")
        
        # Check rounds_count in metadata
        if not stage.metadata or "rounds_count" not in stage.metadata:
            errors.append("Swiss system requires 'rounds_count' in stage metadata")
        else:
            rounds_count = stage.metadata.get("rounds_count")
            if not isinstance(rounds_count, int) or rounds_count < 1:
                errors.append("Swiss 'rounds_count' must be positive integer")
            elif rounds_count > 10:
                errors.append("Swiss system supports maximum 10 rounds")
        
        return (len(errors) == 0, errors)
    
    def supports_third_place_match(self) -> bool:
        """Swiss system does not have third-place matches (standings-based)."""
        return False
