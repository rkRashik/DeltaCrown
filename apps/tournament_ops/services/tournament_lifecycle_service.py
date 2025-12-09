"""
Tournament lifecycle orchestration service.

This service manages tournament state transitions and lifecycle events.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 4, Epic 4.2
"""

from common.events import get_event_bus, Event
from apps.tournament_ops.adapters import (
    TeamAdapter,
    UserAdapter,
    GameAdapter,
    TournamentAdapter,
)
from apps.tournament_ops.dtos import TournamentDTO
from apps.tournament_ops.exceptions import (
    InvalidTournamentStateError,
    RegistrationError,
)


class TournamentLifecycleService:
    """
    Orchestrates tournament lifecycle state transitions.

    This service manages:
    - Tournament state transitions (draft → open → in_progress → completed)
    - Registration window management
    - Bracket generation triggers
    - Tournament completion and payout triggers
    - Lifecycle event publishing

    Implementation Status:
    - Phase 1, Epic 1.4: Service skeleton ✅
    - Phase 4, Epic 4.1: Lifecycle workflow implementation (future)
    - Phase 3: Bracket generation integration (future)
    - Phase 6: Result finalization integration (future)

    Reference: LIFECYCLE_GAPS_PART_2.md - Section 2 (Lifecycle Gaps)
    """

    def __init__(
        self,
        team_adapter: TeamAdapter,
        user_adapter: UserAdapter,
        game_adapter: GameAdapter,
        tournament_adapter: TournamentAdapter,
    ) -> None:
        """
        Initialize lifecycle service with required adapters.

        Args:
            team_adapter: Adapter for team data access.
            user_adapter: Adapter for user/profile data access.
            game_adapter: Adapter for game configuration access.
            tournament_adapter: Adapter for tournament data access.
        """
        self.team_adapter = team_adapter
        self.user_adapter = user_adapter
        self.game_adapter = game_adapter
        self.tournament_adapter = tournament_adapter
        self.event_bus = get_event_bus()

    def open_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Open a tournament for registration.

        Workflow:
        1. Validate tournament is in draft or published state
        2. Validate all tournament configuration is complete
        3. Update tournament status to "registration_open"
        4. Publish TournamentOpenedEvent

        Args:
            tournament_id: ID of the tournament to open.

        Returns:
            Updated TournamentDTO.

        Raises:
            InvalidTournamentStateError: If tournament is not in draft/published state.

        Reference: Phase 4, Epic 4.2 (Tournament Lifecycle Orchestration)
        """
        # Method-level import for status constants
        from apps.tournaments.models import Tournament

        # Get current tournament state
        tournament = self.tournament_adapter.get_tournament(tournament_id)

        # Validate current state allows opening
        valid_states = [Tournament.DRAFT, Tournament.PUBLISHED]
        if tournament.status not in valid_states:
            raise InvalidTournamentStateError(
                f"Cannot open tournament {tournament_id} with status '{tournament.status}'. "
                f"Expected one of {valid_states}."
            )

        # Update status to REGISTRATION_OPEN
        updated_tournament = self.tournament_adapter.update_tournament_status(
            tournament_id=tournament_id, new_status=Tournament.REGISTRATION_OPEN
        )

        # Publish TournamentOpenedEvent
        self.event_bus.publish(
            Event(
                name="TournamentOpenedEvent",
                payload={
                    "tournament_id": tournament_id,
                    "tournament_name": updated_tournament.name,
                    "game_slug": updated_tournament.game_slug,
                    "max_teams": updated_tournament.max_teams,
                },
            )
        )

        return updated_tournament

    def start_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Start a tournament (generate brackets and begin play).

        Workflow:
        1. Validate minimum registration count met
        2. Close registration window
        3. Update tournament status to "live"
        4. Publish TournamentStartedEvent (triggers bracket generation in Phase 3)

        Args:
            tournament_id: ID of the tournament to start.

        Returns:
            Updated TournamentDTO.

        Raises:
            InvalidTournamentStateError: If tournament is not in registration_open/registration_closed state.
            RegistrationError: If minimum participant count not met.

        Reference: Phase 4, Epic 4.2 (Tournament Lifecycle Orchestration)
        """
        # Method-level import for status constants
        from apps.tournaments.models import Tournament

        # Get current tournament state
        tournament = self.tournament_adapter.get_tournament(tournament_id)

        # Validate current state allows starting
        valid_states = [Tournament.REGISTRATION_OPEN, Tournament.REGISTRATION_CLOSED]
        if tournament.status not in valid_states:
            raise InvalidTournamentStateError(
                f"Cannot start tournament {tournament_id} with status '{tournament.status}'. "
                f"Expected one of {valid_states}."
            )

        # Validate minimum participant count
        registration_count = self.tournament_adapter.get_registration_count(tournament_id)
        min_participants = self.tournament_adapter.get_minimum_participants(tournament_id)

        if registration_count < min_participants:
            raise RegistrationError(
                f"Cannot start tournament {tournament_id}. "
                f"Only {registration_count} teams registered, minimum {min_participants} required."
            )

        # Update status to LIVE
        updated_tournament = self.tournament_adapter.update_tournament_status(
            tournament_id=tournament_id, new_status=Tournament.LIVE
        )

        # Publish TournamentStartedEvent (triggers bracket generation in Phase 3)
        self.event_bus.publish(
            Event(
                name="TournamentStartedEvent",
                payload={
                    "tournament_id": tournament_id,
                    "tournament_name": updated_tournament.name,
                    "game_slug": updated_tournament.game_slug,
                    "participant_count": registration_count,
                    "stage": updated_tournament.stage,
                },
            )
        )

        return updated_tournament

    def complete_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Complete a tournament (finalize results, trigger payouts).

        Workflow:
        1. Validate all matches are completed
        2. Update tournament status to "completed"
        3. Publish TournamentCompletedEvent (triggers payout in Phase 6)

        Args:
            tournament_id: ID of the tournament to complete.

        Returns:
            Updated TournamentDTO.

        Raises:
            InvalidTournamentStateError: If tournament is not in live state.
            InvalidTournamentStateError: If not all matches are completed.

        Reference: Phase 4, Epic 4.2 (Tournament Lifecycle Orchestration)
        """
        # Method-level import for status constants
        from apps.tournaments.models import Tournament

        # Get current tournament state
        tournament = self.tournament_adapter.get_tournament(tournament_id)

        # Validate current state allows completion
        if tournament.status != Tournament.LIVE:
            raise InvalidTournamentStateError(
                f"Cannot complete tournament {tournament_id} with status '{tournament.status}'. "
                f"Expected '{Tournament.LIVE}'."
            )

        # Validate all matches are completed
        all_matches_completed = self.tournament_adapter.check_all_matches_completed(
            tournament_id
        )
        if not all_matches_completed:
            raise InvalidTournamentStateError(
                f"Cannot complete tournament {tournament_id}. "
                "Not all matches are completed."
            )

        # Update status to COMPLETED
        updated_tournament = self.tournament_adapter.update_tournament_status(
            tournament_id=tournament_id, new_status=Tournament.COMPLETED
        )

        # Publish TournamentCompletedEvent (triggers payout, leaderboard updates in Phase 6)
        self.event_bus.publish(
            Event(
                name="TournamentCompletedEvent",
                payload={
                    "tournament_id": tournament_id,
                    "tournament_name": updated_tournament.name,
                    "game_slug": updated_tournament.game_slug,
                },
            )
        )

        return updated_tournament

    def cancel_tournament(self, tournament_id: int, reason: str) -> TournamentDTO:
        """
        Cancel a tournament and process refunds.

        Workflow:
        1. Update tournament status to "cancelled"
        2. Publish TournamentCancelledEvent (triggers refund processing)

        Args:
            tournament_id: ID of the tournament to cancel.
            reason: Reason for cancellation.

        Returns:
            Updated TournamentDTO.

        Raises:
            InvalidTournamentStateError: If tournament is already completed.

        Reference: Phase 4, Epic 4.2 (Tournament Lifecycle Orchestration)
        """
        # Method-level import for status constants
        from apps.tournaments.models import Tournament

        # Get current tournament state
        tournament = self.tournament_adapter.get_tournament(tournament_id)

        # Validate tournament is not already completed
        if tournament.status == Tournament.COMPLETED:
            raise InvalidTournamentStateError(
                f"Cannot cancel tournament {tournament_id} with status '{tournament.status}'. "
                "Completed tournaments cannot be cancelled."
            )

        # Update status to CANCELLED
        updated_tournament = self.tournament_adapter.update_tournament_status(
            tournament_id=tournament_id, new_status=Tournament.CANCELLED
        )

        # Publish TournamentCancelledEvent (triggers refund processing)
        self.event_bus.publish(
            Event(
                name="TournamentCancelledEvent",
                payload={
                    "tournament_id": tournament_id,
                    "tournament_name": updated_tournament.name,
                    "game_slug": updated_tournament.game_slug,
                    "reason": reason,
                },
            )
        )

        return updated_tournament
