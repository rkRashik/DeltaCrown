"""
Round Robin Bracket Generator.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1.4

Generates round-robin tournament brackets where every team plays every other team exactly once.

Features:
- All teams play all other teams once
- No elimination (all teams play full schedule)
- Uses circle method algorithm for optimal scheduling
- Supports 3-20 participants (practical limits)

Architecture:
- DTO-only: No ORM imports, works purely with DTOs
- Pure function: Deterministic output for given inputs
- No side effects: Does not persist to database
"""

from typing import List

from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.stage import StageDTO

from .base import BracketGenerator, generate_round_robin_pairings


class RoundRobinGenerator:
    """
    Round-robin bracket generator.
    
    Tournament Structure:
    - Every team plays every other team exactly once
    - Total matches = N * (N-1) / 2 where N = participant count
    - No elimination - all teams complete full schedule
    - Final standings determined by wins/points
    
    Scheduling:
    - Uses circle method (rotating table) algorithm
    - Ensures balanced schedule (each team plays once per round when possible)
    - Handles odd participant counts (one team has bye each round)
    
    Example (4 teams):
        Round 1: 1v2, 3v4
        Round 2: 1v3, 2v4
        Round 3: 1v4, 2v3
        Total: 6 matches (4*3/2)
    """
    
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate round-robin bracket.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participants: List of teams (order doesn't affect matchups)
        
        Returns:
            List of MatchDTO instances for all matches
        
        Raises:
            ValueError: If fewer than 3 participants (minimum for round-robin)
        """
        is_valid, errors = self.validate_configuration(tournament, stage, len(participants))
        if not is_valid:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        participant_count = len(participants)
        
        # Generate all unique pairings using circle method
        pairings = generate_round_robin_pairings(participant_count)
        
        # Create matches from pairings
        matches = []
        match_number = 1
        
        # Group pairings into rounds (balanced scheduling)
        matches_per_round = participant_count // 2
        current_round = 1
        round_match_count = 0
        
        for idx1, idx2 in pairings:
            team1 = participants[idx1]
            team2 = participants[idx2]
            
            match = MatchDTO(
                id=None,
                tournament_id=tournament.id if tournament.id else 0,
                stage_id=stage.id if stage.id else 0,
                round_number=current_round,
                match_number=round_match_count + 1,
                stage_type="main",
                team_a_id=team1.id,
                team_b_id=team2.id,
                team1_name=team1.name,
                team2_name=team2.name,
                state="pending",
                metadata={
                    "bracket_type": "round_robin",
                    "total_rounds": participant_count - 1 if participant_count % 2 == 0 else participant_count,
                    "pairing_index": match_number - 1,
                },
            )
            matches.append(match)
            
            match_number += 1
            round_match_count += 1
            
            # Move to next round when current round is full
            if round_match_count >= matches_per_round:
                current_round += 1
                round_match_count = 0
        
        return matches
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participant_count: int
    ) -> tuple[bool, List[str]]:
        """
        Validate round-robin configuration.
        
        Requirements:
        - At least 3 participants (minimum meaningful round-robin)
        - Participant count reasonable (<= 20 for practical scheduling)
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participant_count: Number of participants
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if participant_count < 3:
            errors.append("Round-robin requires at least 3 participants")
        
        if participant_count > 20:
            errors.append("Round-robin supports maximum 20 participants (practical limit)")
        
        return (len(errors) == 0, errors)
    
    def supports_third_place_match(self) -> bool:
        """Round-robin does not have third-place matches (all teams play all others)."""
        return False
