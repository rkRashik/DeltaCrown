"""
Registration orchestration service (DTO facade layer).

This service provides the adapter-based entry point for tournament registration
workflows, coordinating cross-domain eligibility checks and event publishing.

The canonical ORM-level implementation lives in:
    apps.tournaments.services.registration_service.RegistrationService

This service adds DTO validation, adapter-based cross-domain checks, and
event bus publishing on top of the ORM service.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.4 & Phase 5
"""

from typing import Optional
import logging

from common.events import get_event_bus, Event
from apps.tournament_ops.adapters import TeamAdapter, UserAdapter, GameAdapter, EconomyAdapter
from apps.tournament_ops.dtos import (
    RegistrationDTO,
    EligibilityResultDTO,
    PaymentResultDTO,
)
from apps.tournament_ops.exceptions import (
    RegistrationError,
    EligibilityError,
    PaymentError,
)

logger = logging.getLogger(__name__)


class RegistrationService:
    """
    Orchestrates tournament registration workflows.

    This service coordinates:
    - Team eligibility validation (team size, game identity verification)
    - User eligibility validation (age, region, ban status)
    - Payment processing (registration fees via DeltaCoin)
    - Smart registration (custom questions, auto-approval rules)
    - Event publishing (RegistrationStartedEvent, RegistrationApprovedEvent, etc.)

    Implementation Status:
    - Phase 1, Epic 1.4: Service skeleton ✅
    - Phase 5, Epic 5.1: Smart registration rules (future)
    - Phase 5, Epic 5.2: Auto-approval logic (future)
    - Phase 5, Epic 5.3: Custom questions (future)

    Reference: SMART_REG_AND_RULES_PART_3.md - Section 3 (Smart Registration)
    """

    def __init__(
        self,
        team_adapter: TeamAdapter,
        user_adapter: UserAdapter,
        game_adapter: GameAdapter,
        economy_adapter: EconomyAdapter,
    ) -> None:
        """
        Initialize registration service with required adapters.

        Args:
            team_adapter: Adapter for team data access.
            user_adapter: Adapter for user/profile data access.
            game_adapter: Adapter for game configuration access.
            economy_adapter: Adapter for payment processing.
        """
        self.team_adapter = team_adapter
        self.user_adapter = user_adapter
        self.game_adapter = game_adapter
        self.economy_adapter = economy_adapter
        self.event_bus = get_event_bus()

    def start_registration(
        self,
        team_id: Optional[int],
        tournament_id: int,
        user_id: int,
        answers: Optional[dict] = None,
    ) -> RegistrationDTO:
        """
        Initiate a new tournament registration.

        Workflow:
        1. Validate team eligibility (size, game match, verification)
        2. Validate user eligibility (captain status, ban status, age/region)
        3. Create pending registration record
        4. Publish RegistrationStartedEvent
        5. Trigger payment flow if registration fee exists
        6. Apply auto-approval rules (Phase 5)

        Args:
            team_id: ID of the team registering (None for individual tournaments).
            tournament_id: ID of the tournament.
            user_id: ID of the user initiating registration (usually team captain).
            answers: Optional custom registration question answers.

        Returns:
            RegistrationDTO with status "submitted".

        Raises:
            EligibilityError: If team or user is not eligible.
            RegistrationError: If registration creation fails.

        TODO (Phase 5, Epic 5.1):
        - Fetch tournament registration rules
        - Validate required custom questions
        - Apply smart registration auto-approval logic
        """
        logger.info(
            f"Starting registration for tournament {tournament_id}, "
            f"user {user_id}, team {team_id}"
        )

        # Step 1: Validate eligibility
        eligibility = self.validate_registration(
            team_id=team_id,
            tournament_id=tournament_id,
            user_id=user_id,
        )

        if not eligibility.is_eligible:
            logger.warning(
                f"Eligibility check failed for user {user_id}: {eligibility.reasons}"
            )
            raise EligibilityError(
                f"User {user_id} is not eligible to register: {', '.join(eligibility.reasons)}"
            )

        # Step 2: Create registration DTO (SUBMITTED state)
        # In real implementation, this would persist via an adapter
        # For Phase 4, we create a DTO in-memory
        registration = RegistrationDTO(
            id=None,  # Will be assigned by persistence layer
            tournament_id=tournament_id,
            team_id=team_id,
            user_id=user_id,
            answers=answers or {},
            status="pending",  # Phase 4: Use pending status (DTO validation requirement)
        )

        # Validate DTO
        validation_errors = registration.validate()
        if validation_errors:
            raise RegistrationError(f"Invalid registration data: {validation_errors}")

        # Step 3: Publish event
        self.event_bus.publish(
            Event(
                name="RegistrationStartedEvent",
                payload={
                    "tournament_id": tournament_id,
                    "team_id": team_id,
                    "user_id": user_id,
                    "status": registration.status,
                    "answers": answers or {},
                },
            )
        )

        logger.info(
            f"Registration created for user {user_id} in tournament {tournament_id} "
            f"with status {registration.status}"
        )
        return registration


    def complete_registration(
        self, registration: RegistrationDTO, payment: PaymentResultDTO
    ) -> RegistrationDTO:
        """
        Complete a pending registration (after payment confirmed).

        Workflow:
        1. Verify payment status
        2. Update registration status to "confirmed"
        3. Publish RegistrationConfirmedEvent
        4. Trigger team notifications

        Args:
            registration: Registration DTO to complete.
            payment: Payment result DTO with transaction details.

        Returns:
            Updated RegistrationDTO with status "confirmed".

        Raises:
            PaymentError: If payment verification fails.
            RegistrationError: If registration is not in valid state.

        TODO (Phase 5, Epic 5.2):
        - Check auto-approval rules
        - Route to manual review queue if needed
        """
        logger.info(f"Completing registration {registration.id}")

        # Step 1: Verify payment
        if not payment.success:
            logger.error(
                f"Payment failed for registration {registration.id}: {payment.error}"
            )
            raise PaymentError(f"Payment verification failed: {payment.error}")

        payment_errors = payment.validate()
        if payment_errors:
            raise PaymentError(f"Invalid payment result: {payment_errors}")

        # Step 2: Update registration status
        # In real implementation, this would persist via adapter
        # For Phase 4, we create a new DTO with updated status
        confirmed_registration = RegistrationDTO(
            id=registration.id,
            tournament_id=registration.tournament_id,
            team_id=registration.team_id,
            user_id=registration.user_id,
            answers=registration.answers,
            status="approved",  # Use approved instead of confirmed (DTO validation)
        )

        # Step 3: Publish event
        self.event_bus.publish(
            Event(
                name="RegistrationConfirmedEvent",
                payload={
                    "registration_id": confirmed_registration.id,
                    "tournament_id": confirmed_registration.tournament_id,
                    "team_id": confirmed_registration.team_id,
                    "user_id": confirmed_registration.user_id,
                    "status": confirmed_registration.status,
                    "payment_transaction_id": payment.transaction_id,
                },
            )
        )

        logger.info(
            f"Registration {registration.id} confirmed with payment {payment.transaction_id}"
        )
        return confirmed_registration

    def validate_registration(
        self, team_id: Optional[int], tournament_id: int, user_id: int
    ) -> EligibilityResultDTO:
        """
        Validate if a team/user is eligible to register for a tournament.

        Checks:
        - Team exists and is verified (if team_id provided)
        - Team game matches tournament game
        - Team size meets tournament requirements
        - All team members have verified game identities
        - No team members are banned
        - Team not already registered
        - User has permission to register (captain or individual)

        Args:
            team_id: ID of the team to validate (None for individual tournaments).
            tournament_id: ID of the tournament.
            user_id: ID of the user initiating registration.

        Returns:
            EligibilityResultDTO with is_eligible flag and reasons.

        TODO (Phase 1, Epic 1.4):
        - Implement all eligibility checks via adapters
        - Use TeamAdapter and UserAdapter for cross-domain validation
        """
        logger.info(
            f"Validating registration eligibility for tournament {tournament_id}, "
            f"user {user_id}, team {team_id}"
        )

        reasons = []

        # Phase 4 Implementation: Simplified eligibility (adapters not fully connected)
        # In real implementation, we would:
        # 1. team = self.team_adapter.get_team(team_id) if team_id else None
        # 2. user = self.user_adapter.get_user(user_id)
        # 3. tournament = self.game_adapter.get_tournament(tournament_id)
        # 4. Validate team size, game match, verification status, etc.

        # For Phase 4, we allow all registrations (testing focus)
        # Phase 5 will add real eligibility rules via GameRulesEngine

        is_eligible = len(reasons) == 0

        result = EligibilityResultDTO(
            is_eligible=is_eligible,
            reasons=reasons,
        )

        # Validate result DTO
        result_errors = result.validate()
        if result_errors:
            logger.error(f"Eligibility result validation failed: {result_errors}")
            # Fallback: deny registration if result is malformed
            return EligibilityResultDTO(
                is_eligible=False,
                reasons=["Internal validation error: eligibility check failed"],
            )

        logger.info(
            f"Eligibility validation result: is_eligible={is_eligible}, reasons={reasons}"
        )
        return result

    def withdraw_registration(
        self, registration: RegistrationDTO, initiated_by_user_id: int
    ) -> RegistrationDTO:
        """
        Withdraw a registration and process refund if applicable.

        Workflow:
        1. Validate withdrawal eligibility (tournament not started, etc.)
        2. Update registration status to "withdrawn"
        3. Process refund if payment was made
        4. Publish RegistrationWithdrawnEvent

        Args:
            registration: Registration DTO to withdraw.
            initiated_by_user_id: ID of the user initiating withdrawal.

        Returns:
            Updated RegistrationDTO with status "withdrawn".

        Raises:
            RegistrationError: If withdrawal is not allowed.

        TODO (Phase 5, Epic 5.4):
        - Implement withdrawal rules (deadlines, penalties)
        - Handle partial refunds
        """
        logger.info(
            f"Withdrawing registration {registration.id} by user {initiated_by_user_id}"
        )

        # Step 1: Validate withdrawal eligibility
        if registration.status == "withdrawn":
            raise RegistrationError(
                f"Registration {registration.id} is already withdrawn"
            )

        # In real implementation, check:
        # - Tournament has not started
        # - User has permission to withdraw
        # - Withdrawal deadline not passed

        # Step 2: Update registration status
        withdrawn_registration = RegistrationDTO(
            id=registration.id,
            tournament_id=registration.tournament_id,
            team_id=registration.team_id,
            user_id=registration.user_id,
            answers=registration.answers,
            status="withdrawn",
        )

        # Step 3: Process refund (via payment service - delegated to caller)
        # Note: Refund logic is handled by TournamentOpsService/PaymentOrchestrationService

        # Step 4: Publish event
        self.event_bus.publish(
            Event(
                name="RegistrationWithdrawnEvent",
                payload={
                    "registration_id": withdrawn_registration.id,
                    "tournament_id": withdrawn_registration.tournament_id,
                    "team_id": withdrawn_registration.team_id,
                    "user_id": withdrawn_registration.user_id,
                    "initiated_by_user_id": initiated_by_user_id,
                    "status": withdrawn_registration.status,
                },
            )
        )

        logger.info(f"Registration {registration.id} withdrawn successfully")
        return withdrawn_registration
        raise NotImplementedError(
            "RegistrationService.withdraw_registration() not yet implemented. "
            "Will be completed in Phase 5, Epic 5.4."
        )
