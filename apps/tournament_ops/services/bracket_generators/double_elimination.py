"""
Double Elimination Bracket Generator.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1.3

Generates double-elimination tournament brackets with winners and losers brackets.
Each team must lose twice to be eliminated.

Features:
- Winners bracket (standard single-elimination structure)
- Losers bracket (teams dropping from winners bracket)
- Grand finals (winners bracket champion vs losers bracket champion)
- Grand finals reset if losers bracket champion wins first match

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


class DoubleEliminationGenerator:
    """
    Double elimination bracket generator.
    
    Tournament Structure:
    - Winners Bracket: Standard single elimination
    - Losers Bracket: Teams dropping from winners bracket
    - Grand Finals: WB champion vs LB champion
    - Grand Finals Reset: If LB champion wins, play one more match (both have 1 loss)
    
    Bracket Flow:
    1. All teams start in winners bracket
    2. First loss → drop to losers bracket
    3. Second loss → eliminated
    4. Losers bracket has interleaving rounds with winners bracket drops
    
    Example (4 teams):
        WB Round 1: 1v4, 2v3
        LB Round 1: Loser(1v4) vs Loser(2v3)
        WB Finals: Winner(1v4) vs Winner(2v3)
        LB Finals: Winner(LBR1) vs Loser(WB Finals)
        Grand Finals: Winner(WB Finals) vs Winner(LB Finals)
    
    TODO (Epic 3.3): Wire match advancement logic via StageTransitionService
    TODO (Epic 3.4): Support bracket editing for manual advancement overrides
    """
    
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate double elimination bracket.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participants: Ordered list of teams (seeding order)
        
        Returns:
            List of MatchDTO instances for winners bracket, losers bracket, and grand finals
        
        Raises:
            ValueError: If fewer than 4 participants (minimum for double elim)
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
        wb_rounds = int(math.log2(total_slots))
        
        matches = []
        
        # Generate winners bracket
        wb_matches = self._generate_winners_bracket(
            rounds=wb_rounds,
            teams=seeded,
            stage_id=stage.id if stage.id else 0,
            tournament_id=tournament.id if tournament.id else 0,
        )
        matches.extend(wb_matches)
        
        # Generate losers bracket
        lb_matches = self._generate_losers_bracket(
            wb_rounds=wb_rounds,
            participant_count=len(seeded),
            stage_id=stage.id if stage.id else 0,
            tournament_id=tournament.id if tournament.id else 0,
        )
        matches.extend(lb_matches)
        
        # Generate grand finals
        gf_matches = self._generate_grand_finals(
            wb_rounds=wb_rounds,
            stage_id=stage.id if stage.id else 0,
            tournament_id=tournament.id if tournament.id else 0,
            grand_finals_reset=stage.metadata.get("grand_finals_reset", True) if stage.metadata else True,
        )
        matches.extend(gf_matches)
        
        return matches
    
    def _generate_winners_bracket(
        self,
        rounds: int,
        teams: List[TeamDTO | None],
        stage_id: int,
        tournament_id: int,
    ) -> List[MatchDTO]:
        """
        Generate winners bracket (standard single-elimination structure).
        
        Args:
            rounds: Number of rounds in winners bracket
            teams: Seeded participants (may include None for byes)
            stage_id: Stage identifier
            tournament_id: Tournament identifier
        
        Returns:
            List of MatchDTO instances for winners bracket
        """
        matches = []
        current_round_teams = teams
        
        for round_num in range(1, rounds + 1):
            match_number = 1
            round_matches = []
            
            # Pair teams: 1v2, 3v4, 5v6, etc.
            for i in range(0, len(current_round_teams), 2):
                team1 = current_round_teams[i]
                team2 = current_round_teams[i + 1] if i + 1 < len(current_round_teams) else None
                
                # Skip if both teams are byes
                if team1 is None and team2 is None:
                    continue
                
                match = MatchDTO(
                    id=None,
                    tournament_id=tournament_id,
                    stage_id=stage_id,
                    round_number=round_num,
                    match_number=match_number,
                    stage_type="winners",  # Winners bracket
                    team1_id=team1.id if team1 else None,
                    team2_id=team2.id if team2 else None,
                    team1_name=team1.name if team1 else "BYE",
                    team2_name=team2.name if team2 else "BYE",
                    status="pending",
                    metadata={
                        "bracket_type": "double_elimination",
                        "bracket_stage": "winners",
                        "has_bye": team1 is None or team2 is None,
                    },
                )
                round_matches.append(match)
                match_number += 1
            
            matches.extend(round_matches)
            
            # Prepare next round (winners TBD)
            current_round_teams = [None] * (len(current_round_teams) // 2)
        
        return matches
    
    def _generate_losers_bracket(
        self,
        wb_rounds: int,
        participant_count: int,
        stage_id: int,
        tournament_id: int,
    ) -> List[MatchDTO]:
        """
        Generate losers bracket.
        
        Losers bracket has 2*(wb_rounds - 1) rounds:
        - Odd rounds: Droppers from winners bracket face each other
        - Even rounds: Winners of odd rounds face each other
        
        Args:
            wb_rounds: Number of winners bracket rounds
            participant_count: Total number of participants
            stage_id: Stage identifier
            tournament_id: Tournament identifier
        
        Returns:
            List of MatchDTO instances for losers bracket
        """
        matches = []
        
        # Losers bracket rounds = 2 * (WB rounds - 1)
        # This creates the interleaving pattern where WB droppers enter at specific points
        lb_rounds = 2 * (wb_rounds - 1)
        
        # Start with participants who lost in WB Round 1
        # Number of LB Round 1 matches = half of WB Round 1 matches
        current_match_count = participant_count // 4
        
        for lb_round_num in range(1, lb_rounds + 1):
            round_matches = []
            
            for match_num in range(1, current_match_count + 1):
                match = MatchDTO(
                    id=None,
                    tournament_id=tournament_id,
                    stage_id=stage_id,
                    round_number=lb_round_num,
                    match_number=match_num,
                    stage_type="losers",  # Losers bracket
                    team1_id=None,  # TBD: Based on winners bracket results
                    team2_id=None,  # TBD: Based on winners bracket results
                    team1_name="TBD",
                    team2_name="TBD",
                    status="pending",
                    metadata={
                        "bracket_type": "double_elimination",
                        "bracket_stage": "losers",
                        "losers_round": lb_round_num,
                    },
                )
                round_matches.append(match)
            
            matches.extend(round_matches)
            
            # Update match count for next round
            # Even rounds: same count (consolidation)
            # Odd rounds: half count (advancement)
            if lb_round_num % 2 == 1:
                current_match_count = current_match_count // 2
        
        return matches
    
    def _generate_grand_finals(
        self,
        wb_rounds: int,
        stage_id: int,
        tournament_id: int,
        grand_finals_reset: bool = True,
    ) -> List[MatchDTO]:
        """
        Generate grand finals matches.
        
        Grand Finals:
        - Match 1: WB champion (0 losses) vs LB champion (1 loss)
        - Match 2 (reset): If LB champion wins match 1, both have 1 loss → play again
        
        Args:
            wb_rounds: Number of winners bracket rounds
            stage_id: Stage identifier
            tournament_id: Tournament identifier
            grand_finals_reset: Whether to generate reset match
        
        Returns:
            List of MatchDTO instances for grand finals (1 or 2 matches)
        """
        matches = []
        
        # Grand Finals Match 1
        gf_match = MatchDTO(
            id=None,
            tournament_id=tournament_id,
            stage_id=stage_id,
            round_number=wb_rounds + 1,  # After all WB rounds
            match_number=1,
            stage_type="grand_finals",
            team1_id=None,  # TBD: Winners bracket champion
            team2_id=None,  # TBD: Losers bracket champion
            team1_name="WB Champion (TBD)",
            team2_name="LB Champion (TBD)",
            status="pending",
            metadata={
                "bracket_type": "double_elimination",
                "bracket_stage": "grand_finals",
                "is_reset_eligible": grand_finals_reset,
            },
        )
        matches.append(gf_match)
        
        # Grand Finals Reset (if enabled)
        if grand_finals_reset:
            gf_reset = MatchDTO(
                id=None,
                tournament_id=tournament_id,
                stage_id=stage_id,
                round_number=wb_rounds + 2,
                match_number=1,
                stage_type="grand_finals_reset",
                team1_id=None,  # TBD: Conditional on GF match 1 result
                team2_id=None,  # TBD: Conditional on GF match 1 result
                team1_name="TBD (if reset needed)",
                team2_name="TBD (if reset needed)",
                status="pending",
                metadata={
                    "bracket_type": "double_elimination",
                    "bracket_stage": "grand_finals_reset",
                    "is_conditional": True,
                    "condition": "Only played if LB champion wins GF match 1",
                },
            )
            matches.append(gf_reset)
        
        return matches
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participant_count: int
    ) -> tuple[bool, List[str]]:
        """
        Validate double elimination configuration.
        
        Requirements:
        - At least 4 participants (minimum meaningful double elim)
        - Participant count reasonable (<= 128 for safety)
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participant_count: Number of participants
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if participant_count < 4:
            errors.append("Double elimination requires at least 4 participants")
        
        if participant_count > 128:
            errors.append("Double elimination supports maximum 128 participants")
        
        return (len(errors) == 0, errors)
    
    def supports_third_place_match(self) -> bool:
        """
        Double elimination does not need third-place match.
        
        The losers bracket finals already determines 3rd place.
        """
        return False
