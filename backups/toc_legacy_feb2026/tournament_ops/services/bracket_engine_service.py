"""
Bracket Engine Service - Universal Tournament Bracket Orchestrator.

Phase 3, Epic 3.1: Universal Bracket Engine
Reference: DEV_PROGRESS_TRACKER.md - Epic 3.1.6

This service orchestrates bracket generation by selecting the appropriate generator
based on tournament/stage format and delegating to it.

Architecture:
- DTO-only: No ORM imports, works exclusively with DTOs
- Pure orchestration: Delegates actual generation to format-specific generators
- Extensible: New formats can be registered without modifying existing code
- Framework-light: Simple Python class with no Django dependencies

Responsibilities:
- Format selection based on stage.type or tournament.format
- Generator registry management
- Configuration validation before generation
- Centralized logging and error handling (TODO: EventBus integration)

Integration:
- Called by tournaments domain via feature flag wrapper (Epic 3.1.7)
- Returns MatchDTO instances that tournaments domain persists
- Epic 3.3: Works with StageTransitionService for match advancement
- Epic 3.4: Provides bracket structure for bracket editor
"""

from typing import List, Dict, Type
import logging

from apps.tournament_ops.dtos.tournament import TournamentDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.match import MatchDTO
from apps.tournament_ops.dtos.stage import StageDTO

from .bracket_generators import (
    BracketGenerator,
    SingleEliminationGenerator,
    DoubleEliminationGenerator,
    RoundRobinGenerator,
    SwissSystemGenerator,
)

logger = logging.getLogger("tournament_ops.bracket_engine")


class BracketEngineService:
    """
    Universal bracket generation orchestrator.
    
    Responsibilities:
    1. Select appropriate generator based on format
    2. Validate configuration before generation
    3. Delegate to generator and return results
    4. Log generation events for observability
    
    Format Registry:
    - single_elim → SingleEliminationGenerator
    - double_elim → DoubleEliminationGenerator
    - round_robin → RoundRobinGenerator
    - swiss → SwissSystemGenerator
    - Extensible via register_generator()
    
    Usage:
        service = BracketEngineService()
        matches = service.generate_bracket_for_stage(
            tournament=tournament_dto,
            stage=stage_dto,
            participants=team_dtos
        )
    """
    
    def __init__(self):
        """
        Initialize bracket engine with default generator registry.
        """
        self._generators: Dict[str, BracketGenerator] = {
            "single_elim": SingleEliminationGenerator(),
            "double_elim": DoubleEliminationGenerator(),
            "round_robin": RoundRobinGenerator(),
            "swiss": SwissSystemGenerator(),
            # Aliases so both short and long format keys work
            "single_elimination": SingleEliminationGenerator(),
            "double_elimination": DoubleEliminationGenerator(),
        }
    
    def generate_bracket_for_stage(
        self,
        tournament: TournamentDTO,
        stage: StageDTO,
        participants: List[TeamDTO]
    ) -> List[MatchDTO]:
        """
        Generate bracket for a tournament stage.
        
        Main entry point for bracket generation. Selects appropriate generator
        based on stage type and delegates generation.
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration (includes type/format)
            participants: Ordered list of teams (seeding order preserved)
        
        Returns:
            List of MatchDTO instances representing the bracket structure
        
        Raises:
            ValueError: If format not supported or configuration invalid
            KeyError: If generator not found for format
        
        TODO (Epic 3.3): Emit events via EventBus for bracket generation tracking
        TODO (Epic 3.4): Add metadata for bracket editor compatibility
        """
        # Determine format from stage.type or tournament.format
        format_key = self._determine_format(tournament, stage)
        
        logger.info(
            f"Generating bracket for tournament {tournament.id}, "
            f"stage {stage.id}, format '{format_key}', "
            f"{len(participants)} participants"
        )
        
        # Get generator for format
        generator = self._get_generator(format_key)
        
        # Validate configuration
        is_valid, errors = generator.validate_configuration(
            tournament=tournament,
            stage=stage,
            participant_count=len(participants)
        )
        
        if not is_valid:
            error_msg = f"Invalid bracket configuration: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Generate bracket
        try:
            matches = generator.generate_bracket(
                tournament=tournament,
                stage=stage,
                participants=participants
            )
            
            logger.info(
                f"Successfully generated {len(matches)} matches for "
                f"format '{format_key}'"
            )
            
            # TODO (Epic 3.3): Emit BracketGeneratedEvent via EventBus
            
            return matches
        
        except Exception as e:
            logger.exception(
                f"Error generating bracket for format '{format_key}': {e}"
            )
            raise
    
    def _determine_format(
        self,
        tournament: TournamentDTO,
        stage: StageDTO
    ) -> str:
        """
        Determine bracket format from stage or tournament configuration.
        
        Priority:
        1. stage.type (if present and recognized)
        2. tournament.format (fallback)
        
        Args:
            tournament: Tournament configuration
            stage: Stage configuration
        
        Returns:
            Format key for generator registry
        
        Raises:
            ValueError: If format cannot be determined
        """
        # Try stage.type first
        if stage.type:
            format_key = stage.type.lower().replace(" ", "_").replace("-", "_")
            if format_key in self._generators:
                return format_key
        
        # Fall back to tournament.ruleset or game_slug (TournamentDTO has no .format)
        fallback_format = getattr(tournament, "format", None)
        if fallback_format:
            format_key = fallback_format.lower().replace(" ", "_").replace("-", "_")
            if format_key in self._generators:
                return format_key
        
        # If still not found, raise error with helpful message
        available_formats = ", ".join(sorted(set(self._generators.keys())))
        stage_type_repr = stage.type if stage.type else "(empty)"
        raise ValueError(
            f"Unknown bracket format. Stage type: '{stage_type_repr}'. "
            f"Available formats: {available_formats}"
        )
    
    def _get_generator(self, format_key: str) -> BracketGenerator:
        """
        Get generator instance for format.
        
        Args:
            format_key: Format identifier
        
        Returns:
            BracketGenerator instance
        
        Raises:
            KeyError: If format not registered
        """
        if format_key not in self._generators:
            available_formats = ", ".join(self._generators.keys())
            raise KeyError(
                f"No generator registered for format '{format_key}'. "
                f"Available formats: {available_formats}"
            )
        
        return self._generators[format_key]
    
    def register_generator(
        self,
        format_key: str,
        generator: BracketGenerator
    ) -> None:
        """
        Register a new bracket generator for a format.
        
        Allows extension with custom formats without modifying core code.
        
        Args:
            format_key: Format identifier (e.g., "group_stage", "knockout")
            generator: BracketGenerator instance
        
        Example:
            service = BracketEngineService()
            service.register_generator("group_stage", GroupStageGenerator())
        
        TODO (Epic 3.6): Support for hybrid formats (group stage + playoffs)
        """
        if format_key in self._generators:
            logger.warning(
                f"Overwriting existing generator for format '{format_key}'"
            )
        
        self._generators[format_key] = generator
        logger.info(f"Registered generator for format '{format_key}'")
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of all supported bracket formats.
        
        Returns:
            List of format keys
        
        Example:
            >>> service.get_supported_formats()
            ['single_elim', 'double_elim', 'round_robin', 'swiss']
        """
        return list(self._generators.keys())
    
    def supports_format(self, format_key: str) -> bool:
        """
        Check if a format is supported.
        
        Args:
            format_key: Format identifier
        
        Returns:
            True if format is registered, False otherwise
        """
        return format_key in self._generators
