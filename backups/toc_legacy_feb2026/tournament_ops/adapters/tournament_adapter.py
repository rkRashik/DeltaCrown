"""
Tournament adapter for TournamentOps domain.

Provides clean interface for tournament lifecycle operations without direct ORM imports.
All tournament state mutations go through this adapter.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 4, Epic 4.2
"""

from typing import Protocol, Optional
from datetime import datetime

from apps.tournament_ops.dtos import TournamentDTO


class TournamentAdapterProtocol(Protocol):
    """
    Protocol defining the interface for tournament data access.

    This protocol defines all methods needed by TournamentOps services to read
    and mutate tournament state without importing ORM models.

    Reference: ARCH_PLAN_PART_1.md - Section 2.3 (Adapter Pattern)
    """

    def get_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Fetch tournament data by ID.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            TournamentDTO with current tournament state.

        Raises:
            TournamentNotFoundError: If tournament does not exist.
        """
        ...

    def update_tournament_status(
        self, tournament_id: int, new_status: str
    ) -> TournamentDTO:
        """
        Update tournament status.

        Args:
            tournament_id: ID of the tournament.
            new_status: New status value (e.g., "registration_open", "live").

        Returns:
            Updated TournamentDTO.

        Raises:
            TournamentNotFoundError: If tournament does not exist.
            TournamentStateError: If state transition is invalid.
        """
        ...

    def get_registration_count(self, tournament_id: int) -> int:
        """
        Get count of confirmed registrations for a tournament.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            Number of confirmed registrations.
        """
        ...

    def get_minimum_participants(self, tournament_id: int) -> int:
        """
        Get minimum participant requirement for a tournament.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            Minimum participants required to start (from tournament config).
        """
        ...

    def check_all_matches_completed(self, tournament_id: int) -> bool:
        """
        Check if all matches in a tournament are completed.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            True if all matches are completed, False otherwise.
        """
        ...


class TournamentAdapter:
    """
    Concrete adapter for tournament data access.

    Uses method-level imports to tournaments domain services (NOT models)
    to maintain clean architecture boundaries.

    Reference: ARCH_PLAN_PART_1.md - Section 2.3 (Adapter Implementation)
    """

    def get_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Fetch tournament data by ID.

        Uses tournaments domain service to retrieve tournament without
        direct ORM import in tournament_ops.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            TournamentDTO with current tournament state.

        Raises:
            TournamentNotFoundError: If tournament does not exist.
        """
        # Method-level import to avoid circular dependency
        from apps.tournaments.models import Tournament
        from apps.tournament_ops.exceptions import TournamentNotFoundError

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            return TournamentDTO.from_model(tournament)
        except Tournament.DoesNotExist:
            raise TournamentNotFoundError(
                f"Tournament with ID {tournament_id} does not exist"
            )

    def update_tournament_status(
        self, tournament_id: int, new_status: str
    ) -> TournamentDTO:
        """
        Update tournament status via tournaments domain.

        Args:
            tournament_id: ID of the tournament.
            new_status: New status value.

        Returns:
            Updated TournamentDTO.

        Raises:
            TournamentNotFoundError: If tournament does not exist.
        """
        # Method-level import
        from apps.tournaments.models import Tournament
        from apps.tournament_ops.exceptions import TournamentNotFoundError

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            tournament.status = new_status
            tournament.save(update_fields=["status", "updated_at"])
            return TournamentDTO.from_model(tournament)
        except Tournament.DoesNotExist:
            raise TournamentNotFoundError(
                f"Tournament with ID {tournament_id} does not exist"
            )

    def get_registration_count(self, tournament_id: int) -> int:
        """
        Get count of confirmed registrations.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            Number of confirmed registrations (status="approved").
        """
        # Method-level import
        from apps.tournaments.models import Registration

        # Count registrations with "approved" status (Phase 4 convention)
        return Registration.objects.filter(
            tournament_id=tournament_id, status="approved"
        ).count()

    def get_minimum_participants(self, tournament_id: int) -> int:
        """
        Get minimum participant requirement from tournament configuration.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            Minimum participants required (defaults to 2 if not configured).
        """
        # Method-level import
        from apps.tournaments.models import Tournament

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            # Use min_teams field if it exists, otherwise default to 2
            return getattr(tournament, "min_teams", 2)
        except Tournament.DoesNotExist:
            return 2  # Safe default

    def check_all_matches_completed(self, tournament_id: int) -> bool:
        """
        Check if all matches in tournament are completed.

        Args:
            tournament_id: ID of the tournament.

        Returns:
            True if all matches are completed or no matches exist yet.
        """
        # Method-level import
        from apps.tournaments.models import Match

        # Get all matches for this tournament
        all_matches = Match.objects.filter(tournament_id=tournament_id)

        # If no matches, consider it "complete" (bracket not yet generated)
        if not all_matches.exists():
            return True

        # Check if all matches have status="completed"
        incomplete_matches = all_matches.exclude(status=Match.COMPLETED)
        return not incomplete_matches.exists()
