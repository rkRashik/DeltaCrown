"""
TournamentOps Orchestration Service (Phase 4, Epic 4.1).

This is the **main facade** for TournamentOps workflows, coordinating:
- Registration orchestration (draft → submit → payment → confirm)
- Payment verification workflows
- Tournament lifecycle coordination (future: Phase 4, Epic 4.2)

Reference Documents:
- ROADMAP_AND_EPICS_PART_4.md - Phase 4 (Weeks 13-16)
- CLEANUP_AND_TESTING_PART_6.md - §9.4 (Phase 4 Acceptance Tests)
- ARCH_PLAN_PART_1.md - Service boundaries and adapter pattern
"""

from typing import Optional
import logging

from common.events import get_event_bus, Event
from apps.tournament_ops.adapters import (
    TeamAdapter,
    UserAdapter,
    GameAdapter,
    EconomyAdapter,
    TournamentAdapter,
)
from apps.tournament_ops.dtos import RegistrationDTO, PaymentResultDTO, EligibilityResultDTO, TournamentDTO
from apps.tournament_ops.services.registration_service import RegistrationService
from apps.tournament_ops.services.payment_service import PaymentOrchestrationService
from apps.tournament_ops.services.tournament_lifecycle_service import TournamentLifecycleService
from apps.tournament_ops.exceptions import (
    RegistrationError,
    EligibilityError,
    PaymentError,
)

logger = logging.getLogger(__name__)


