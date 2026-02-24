"""
Single Elimination Bracket Generator.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1.2

Generates single-elimination tournament brackets with automatic bye handling
for non-power-of-two participant counts.

Features:
- Handles 2 to 128+ participants
- Automatic bye placement for non-power-of-two counts
- Optional third-place match support
- Standard seeding (1 vs lowest, 2 vs 2nd-lowest, etc.)

Architecture:
- DTO-only: No ORM imports, works purely with DTOs
- Pure function: Deterministic output for given inputs
- No side effects: Does not persist to database
"""

from typing import List
import math

from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.stage import StageDTO

from .base import (
    BracketGenerator,
    calculate_bye_count,
    next_power_of_two,
    seed_participants_with_byes,
)


class SingleEliminationGenerator:
    """
    Single elimination bracket generator.
    
    Tournament Structure:
    - Each match eliminates the loser
    - Winner advances to next round
    - Continues until one team remains (champion)
    - Optional third-place match between losing semifinalists
    
    Bye Handling:
    - Non-power-of-two counts automatically get byes
    - Byes distributed to top seeds
    - Teams with byes advance directly to round 2
    
    Example (6 teams):
        Round 1: Team3 vs Team4, Team5 vs Team6
        Round 2: Team1 vs Winner(3v4), Team2 vs Winner(5v6)
        Finals: Winner(R2-1) vs Winner(R2-2)
    """
    
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate single elimination bracket.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration (includes third_place_match setting)
            participants: Ordered list of teams (seeding order)
        
        Returns:
            List of MatchDTO instances for all bracket matches
        
        Raises:
            ValueError: If fewer than 2 participants
        """
        is_valid, errors = self.validate_configuration(tournament, stage, len(participants))
        if not is_valid:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        participant_count = len(participants)
        bye_count = calculate_bye_count(participant_count)
        total_slots = next_power_of_two(participant_count)
        
        # Seed participants with byes
        seeded = seed_participants_with_byes(participants, bye_count)
        
        # Calculate bracket structure
        rounds = int(math.log2(total_slots))
        matches = []
        
        # Generate matches round by round
        current_round_teams = seeded
        
        for round_num in range(1, rounds + 1):
            round_matches = self._generate_round_matches(
                round_num=round_num,
                teams=current_round_teams,
                stage_id=stage.id if stage.id else 0,
                tournament_id=tournament.id if tournament.id else 0,
            )
            matches.extend(round_matches)
            
            # Prepare next round (winners TBD)
            current_round_teams = [None] * (len(current_round_teams) // 2)
        
        # Add third-place match if configured
        third_place_enabled = stage.config.get("third_place_match", False) if stage.config else False
        if third_place_enabled and rounds >= 2:
            third_place_match = self._generate_third_place_match(
                rounds=rounds,
                stage_id=stage.id if stage.id else 0,
                tournament_id=tournament.id if tournament.id else 0,
            )
            matches.append(third_place_match)
        
        return matches
    
    def _generate_round_matches(
        self,
        round_num: int,
        teams: List[TeamDTO | None],
        stage_id: int,
        tournament_id: int,
    ) -> List[MatchDTO]:
        """
        Generate all matches for a single round.
        
        Args:
            round_num: Current round number (1-indexed)
            teams: List of teams in this round (may include None for byes)
            stage_id: Stage identifier
            tournament_id: Tournament identifier
        
        Returns:
            List of MatchDTO instances for this round
        """
        matches = []
        match_number = 1
        
        # Pair teams: 1v2, 3v4, 5v6, etc.
        for i in range(0, len(teams), 2):
            team1 = teams[i]
            team2 = teams[i + 1] if i + 1 < len(teams) else None
            
            # Skip if both teams are byes (shouldn't happen with proper seeding)
            if team1 is None and team2 is None:
                continue
            
            match = MatchDTO(
                id=0,  # Will be assigned on persistence
                tournament_id=tournament_id,
                team_a_id=team1.id if team1 else 0,
                team_b_id=team2.id if team2 else 0,
                round_number=round_num,
                stage=f"Round {round_num}",
                state="pending",
                scheduled_time=None,
                result=None,
            )
            matches.append(match)
            match_number += 1
        
        return matches
    
    def _generate_third_place_match(
        self,
        rounds: int,
        stage_id: int,
        tournament_id: int,
    ) -> MatchDTO:
        """
        Generate third-place match (losers of semifinals).
        
        Args:
            rounds: Total number of rounds in bracket
            stage_id: Stage identifier
            tournament_id: Tournament identifier
        
        Returns:
            MatchDTO for third-place match
        """
        # Third place match is between losing semifinalists
        # Place it after finals (round = rounds + 1)
        return MatchDTO(
            id=0,
            tournament_id=tournament_id,
            team_a_id=0,  # TBD: Loser of semifinal 1
            team_b_id=0,  # TBD: Loser of semifinal 2
            round_number=rounds + 1,
            stage="Third Place",
            state="pending",
            scheduled_time=None,
            result=None,
        )
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participant_count: int
    ) -> tuple[bool, List[str]]:
        """
        Validate single elimination configuration.
        
        Requirements:
        - At least 2 participants
        - Participant count reasonable (<= 256 for safety)
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participant_count: Number of participants
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if participant_count < 2:
            errors.append("Single elimination requires at least 2 participants")
        
        if participant_count > 256:
            errors.append("Single elimination supports maximum 256 participants")
        
        return (len(errors) == 0, errors)
    
    def supports_third_place_match(self) -> bool:
        """Single elimination supports third-place matches."""
        return True
