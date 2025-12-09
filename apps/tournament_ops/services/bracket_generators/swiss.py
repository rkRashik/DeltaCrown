"""
Swiss System Bracket Generator.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1.5

Generates Swiss-system tournament brackets with pairing based on current standings.

Features:
- Fixed number of rounds (typically log2(N) or log2(N)+1)
- First round: Seeded pairing (top half vs bottom half)
- Subsequent rounds: Pair teams with similar records
- No elimination - all teams play all rounds

Architecture:
- DTO-only: No ORM imports, works purely with DTOs
- Pure function: Deterministic output for given inputs
- First-round implementation complete
- Subsequent rounds: Stub with TODO for Epic 3.5 scoring integration
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
    - Rounds 2+: Pair teams with same/similar records
    - All teams play all rounds
    - Final standings by total wins/points
    
    Pairing Algorithm:
    - First round: Top half vs bottom half by seed
    - Subsequent rounds: Same-record pairing (1st vs 2nd, 3rd vs 4th, etc.)
    - Avoid repeat pairings when possible
    - Handle odd counts with byes
    
    Example (8 teams, 3 rounds):
        Round 1: 1v5, 2v6, 3v7, 4v8
        Round 2: Pair 2-0 teams, 1-1 teams, 0-2 teams
        Round 3: Final pairings based on standings
    
    TODO (Epic 3.5): Integrate with scoring system for rounds 2+ pairings
    TODO (Epic 3.3): Wire standings calculation via StageTransitionService
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
                stage_type="main",  # Swiss has single pool
                team1_id=team1.id,
                team2_id=team2.id if team2 else None,
                team1_name=team1.name,
                team2_name=team2.name if team2 else "BYE",
                status="pending",
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
        
        STUB IMPLEMENTATION for Epic 3.1.
        
        Algorithm:
        1. Sort teams by current record (wins, then tiebreakers)
        2. Group teams by record (2-0, 1-1, 0-2, etc.)
        3. Within each group, pair sequentially (1v2, 3v4, etc.)
        4. Avoid repeat pairings from previous rounds
        
        Args:
            round_number: Current round number (2+)
            standings: List of team standings dicts with:
                - team_id: Team identifier
                - wins: Number of wins
                - losses: Number of losses
                - points: Total points scored
            previous_pairings: List of (team1_id, team2_id) tuples from prior rounds
        
        Returns:
            List of (team1_id, team2_id) tuples for this round
        
        TODO (Epic 3.5): Implement full pairing algorithm with:
            - Record-based grouping
            - Tiebreaker handling (opponent strength, points, etc.)
            - Repeat pairing avoidance
            - Integration with GameRulesEngine scoring
        
        Reference: https://en.wikipedia.org/wiki/Swiss-system_tournament#Pairing_algorithm
        """
        # STUB: Return empty list
        # Full implementation requires scoring integration (Epic 3.5)
        
        # Sort standings by record
        sorted_standings = sorted(
            standings,
            key=lambda s: (s.get("wins", 0), s.get("points", 0)),
            reverse=True
        )
        
        # Simple pairing: sequential pairs (no record grouping yet)
        pairings = []
        used_teams = set()
        
        for i in range(0, len(sorted_standings) - 1, 2):
            team1 = sorted_standings[i]
            team2 = sorted_standings[i + 1]
            
            team1_id = team1["team_id"]
            team2_id = team2["team_id"]
            
            # TODO: Check for repeat pairings and adjust
            # TODO: Implement proper record-based grouping
            
            if team1_id not in used_teams and team2_id not in used_teams:
                pairings.append((team1_id, team2_id))
                used_teams.add(team1_id)
                used_teams.add(team2_id)
        
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