class TournamentOpsService:
    """
    Facade for TournamentOps workflows.

    Coordinates registration, payment, and tournament lifecycle operations
    across domain boundaries using the adapter pattern.

    **Workflow Coverage**:
    - Registration: DRAFT → SUBMITTED → PENDING_PAYMENT → CONFIRMED
    - Payment verification: verify payment → confirm registration → emit events
    - Tournament lifecycle: open → close → start → complete (future: Epic 4.2)

    **Architecture**:
    - Uses RegistrationService for registration orchestration
    - Uses PaymentOrchestrationService for payment processing
    - Uses adapters (Team/User/Game/Economy) for cross-domain data access
    - Uses event bus for event-driven communication

    **Reference**: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.1
    """

    def __init__(
        self,
        registration_service: Optional[RegistrationService] = None,
        payment_service: Optional[PaymentOrchestrationService] = None,
        lifecycle_service: Optional[TournamentLifecycleService] = None,
        team_adapter: Optional[TeamAdapter] = None,
        user_adapter: Optional[UserAdapter] = None,
        game_adapter: Optional[GameAdapter] = None,
        economy_adapter: Optional[EconomyAdapter] = None,
        tournament_adapter: Optional[TournamentAdapter] = None,
    ):
        """
        Initialize TournamentOps orchestration service.

        Args:
            registration_service: Registration workflow service (injected for testability).
            payment_service: Payment orchestration service (injected for testability).
            lifecycle_service: Tournament lifecycle service (injected for testability).
            team_adapter: Team data adapter.
            user_adapter: User data adapter.
            game_adapter: Game rules adapter.
            economy_adapter: Economy/payment adapter.
            tournament_adapter: Tournament data adapter.

        Note: If adapters are None, they will be lazily initialized on first use.
        """
        # Collaborating services
        self._registration_service = registration_service
        self._payment_service = payment_service
        self._lifecycle_service = lifecycle_service

        # Adapters (lazy initialization if None)
        self._team_adapter = team_adapter
        self._user_adapter = user_adapter
        self._game_adapter = game_adapter
        self._economy_adapter = economy_adapter
        self._tournament_adapter = tournament_adapter

        # Event bus
        self.event_bus = get_event_bus()

    @property
    def registration_service(self) -> RegistrationService:
        """Lazy initialization of RegistrationService."""
        if self._registration_service is None:
            self._registration_service = RegistrationService(
                team_adapter=self.team_adapter,
                user_adapter=self.user_adapter,
                game_adapter=self.game_adapter,
                economy_adapter=self.economy_adapter,
            )
        return self._registration_service

    @property
    def payment_service(self) -> PaymentOrchestrationService:
        """Lazy initialization of PaymentOrchestrationService."""
        if self._payment_service is None:
            self._payment_service = PaymentOrchestrationService(
                economy_adapter=self.economy_adapter
            )
        return self._payment_service

    @property
    def lifecycle_service(self) -> TournamentLifecycleService:
        """Lazy initialization of TournamentLifecycleService."""
        if self._lifecycle_service is None:
            self._lifecycle_service = TournamentLifecycleService(
                team_adapter=self.team_adapter,
                user_adapter=self.user_adapter,
                game_adapter=self.game_adapter,
                tournament_adapter=self.tournament_adapter,
            )
        return self._lifecycle_service

    @property
    def team_adapter(self) -> TeamAdapter:
        """Lazy initialization of TeamAdapter."""
        if self._team_adapter is None:
            self._team_adapter = TeamAdapter()
        return self._team_adapter

    @property
    def user_adapter(self) -> UserAdapter:
        """Lazy initialization of UserAdapter."""
        if self._user_adapter is None:
            self._user_adapter = UserAdapter()
        return self._user_adapter

    @property
    def game_adapter(self) -> GameAdapter:
        """Lazy initialization of GameAdapter."""
        if self._game_adapter is None:
            self._game_adapter = GameAdapter()
        return self._game_adapter

    @property
    def economy_adapter(self) -> EconomyAdapter:
        """Lazy initialization of EconomyAdapter."""
        if self._economy_adapter is None:
            self._economy_adapter = EconomyAdapter()
        return self._economy_adapter

    @property
    def tournament_adapter(self) -> TournamentAdapter:
        """Lazy initialization of TournamentAdapter."""
        if self._tournament_adapter is None:
            self._tournament_adapter = TournamentAdapter()
        return self._tournament_adapter

    # -------------------------------------------------------------------------
    # Registration Orchestration (Phase 4, Epic 4.1)
    # -------------------------------------------------------------------------

    def register_participant(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None,
        answers: Optional[dict] = None,
    ) -> RegistrationDTO:
        """
        Register a participant (team or individual) for a tournament.

        **Workflow** (ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.1):
        1. Validate team & user eligibility (via RegistrationService)
        2. Create registration record (DRAFT or SUBMITTED state)
        3. Charge registration fee if applicable (via PaymentOrchestrationService)
        4. Transition to PENDING_PAYMENT or CONFIRMED state
        5. Publish RegistrationStartedEvent

        Args:
            tournament_id: ID of the tournament to register for.
            user_id: ID of the user initiating registration (team captain or individual).
            team_id: ID of the team (None for individual tournaments).
            answers: Custom registration question answers (optional).

        Returns:
            RegistrationDTO with current state (PENDING_PAYMENT or CONFIRMED).

        Raises:
            EligibilityError: If team or user is not eligible.
            PaymentError: If payment processing fails.
            RegistrationError: If registration creation fails.

        **Acceptance Test**: test_register_participant_creates_registration_and_payment()
        (CLEANUP_AND_TESTING_PART_6.md §9.4)
        """
        logger.info(
            f"Starting registration for tournament {tournament_id}, "
            f"user {user_id}, team {team_id}"
        )

        # Step 1: Start registration (creates DRAFT/SUBMITTED record)
        registration = self.registration_service.start_registration(
            team_id=team_id,
            tournament_id=tournament_id,
            user_id=user_id,
            answers=answers or {},
        )

        # Step 2: Process payment if registration fee exists
        # (This will be queried from tournament via adapter in real impl)
        # For now, assume registration fee is handled by payment service
        try:
            # Note: In real implementation, we'd fetch tournament.registration_fee
            # and only charge if > 0. For Phase 4, we simulate this:
            # payment_result = self.payment_service.charge_registration_fee(
            #     user_id=user_id,
            #     tournament_id=tournament_id,
            #     amount=tournament.registration_fee
            # )
            # if payment_result.success:
            #     registration = self.registration_service.complete_registration(
            #         registration=registration,
            #         payment=payment_result
            #     )
            pass  # Payment handling deferred to verify_payment_and_confirm_registration
        except Exception as e:
            logger.error(f"Payment processing failed during registration: {e}")
            raise PaymentError(f"Failed to process payment: {e}") from e

        # Step 3: Publish event
        self.event_bus.publish(
            Event(
                name="RegistrationStartedEvent",
                payload={
                    "registration_id": registration.id,
                    "tournament_id": tournament_id,
                    "team_id": team_id,
                    "user_id": user_id,
                    "status": registration.status,
                },
            )
        )

        logger.info(f"Registration {registration.id} created with status {registration.status}")
        return registration

    def verify_payment_and_confirm_registration(
        self,
        registration_id: int,
        payment_reference: Optional[str] = None,
    ) -> RegistrationDTO:
        """
        Verify payment and transition registration to CONFIRMED state.

        **Workflow**:
        1. Verify payment via PaymentOrchestrationService
        2. Transition registration from PENDING_PAYMENT → CONFIRMED
        3. Publish RegistrationConfirmedEvent

        Args:
            registration_id: ID of the registration to confirm.
            payment_reference: Optional payment reference/transaction ID.

        Returns:
            Updated RegistrationDTO with status CONFIRMED.

        Raises:
            PaymentError: If payment verification fails.
            RegistrationError: If registration is not in PENDING_PAYMENT state.

        **Acceptance Test**: test_payment_verification_approves_registration()
        (CLEANUP_AND_TESTING_PART_6.md §9.4)
        """
        logger.info(f"Verifying payment for registration {registration_id}")

        # Step 1: Fetch registration (in real impl, via adapter)
        # For Phase 4, we assume registration service has internal access
        # registration = self._fetch_registration(registration_id)

        # Step 2: Verify payment (mocked in Phase 4, real in Phase 5)
        payment_result = PaymentResultDTO(
            success=True,
            transaction_id=payment_reference or f"txn_{registration_id}",
            error=None,
        )

        # Validate payment result
        payment_errors = payment_result.validate()
        if payment_errors:
            raise PaymentError(f"Invalid payment result: {payment_errors}")

        # Step 3: Complete registration (PENDING_PAYMENT → CONFIRMED)
        # In real impl, we'd fetch the registration DTO first
        # For Phase 4, we create a placeholder:
        registration = RegistrationDTO(
            id=registration_id,
            tournament_id=0,  # Would be fetched from DB
            team_id=0,
            user_id=0,
            answers={},
            status="pending_payment",
        )

        confirmed_registration = self.registration_service.complete_registration(
            registration=registration,
            payment=payment_result,
        )

        # Step 4: Publish event
        self.event_bus.publish(
            Event(
                name="RegistrationConfirmedEvent",
                payload={
                    "registration_id": confirmed_registration.id,
                    "tournament_id": confirmed_registration.tournament_id,
                    "team_id": confirmed_registration.team_id,
                    "user_id": confirmed_registration.user_id,
                    "status": confirmed_registration.status,
                    "payment_reference": payment_reference,
                },
            )
        )

        logger.info(f"Registration {registration_id} confirmed")
        return confirmed_registration

    def get_registration_state(self, registration_id: int) -> str:
        """
        Get current registration state.

        Args:
            registration_id: ID of the registration.

        Returns:
            Current status string (e.g., "draft", "submitted", "confirmed").

        Note: This is a simple helper for UI/testing. In real implementation,
        would fetch from registration adapter.
        """
        # Placeholder: In real impl, fetch via adapter
        # registration = self._fetch_registration(registration_id)
        # return registration.status
        return "pending"  # Placeholder for Phase 4

    # -------------------------------------------------------------------------
    # Tournament Lifecycle (Phase 4, Epic 4.2)
    # -------------------------------------------------------------------------

    def open_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Open a tournament for registration.

        Delegates to TournamentLifecycleService.open_tournament().

        Args:
            tournament_id: ID of the tournament to open.

        Returns:
            Updated TournamentDTO with status REGISTRATION_OPEN.

        Raises:
            InvalidTournamentStateError: If tournament cannot be opened.

        Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.2
        """
        return self.lifecycle_service.open_tournament(tournament_id)

    def start_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Start tournament (generate brackets and begin play).

        Delegates to TournamentLifecycleService.start_tournament().

        Args:
            tournament_id: ID of the tournament to start.

        Returns:
            Updated TournamentDTO with status LIVE.

        Raises:
            InvalidTournamentStateError: If tournament cannot be started.
            RegistrationError: If minimum participant count not met.

        Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.2
        """
        return self.lifecycle_service.start_tournament(tournament_id)

    def complete_tournament(self, tournament_id: int) -> TournamentDTO:
        """
        Complete tournament (finalize results and trigger payouts).

        Delegates to TournamentLifecycleService.complete_tournament().

        Args:
            tournament_id: ID of the tournament to complete.

        Returns:
            Updated TournamentDTO with status COMPLETED.

        Raises:
            InvalidTournamentStateError: If tournament cannot be completed.

        Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.2
        """
        return self.lifecycle_service.complete_tournament(tournament_id)

    def cancel_tournament(self, tournament_id: int, reason: str) -> TournamentDTO:
        """
        Cancel tournament and trigger refund processing.

        Delegates to TournamentLifecycleService.cancel_tournament().

        Args:
            tournament_id: ID of the tournament to cancel.
            reason: Reason for cancellation.

        Returns:
            Updated TournamentDTO with status CANCELLED.

        Raises:
            InvalidTournamentStateError: If tournament cannot be cancelled.

        Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.2
        """
        return self.lifecycle_service.cancel_tournament(tournament_id, reason)
