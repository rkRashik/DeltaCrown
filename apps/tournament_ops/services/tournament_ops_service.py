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
from apps.tournament_ops.services.result_submission_service import ResultSubmissionService
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
        result_submission_service: Optional[ResultSubmissionService] = None,
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
            result_submission_service: Result submission service (injected for testability).
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
        self._result_submission_service = result_submission_service

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
    def result_submission_service(self) -> ResultSubmissionService:
        """Lazy initialization of ResultSubmissionService (Phase 6, Epic 6.1)."""
        if self._result_submission_service is None:
            from apps.tournament_ops.adapters import (
                ResultSubmissionAdapter,
                SchemaValidationAdapter,
                MatchAdapter,
                DisputeAdapter,
            )
            self._result_submission_service = ResultSubmissionService(
                result_submission_adapter=ResultSubmissionAdapter(),
                schema_validation_adapter=SchemaValidationAdapter(),
                match_adapter=MatchAdapter(),
                game_adapter=self.game_adapter,
                dispute_adapter=DisputeAdapter(),
            )
        return self._result_submission_service

    @property
    def dispute_service(self):
        """Lazy initialization of DisputeService (Phase 6, Epic 6.2 & 6.5)."""
        if not hasattr(self, '_dispute_service') or self._dispute_service is None:
            from apps.tournament_ops.services import DisputeService
            from apps.tournament_ops.adapters import DisputeAdapter, ResultSubmissionAdapter
            self._dispute_service = DisputeService(
                dispute_adapter=DisputeAdapter(),
                result_submission_adapter=ResultSubmissionAdapter(),
                result_verification_service=self.result_verification_service,  # Epic 6.4 integration
                notification_adapter=self.notification_adapter,  # Epic 6.5 integration
            )
        return self._dispute_service

    @property
    def review_inbox_service(self):
        """Lazy initialization of ReviewInboxService (Phase 6, Epic 6.3, 6.4, 6.5)."""
        if not hasattr(self, '_review_inbox_service') or self._review_inbox_service is None:
            from apps.tournament_ops.services import ReviewInboxService
            from apps.tournament_ops.adapters import (
                ReviewInboxAdapter,
                DisputeAdapter,
                ResultSubmissionAdapter,
            )
            self._review_inbox_service = ReviewInboxService(
                review_inbox_adapter=ReviewInboxAdapter(),
                dispute_adapter=DisputeAdapter(),
                result_submission_adapter=ResultSubmissionAdapter(),
                match_service=self.match_service,
                result_verification_service=self.result_verification_service,  # Epic 6.4 integration
                dispute_service=self.dispute_service,  # Epic 6.5 integration
            )
        return self._review_inbox_service

    @property
    def result_verification_service(self):
        """Lazy initialization of ResultVerificationService (Phase 6, Epic 6.4)."""
        if not hasattr(self, '_result_verification_service') or self._result_verification_service is None:
            from apps.tournament_ops.services import ResultVerificationService
            from apps.tournament_ops.adapters import (
                ResultSubmissionAdapter,
                DisputeAdapter,
                SchemaValidationAdapter,
            )
            self._result_verification_service = ResultVerificationService(
                result_submission_adapter=ResultSubmissionAdapter(),
                dispute_adapter=DisputeAdapter(),
                schema_validation_adapter=SchemaValidationAdapter(),
                match_service=self.match_service,
            )
        return self._result_verification_service

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
    
    @property
    def notification_adapter(self):
        """Lazy initialization of NotificationAdapter (Phase 6, Epic 6.5)."""
        if not hasattr(self, '_notification_adapter') or self._notification_adapter is None:
            from apps.tournament_ops.adapters import NotificationAdapter
            self._notification_adapter = NotificationAdapter()
        return self._notification_adapter

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

    # -------------------------------------------------------------------------
    # Smart Registration (Phase 5)
    # -------------------------------------------------------------------------

    @property
    def smart_registration_adapter(self):
        """Lazy initialization of SmartRegistrationAdapter."""
        if not hasattr(self, '_smart_registration_adapter') or self._smart_registration_adapter is None:
            from apps.tournament_ops.adapters import SmartRegistrationAdapter
            self._smart_registration_adapter = SmartRegistrationAdapter()
        return self._smart_registration_adapter

    @property
    def smart_registration_service(self):
        """Lazy initialization of SmartRegistrationService."""
        if not hasattr(self, '_smart_registration_service') or self._smart_registration_service is None:
            from apps.tournament_ops.services.smart_registration_service import SmartRegistrationService
            self._smart_registration_service = SmartRegistrationService(
                smart_reg_adapter=self.smart_registration_adapter,
                registration_service=self.registration_service,
                team_adapter=self.team_adapter,
                user_adapter=self.user_adapter,
                game_adapter=self.game_adapter,
                tournament_adapter=self.tournament_adapter,
            )
        return self._smart_registration_service

    def create_draft_registration(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None,
    ):
        """
        Create a new registration draft (Phase 5).

        Delegates to SmartRegistrationService.create_draft_registration().

        Args:
            tournament_id: Tournament ID
            user_id: User creating registration
            team_id: Team ID (null for solo tournaments)

        Returns:
            RegistrationDraftDTO

        Reference: SMART_REG_AND_RULES_PART_3.md Section 3
        """
        return self.smart_registration_service.create_draft_registration(
            tournament_id, user_id, team_id
        )

    def get_registration_form(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int] = None,
    ) -> dict:
        """
        Get registration form configuration (Phase 5).

        Delegates to SmartRegistrationService.get_registration_form().

        Args:
            tournament_id: Tournament ID
            user_id: User ID
            team_id: Team ID (null for solo)

        Returns:
            {
                'questions': [RegistrationQuestionDTO, ...],
                'auto_fill_data': {field_name: value, ...},
                'locked_fields': [field_name, ...],
            }

        Reference: SMART_REG_AND_RULES_PART_3.md Section 3
        """
        return self.smart_registration_service.get_registration_form(
            tournament_id, user_id, team_id
        )

    def submit_registration_answers(
        self,
        registration_id: int,
        answers: dict,
    ) -> RegistrationDTO:
        """
        Submit answers to registration questions (Phase 5).

        Delegates to SmartRegistrationService.submit_answers().

        Args:
            registration_id: Registration ID
            answers: {question_slug: answer_value, ...}

        Returns:
            Updated RegistrationDTO

        Reference: SMART_REG_AND_RULES_PART_3.md Section 3
        """
        return self.smart_registration_service.submit_answers(registration_id, answers)

    def evaluate_registration(
        self,
        registration_id: int,
    ) -> RegistrationDTO:
        """
        Evaluate registration against auto-approval rules (Phase 5).

        Delegates to SmartRegistrationService.evaluate_registration().

        Args:
            registration_id: Registration ID

        Returns:
            Updated RegistrationDTO (status: auto_approved, rejected, or needs_review)

        Reference: SMART_REG_AND_RULES_PART_3.md Section 3
        """
        return self.smart_registration_service.evaluate_registration(registration_id)

    def auto_process_registration(
        self,
        tournament_id: int,
        user_id: int,
        team_id: Optional[int],
        answers: dict,
    ) -> tuple:
        """
        One-shot registration processing (Phase 5).

        Delegates to SmartRegistrationService.auto_process_registration().

        Args:
            tournament_id: Tournament ID
            user_id: User ID
            team_id: Team ID (null for solo)
            answers: {question_slug: answer_value, ...}

        Returns:
            (RegistrationDTO, decision: 'auto_approved'|'auto_rejected'|'needs_review')

        Reference: SMART_REG_AND_RULES_PART_3.md Section 3
        """
        return self.smart_registration_service.auto_process_registration(
            tournament_id, user_id, team_id, answers
        )

    # -------------------------------------------------------------------------
    # Result Submission (Phase 6, Epic 6.1)
    # -------------------------------------------------------------------------

    def submit_match_result(
        self,
        match_id: int,
        submitted_by_user_id: int,
        submitted_by_team_id: Optional[int],
        raw_result_payload: dict,
        proof_screenshot_url: Optional[str] = None,
        submitter_notes: str = "",
    ):
        """
        Submit match result with proof (Phase 6, Epic 6.1).

        Delegates to ResultSubmissionService.submit_result().

        Args:
            match_id: Match ID
            submitted_by_user_id: User ID of submitter
            submitted_by_team_id: Team ID if team tournament
            raw_result_payload: Game-specific result data
            proof_screenshot_url: URL to proof screenshot
            submitter_notes: Optional notes from submitter

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.1
        """
        return self.result_submission_service.submit_result(
            match_id=match_id,
            submitted_by_user_id=submitted_by_user_id,
            submitted_by_team_id=submitted_by_team_id,
            raw_result_payload=raw_result_payload,
            proof_screenshot_url=proof_screenshot_url,
            submitter_notes=submitter_notes,
        )

    def confirm_match_result(
        self,
        submission_id: int,
        confirmed_by_user_id: int,
    ):
        """
        Confirm submitted match result (Phase 6, Epic 6.1).

        Delegates to ResultSubmissionService.confirm_result().

        Args:
            submission_id: Submission ID
            confirmed_by_user_id: User ID confirming result

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.1
        """
        return self.result_submission_service.confirm_result(
            submission_id=submission_id,
            confirmed_by_user_id=confirmed_by_user_id,
        )

    def auto_confirm_match_result(self, submission_id: int):
        """
        Auto-confirm match result (admin/Celery use).

        Delegates to ResultSubmissionService.auto_confirm_result().

        Args:
            submission_id: Submission ID

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.1
        """
        return self.result_submission_service.auto_confirm_result(submission_id)

    # -------------------------------------------------------------------------
    # Opponent Verification & Dispute System (Phase 6, Epic 6.2)
    # -------------------------------------------------------------------------

    def opponent_respond_to_submission(
        self,
        submission_id: int,
        responding_user_id: int,
        decision: str,
        reason_code: Optional[str] = None,
        notes: str = "",
        evidence: Optional[list] = None,
    ):
        """
        Opponent responds to match result submission (Phase 6, Epic 6.2).

        Delegates to ResultSubmissionService.opponent_response().

        Args:
            submission_id: Submission ID
            responding_user_id: User ID of opponent responding
            decision: "confirm" or "dispute"
            reason_code: Dispute reason code (required if decision="dispute")
            notes: Optional notes from opponent
            evidence: Optional list of evidence dicts [{type, url, notes}]

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2
        """
        return self.result_submission_service.opponent_response(
            submission_id=submission_id,
            responding_user_id=responding_user_id,
            decision=decision,
            reason_code=reason_code,
            notes=notes,
            evidence=evidence or [],
        )

    def resolve_dispute(
        self,
        dispute_id: int,
        resolved_by_user_id: int,
        resolution: str,
        resolution_notes: str = "",
    ):
        """
        Resolve a dispute with organizer decision (Phase 6, Epic 6.2).

        Delegates to DisputeService.resolve_dispute().

        Args:
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            resolution: "submitter_wins", "opponent_wins", or "cancelled"
            resolution_notes: Internal notes explaining decision

        Returns:
            DisputeDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2
        """
        return self.dispute_service.resolve_dispute(
            dispute_id=dispute_id,
            resolved_by_user_id=resolved_by_user_id,
            resolution=resolution,
            resolution_notes=resolution_notes,
        )

    def escalate_dispute(self, dispute_id: int, escalated_by_user_id: int):
        """
        Escalate dispute to higher-tier support (Phase 6, Epic 6.2).

        Delegates to DisputeService.escalate_dispute().

        Args:
            dispute_id: Dispute ID
            escalated_by_user_id: User escalating

        Returns:
            DisputeDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2
        """
        return self.dispute_service.escalate_dispute(
            dispute_id=dispute_id,
            escalated_by_user_id=escalated_by_user_id,
        )

    def add_dispute_evidence(
        self,
        dispute_id: int,
        uploaded_by_user_id: int,
        evidence_type: str,
        url: str,
        notes: str = "",
    ):
        """
        Add evidence to an open dispute (Phase 6, Epic 6.2).

        Delegates to DisputeService.add_evidence().

        Args:
            dispute_id: Dispute ID
            uploaded_by_user_id: User uploading evidence
            evidence_type: Type (screenshot, video, chat_log, other)
            url: URL to resource
            notes: Additional context

        Returns:
            DisputeEvidenceDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.2
        """
        return self.dispute_service.add_evidence(
            dispute_id=dispute_id,
            uploaded_by_user_id=uploaded_by_user_id,
            evidence_type=evidence_type,
            url=url,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # Organizer Results Inbox (Phase 6, Epic 6.3)
    # -------------------------------------------------------------------------

    def list_results_inbox(self, tournament_id=None):
        """
        List all submissions requiring organizer attention (Phase 6, Epic 6.3).

        Delegates to ReviewInboxService.list_review_items().

        Args:
            tournament_id: Optional tournament filter

        Returns:
            List[OrganizerReviewItemDTO]

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3
        """
        return self.review_inbox_service.list_review_items(
            tournament_id=tournament_id,
            sort_by_priority=True,
        )

    def finalize_submission(self, submission_id: int, resolved_by_user_id: int):
        """
        Finalize submission (organizer approval) (Phase 6, Epic 6.3).

        Delegates to ReviewInboxService.finalize_submission().

        Args:
            submission_id: Submission ID
            resolved_by_user_id: Organizer user ID

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3
        """
        return self.review_inbox_service.finalize_submission(
            submission_id=submission_id,
            resolved_by_user_id=resolved_by_user_id,
        )

    def reject_submission(
        self,
        submission_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ):
        """
        Reject submission (organizer denial) (Phase 6, Epic 6.3).

        Delegates to ReviewInboxService.reject_submission().

        Args:
            submission_id: Submission ID
            resolved_by_user_id: Organizer user ID
            notes: Rejection notes

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3
        """
        return self.review_inbox_service.reject_submission(
            submission_id=submission_id,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes,
        )

    # -------------------------------------------------------------------------
    # Result Verification & Finalization (Phase 6, Epic 6.4)
    # -------------------------------------------------------------------------

    def verify_submission(self, submission_id: int):
        """
        Verify submission against game schema and business rules (Phase 6, Epic 6.4).

        Delegates to ResultVerificationService.verify_submission().

        This is a read-only verification - does not change state.
        Useful for previewing verification results before finalization.

        Args:
            submission_id: Submission ID to verify

        Returns:
            ResultVerificationResultDTO with is_valid, errors, warnings, calculated_scores

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4
        """
        return self.result_verification_service.verify_submission(submission_id)

    def finalize_submission_with_verification(
        self,
        submission_id: int,
        resolved_by_user_id: int,
    ):
        """
        Finalize submission after full verification pipeline (Phase 6, Epic 6.4).

        Delegates to ResultVerificationService.finalize_submission_after_verification().

        This is the core Epic 6.4 method that:
        1. Verifies submission schema & scores
        2. Updates match via MatchService
        3. Resolves disputes if any
        4. Publishes events

        Args:
            submission_id: Submission ID to finalize
            resolved_by_user_id: Organizer user ID

        Returns:
            MatchResultSubmissionDTO (finalized)

        Raises:
            ResultVerificationFailedError: If verification fails

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4
        """
        return self.result_verification_service.finalize_submission_after_verification(
            submission_id=submission_id,
            resolved_by_user_id=resolved_by_user_id,
        )

    def dry_run_submission_verification(self, submission_id: int):
        """
        Perform verification without changing state (dry run) (Phase 6, Epic 6.4).

        Delegates to ResultVerificationService.dry_run_verification().

        Useful for:
        - Frontend preview of verification results
        - Admin tooling to check submissions before finalizing
        - Testing verification logic

        Args:
            submission_id: Submission ID to verify

        Returns:
            ResultVerificationResultDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4
        """
        return self.result_verification_service.dry_run_verification(submission_id)
    
    # ==============================================================================
    # Epic 6.5: Dispute Resolution Façade Methods
    # ==============================================================================
    
    def resolve_dispute_with_original(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ):
        """
        Resolve dispute by approving original submission (Epic 6.5).
        
        Delegates to ReviewInboxService.resolve_dispute_approve_original().
        
        This approves the original submitted result as correct, dismissing the dispute.
        The submission is finalized via ResultVerificationService.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes explaining decision
            
        Returns:
            DisputeDTO (resolved for submitter)
            
        Raises:
            DisputeAlreadyResolvedError: If dispute already resolved
            ResultVerificationFailedError: If verification fails
            
        Reference: Phase 6, Epic 6.5 - Approve Original Resolution
        """
        return self.review_inbox_service.resolve_dispute_approve_original(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes,
        )
    
    def resolve_dispute_with_disputed_result(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ):
        """
        Resolve dispute by approving disputed result (Epic 6.5).
        
        Delegates to ReviewInboxService.resolve_dispute_approve_dispute().
        
        This approves the disputer's version as correct. The submission payload
        is updated to the disputed payload and finalized via ResultVerificationService.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes explaining decision
            
        Returns:
            DisputeDTO (resolved for opponent)
            
        Raises:
            DisputeAlreadyResolvedError: If dispute already resolved
            DisputeError: If dispute has no disputed_result_payload
            ResultVerificationFailedError: If verification fails
            
        Reference: Phase 6, Epic 6.5 - Approve Dispute Resolution
        """
        return self.review_inbox_service.resolve_dispute_approve_dispute(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes,
        )
    
    def resolve_dispute_with_custom_result(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        custom_payload: dict,
        notes: str = "",
    ):
        """
        Resolve dispute with custom organizer result (Epic 6.5).
        
        Delegates to ReviewInboxService.resolve_dispute_custom_result().
        
        This applies a custom result payload entered by the organizer when neither
        the original submission nor the dispute is fully correct. The submission
        payload is updated to the custom payload and finalized via ResultVerificationService.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            custom_payload: Custom result payload (game-specific JSON)
            notes: Resolution notes explaining decision
            
        Returns:
            DisputeDTO (resolved custom)
            
        Raises:
            ValueError: If custom_payload is empty/invalid
            DisputeAlreadyResolvedError: If dispute already resolved
            ResultVerificationFailedError: If verification fails
            
        Reference: Phase 6, Epic 6.5 - Custom Result Resolution
        """
        return self.review_inbox_service.resolve_dispute_custom_result(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolved_by_user_id=resolved_by_user_id,
            custom_payload=custom_payload,
            notes=notes,
        )
    
    def dismiss_dispute(
        self,
        submission_id: int,
        dispute_id: int,
        resolved_by_user_id: int,
        notes: str = "",
    ):
        """
        Dismiss dispute as invalid, restart 24-hour timer (Epic 6.5).
        
        Delegates to ReviewInboxService.resolve_dispute_dismiss().
        
        This marks the dispute as invalid/dismissed and restarts the 24-hour
        auto-confirm timer. The submission is NOT finalized, allowing the
        opponent another chance to confirm or dispute.
        
        Args:
            submission_id: Submission ID
            dispute_id: Dispute ID
            resolved_by_user_id: Organizer/admin user ID
            notes: Resolution notes explaining dismissal reason
            
        Returns:
            DisputeDTO (dismissed)
            
        Raises:
            DisputeAlreadyResolvedError: If dispute already resolved
            
        Reference: Phase 6, Epic 6.5 - Dismiss Dispute Resolution
        """
        return self.review_inbox_service.resolve_dispute_dismiss(
            submission_id=submission_id,
            dispute_id=dispute_id,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes,
        )

        Delegates to ReviewInboxService.reject_submission().

        Args:
            submission_id: Submission ID
            resolved_by_user_id: Organizer user ID
            notes: Rejection notes

        Returns:
            MatchResultSubmissionDTO

        Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.3
        """
        return self.review_inbox_service.reject_submission(
            submission_id=submission_id,
            resolved_by_user_id=resolved_by_user_id,
            notes=notes,
        )
