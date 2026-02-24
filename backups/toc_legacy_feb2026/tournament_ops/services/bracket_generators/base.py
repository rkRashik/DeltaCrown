"""
Base classes and protocols for pluggable bracket generators.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1 "Pluggable Bracket Generators"

This module defines the core interface that all bracket generators must implement,
ensuring a consistent API for generating tournament brackets across different formats.

Architecture Principles:
- DTO-only: All generators work exclusively with DTOs (TournamentDTO, TeamDTO, MatchDTO)
- No ORM usage: Generators are pure functions with no database dependencies
- Framework-light: Pure Python logic using only DTOs and primitives
- Extensible: New formats can be added by implementing the BracketGenerator protocol
"""

from typing import Protocol, runtime_checkable, List
from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.stage import StageDTO


@runtime_checkable
class BracketGenerator(Protocol):
    """
    Protocol defining the interface for tournament bracket generators.
    
    All bracket generators must implement this protocol to be compatible with
    the BracketEngineService orchestrator.
    
    Design Philosophy:
    - Accept DTOs as input (tournament config + participants)
    - Return list of MatchDTO instances representing the bracket structure
    - Validate configuration before generation
    - Support format-specific features (e.g., third-place match, seeding)
    
    Integration Points:
    - Epic 3.3: Stage transitions will wire match advancement logic
    - Epic 3.4: Bracket editor will modify returned match structures
    - Epic 3.5: Scoring integration will update match results
    """
    
    def generate_bracket(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate a complete bracket structure for the given tournament stage.
        
        Args:
            tournament: Tournament configuration (format, settings, etc.)
            stage: Stage configuration (type, settings, third_place_match, etc.)
            participants: Ordered list of teams (seeding order preserved)
        
        Returns:
            List of MatchDTO instances representing all matches in the bracket.
            Each MatchDTO contains:
            - round_number: Which round the match belongs to (1-indexed)
            - match_number: Position within the round (1-indexed)
            - stage_type: Format identifier (e.g., "winners", "losers", "main")
            - team1_id, team2_id: Participant IDs (None for TBD/bye matches)
            - Any format-specific metadata in MatchDTO.metadata field
        
        Raises:
            ValueError: If configuration is invalid for this generator
            
        TODO (Epic 3.3): Integration with StageTransitionService for match advancement
        TODO (Epic 3.4): Support for bracket editing (match reordering, manual seeding)
        TODO (Epic 3.5): Scoring integration for Swiss pairings based on standings
        """
        ...
    
    def validate_configuration(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participant_count: int
    ) -> tuple[bool, List[str]]:
        """
        Validate that the tournament/stage configuration is valid for this generator.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
            participant_count: Number of participants
        
        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if configuration is valid
            - error_messages: List of validation errors (empty if valid)
        
        Example validations:
        - Minimum participant count (e.g., 2+ for single elim, 4+ for double elim)
        - Required settings present (e.g., rounds_count for Swiss)
        - Format-specific constraints (e.g., power-of-two for strict single elim)
        """
        ...
    
    def supports_third_place_match(self) -> bool:
        """
        Indicates whether this generator supports third-place matches.
        
        Returns:
            True if third-place match is supported (e.g., single/double elim)
            False otherwise (e.g., round-robin, Swiss)
        """
        ...


# ============================================================================
# Helper Functions for Bracket Generation
# ============================================================================

def calculate_bye_count(participant_count: int) -> int:
    """
    Calculate number of byes needed to reach next power of two.
    
    Args:
        participant_count: Number of participants
    
    Returns:
        Number of byes needed (0 if already power of two)
    
    Example:
        >>> calculate_bye_count(6)
        2  # 6 teams → 8 slots = 2 byes
        >>> calculate_bye_count(8)
        0  # Already power of two
    """
    if participant_count <= 0:
        return 0
    
    # Find next power of two
    next_power = 1
    while next_power < participant_count:
        next_power *= 2
    
    return next_power - participant_count


def next_power_of_two(n: int) -> int:
    """
    Find the smallest power of two greater than or equal to n.
    
    Args:
        n: Input number
    
    Returns:
        Next power of two
    
    Example:
        >>> next_power_of_two(6)
        8
        >>> next_power_of_two(8)
        8
    """
    if n <= 0:
        return 1
    
    power = 1
    while power < n:
        power *= 2
    
    return power


def seed_participants_with_byes(
    participants: List[TeamDTO],
    bye_count: int
) -> List[TeamDTO | None]:
    """
    Insert byes into participant list following standard seeding rules.
    
    Byes are distributed to highest seeds (top teams) to minimize their
    matches in early rounds.
    
    Args:
        participants: Ordered list of teams (highest seed first)
        bye_count: Number of byes to insert
    
    Returns:
        List with None values representing byes, length = next_power_of_two
    
    Example:
        >>> teams = [Team1, Team2, Team3, Team4, Team5, Team6]
        >>> seed_participants_with_byes(teams, 2)
        [Team1, None, Team2, None, Team3, Team4, Team5, Team6]
        # Top 2 seeds get byes
    """
    if bye_count == 0:
        return participants.copy()
    
    total_slots = len(participants) + bye_count
    seeded = [None] * total_slots
    
    # Distribute byes to top seeds
    # Standard approach: byes go to slots that advance immediately
    bye_positions = set(range(bye_count))
    
    participant_idx = 0
    for slot_idx in range(total_slots):
        if slot_idx not in bye_positions:
            seeded[slot_idx] = participants[participant_idx]
            participant_idx += 1
    
    return seeded


def generate_round_robin_pairings(participant_count: int) -> List[tuple[int, int]]:
    """
    Generate all unique pairings for round-robin using circle method.
    
    Uses the standard "rotating table" algorithm to ensure each participant
    plays every other participant exactly once.
    
    Args:
        participant_count: Number of participants
    
    Returns:
        List of (index1, index2) tuples representing all unique pairings
        Indices are 0-based positions in the participant list
    
    Example:
        >>> generate_round_robin_pairings(4)
        [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
        # All unique pairs, no self-matches
    
    Reference: https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
    """
    if participant_count < 2:
        return []
    
    # Handle odd number by adding dummy participant
    n = participant_count
    if n % 2 == 1:
        n += 1
    
    pairings = []
    participants = list(range(n))
    
    # Circle method: fix first position, rotate others
    for round_num in range(n - 1):
        for i in range(n // 2):
            idx1 = participants[i]
            idx2 = participants[n - 1 - i]
            
            # Skip if dummy participant (for odd counts)
            if idx1 < participant_count and idx2 < participant_count:
                pairings.append((idx1, idx2))
        
        # Rotate all except first position
        participants = [participants[0]] + [participants[-1]] + participants[1:-1]
    
    return pairings
