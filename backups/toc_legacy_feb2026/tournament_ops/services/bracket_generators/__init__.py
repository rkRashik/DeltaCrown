"""
Pluggable Bracket Generators.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1

This module exports all bracket generators and the base interface.
Generators are DTO-based, framework-light, and support multiple tournament formats.

Available Formats:
- Single Elimination: Standard knockout bracket with bye handling
- Double Elimination: Winners + losers brackets with grand finals
- Round Robin: Every team plays every other team once
- Swiss System: Fixed rounds with standings-based pairing

Usage:
    from apps.tournament_ops.services.bracket_generators import (
        SingleEliminationGenerator,
        DoubleEliminationGenerator,
        RoundRobinGenerator,
        SwissSystemGenerator,
    )
    
    generator = SingleEliminationGenerator()
    matches = generator.generate_bracket(tournament_dto, stage_dto, teams)

Architecture:
- All generators implement the BracketGenerator protocol
- No ORM usage - works purely with DTOs
- Generators return List[MatchDTO] representing bracket structure
- Tournament persistence handled separately by tournaments domain

Integration Points:
- Epic 3.3: StageTransitionService wires match advancement
- Epic 3.4: Bracket editor modifies generated structures
- Epic 3.5: Scoring integration for Swiss subsequent rounds
"""

from .base import (
    BracketGenerator,
    calculate_bye_count,
    next_power_of_two,
    seed_participants_with_byes,
    generate_round_robin_pairings,
)

from .single_elimination import SingleEliminationGenerator
from .double_elimination import DoubleEliminationGenerator
from .round_robin import RoundRobinGenerator
from .swiss import SwissSystemGenerator


__all__ = [
    # Protocol/Interface
    "BracketGenerator",
    
    # Generators
    "SingleEliminationGenerator",
    "DoubleEliminationGenerator",
    "RoundRobinGenerator",
    "SwissSystemGenerator",
    
    # Helper functions
    "calculate_bye_count",
    "next_power_of_two",
    "seed_participants_with_byes",
    "generate_round_robin_pairings",
]
