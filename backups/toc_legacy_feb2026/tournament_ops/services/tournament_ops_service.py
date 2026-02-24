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

from typing import Optional, Dict, Any, List
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
    
    @property
    def match_ops_service(self):
        """Lazy initialization of MatchOpsService (Phase 7, Epic 7.4)."""
        if not hasattr(self, '_match_ops_service') or self._match_ops_service is None:
            from apps.tournament_ops.services import MatchOpsService
            from apps.tournament_ops.adapters import MatchOpsAdapter, StaffingAdapter
            self._match_ops_service = MatchOpsService(
                match_ops_adapter=MatchOpsAdapter(),
                staffing_adapter=StaffingAdapter(),
                event_publisher=get_event_bus(),
            )
        return self._match_ops_service
    
    @property
    def audit_log_service(self):
        """Lazy initialization of AuditLogService (Phase 7, Epic 7.5)."""
        if not hasattr(self, '_audit_log_service') or self._audit_log_service is None:
            from apps.tournament_ops.services import AuditLogService
            from apps.tournament_ops.adapters import AuditLogAdapter
            self._audit_log_service = AuditLogService(
                audit_log_adapter=AuditLogAdapter(),
            )
        return self._audit_log_service
    
    @property
    def help_and_onboarding_service(self):
        """Lazy initialization of HelpAndOnboardingService (Phase 7, Epic 7.6)."""
        if not hasattr(self, '_help_and_onboarding_service') or self._help_and_onboarding_service is None:
            from apps.tournament_ops.services import HelpAndOnboardingService
            from apps.tournament_ops.adapters import HelpContentAdapter
            self._help_and_onboarding_service = HelpAndOnboardingService(
                help_content_adapter=HelpContentAdapter(),
            )
        return self._help_and_onboarding_service
    
    @property
    def user_stats_service(self):
        """Lazy initialization of UserStatsService (Phase 8, Epic 8.2)."""
        if not hasattr(self, '_user_stats_service') or self._user_stats_service is None:
            from apps.tournament_ops.services import UserStatsService
            from apps.tournament_ops.adapters import UserStatsAdapter
            self._user_stats_service = UserStatsService(
                adapter=UserStatsAdapter(),
            )
        return self._user_stats_service

    @property
    def team_stats_service(self):
        """Lazy initialization of TeamStatsService (Phase 8, Epic 8.3)."""
        if not hasattr(self, '_team_stats_service') or self._team_stats_service is None:
            from apps.tournament_ops.services import TeamStatsService
            from apps.tournament_ops.adapters import TeamStatsAdapter, TeamRankingAdapter
            self._team_stats_service = TeamStatsService(
                team_stats_adapter=TeamStatsAdapter(),
                team_ranking_adapter=TeamRankingAdapter(),
            )
        return self._team_stats_service

    @property
    def match_history_service(self):
        """Lazy initialization of MatchHistoryService (Phase 8, Epic 8.4)."""
        if not hasattr(self, '_match_history_service') or self._match_history_service is None:
            from apps.tournament_ops.services import MatchHistoryService
            from apps.tournament_ops.adapters import DjangoMatchHistoryAdapter
            self._match_history_service = MatchHistoryService(
                adapter=DjangoMatchHistoryAdapter(),
            )
        return self._match_history_service

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
    
    def list_results_inbox_for_organizer(
        self,
        organizer_user_id: int,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """
        List results inbox for organizer across all tournaments (Phase 7, Epic 7.1).
        
        Delegates to ReviewInboxService.list_review_items_for_organizer().
        
        Args:
            organizer_user_id: Organizer user ID
            filters: Optional filter dict
            
        Returns:
            List[OrganizerReviewItemDTO]
            
        Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1
        """
        return self.review_inbox_service.list_review_items_for_organizer(
            organizer_user_id=organizer_user_id,
            filters=filters,
        )
    
    def bulk_finalize_submissions(
        self,
        submission_ids: List[int],
        resolved_by_user_id: int,
    ) -> Dict[str, Any]:
        """
        Bulk finalize submissions (Phase 7, Epic 7.1).
        
        Delegates to ReviewInboxService.bulk_finalize_submissions().
        
        Args:
            submission_ids: List of submission IDs
            resolved_by_user_id: Organizer user ID
            
        Returns:
            Dict with 'processed', 'failed', 'items' keys
            
        Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1
        """
        return self.review_inbox_service.bulk_finalize_submissions(
            submission_ids=submission_ids,
            resolved_by_user_id=resolved_by_user_id,
        )
    
    def bulk_reject_submissions(
        self,
        submission_ids: List[int],
        resolved_by_user_id: int,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Bulk reject submissions (Phase 7, Epic 7.1).
        
        Delegates to ReviewInboxService.bulk_reject_submissions().
        
        Args:
            submission_ids: List of submission IDs
            resolved_by_user_id: Organizer user ID
            notes: Rejection notes
            
        Returns:
            Dict with 'processed', 'failed', 'items' keys
            
        Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1
        """
        return self.review_inbox_service.bulk_reject_submissions(
            submission_ids=submission_ids,
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
    
    # ========================================================================
    # Phase 7, Epic 7.2 - Manual Match Scheduling Tools
    # ========================================================================
    
    @property
    def manual_scheduling_service(self):
        """Lazy initialization of ManualSchedulingService (Phase 7, Epic 7.2)."""
        if not hasattr(self, '_manual_scheduling_service') or self._manual_scheduling_service is None:
            from apps.tournament_ops.services.manual_scheduling_service import ManualSchedulingService
            from apps.tournament_ops.adapters.match_scheduling_adapter import MatchSchedulingAdapter
            self._manual_scheduling_service = ManualSchedulingService(
                adapter=MatchSchedulingAdapter()
            )
        return self._manual_scheduling_service
    
    def list_matches_for_scheduling(
        self,
        tournament_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ):
        """
        List matches requiring scheduling by organizers (Epic 7.2).
        
        Delegates to ManualSchedulingService.list_matches_for_scheduling().
        
        Retrieves all matches that can be scheduled by organizers,
        with their scheduling metadata, conflicts, and constraints.
        
        Args:
            tournament_id: Filter by tournament
            stage_id: Filter by stage
            filters: Additional filters:
                - unscheduled_only: bool
                - with_conflicts: bool
                
        Returns:
            List[MatchSchedulingItemDTO]: Matches for scheduling
            
        Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
        """
        return self.manual_scheduling_service.list_matches_for_scheduling(
            tournament_id=tournament_id,
            stage_id=stage_id,
            filters=filters
        )
    
    def schedule_match_manually(
        self,
        match_id: int,
        scheduled_time,
        assigned_by_user_id: int,
        skip_conflict_check: bool = False
    ):
        """
        Manually assign a match to a specific time (Epic 7.2).
        
        Delegates to ManualSchedulingService.assign_match().
        
        Assigns a match to a specific time slot with conflict detection
        (soft validation - warnings not errors). Publishes domain events
        for audit and notifications.
        
        Args:
            match_id: Match to schedule
            scheduled_time: Time to schedule at (datetime)
            assigned_by_user_id: User making assignment
            skip_conflict_check: Skip conflict detection (default False)
            
        Returns:
            Dict with keys:
                - match: Updated MatchSchedulingItemDTO
                - conflicts: List of SchedulingConflictDTO (warnings)
                - was_rescheduled: bool
                
        Raises:
            ValueError: If match not found or not schedulable
            
        Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
        """
        return self.manual_scheduling_service.assign_match(
            match_id=match_id,
            scheduled_time=scheduled_time,
            assigned_by_user_id=assigned_by_user_id,
            skip_conflict_check=skip_conflict_check
        )
    
    def bulk_shift_matches(
        self,
        stage_id: int,
        delta_minutes: int,
        assigned_by_user_id: int
    ):
        """
        Bulk shift all scheduled matches in a stage (Epic 7.2).
        
        Delegates to ManualSchedulingService.bulk_shift_matches().
        
        Shifts all scheduled matches in a stage by a time delta.
        Useful for stage delays or rescheduling entire brackets.
        
        Args:
            stage_id: Stage to shift matches in
            delta_minutes: Minutes to shift (positive = later, negative = earlier)
            assigned_by_user_id: User making the change
            
        Returns:
            BulkShiftResultDTO: Results and conflicts
            
        Reference: Phase 7, Epic 7.2 - Bulk Operations
        """
        return self.manual_scheduling_service.bulk_shift_matches(
            stage_id=stage_id,
            delta_minutes=delta_minutes,
            assigned_by_user_id=assigned_by_user_id
        )
    
    def generate_scheduling_slots(
        self,
        stage_id: int,
        slot_duration_minutes: Optional[int] = None,
        interval_minutes: int = 15
    ):
        """
        Auto-generate available time slots for a stage (Epic 7.2).
        
        Delegates to ManualSchedulingService.auto_generate_slots().
        
        Generates available time slots within stage window, respecting
        blackout periods and existing scheduled matches.
        
        Args:
            stage_id: Stage to generate slots for
            slot_duration_minutes: Duration of each slot (or uses game default)
            interval_minutes: Gap between slots (default 15)
            
        Returns:
            List[SchedulingSlotDTO]: Available time slots
            
        Reference: Phase 7, Epic 7.2 - Time Slot Generation
        """
        return self.manual_scheduling_service.auto_generate_slots(
            stage_id=stage_id,
            slot_duration_minutes=slot_duration_minutes,
            interval_minutes=interval_minutes
        )
    
    # ========================================================================
    # Phase 7, Epic 7.3 - Staff & Referee Role System
    # ========================================================================
    
    @property
    def staffing_service(self):
        """Lazy initialization of StaffingService (Phase 7, Epic 7.3)."""
        if not hasattr(self, '_staffing_service') or self._staffing_service is None:
            from apps.tournament_ops.services.staffing_service import StaffingService
            from apps.tournament_ops.adapters.staffing_adapter import StaffingAdapter
            self._staffing_service = StaffingService(
                staffing_adapter=StaffingAdapter()
            )
        return self._staffing_service
    
    def get_staff_roles(self):
        """
        Get all available staff roles (Epic 7.3).
        
        Delegates to StaffingService.get_all_staff_roles().
        
        Returns:
            List[StaffRoleDTO]: All staff roles with capabilities
            
        Reference: Phase 7, Epic 7.3 - Staff Role Management
        """
        return self.staffing_service.get_all_staff_roles()
    
    def assign_tournament_staff(
        self,
        tournament_id: int,
        user_id: int,
        role_code: str,
        assigned_by_user_id: int,
        stage_id: Optional[int] = None,
        notes: str = ""
    ):
        """
        Assign a staff member to a tournament (Epic 7.3).
        
        Delegates to StaffingService.assign_staff_to_tournament().
        
        Assigns a user with a specific role to a tournament or stage.
        Validates role capabilities and publishes assignment events.
        
        Args:
            tournament_id: Tournament to assign staff to
            user_id: User to assign
            role_code: Role code (e.g., 'HEAD_ADMIN', 'REFEREE')
            assigned_by_user_id: User making the assignment
            stage_id: Optional stage for stage-specific assignment
            notes: Optional notes about assignment
            
        Returns:
            TournamentStaffAssignmentDTO: Created assignment
            
        Raises:
            ValueError: If validation fails
            
        Reference: Phase 7, Epic 7.3 - Staff Assignment
        """
        return self.staffing_service.assign_staff_to_tournament(
            tournament_id=tournament_id,
            user_id=user_id,
            role_code=role_code,
            assigned_by_user_id=assigned_by_user_id,
            stage_id=stage_id,
            notes=notes
        )
    
    def remove_tournament_staff(self, assignment_id: int):
        """
        Remove a staff member from a tournament (Epic 7.3).
        
        Delegates to StaffingService.remove_staff_from_tournament().
        
        Deactivates a staff assignment. Prevents removal if staff
        has active referee assignments to matches.
        
        Args:
            assignment_id: Staff assignment ID to remove
            
        Returns:
            TournamentStaffAssignmentDTO: Updated assignment (is_active=False)
            
        Raises:
            ValueError: If assignment has active referee duties
            
        Reference: Phase 7, Epic 7.3 - Staff Removal
        """
        return self.staffing_service.remove_staff_from_tournament(
            assignment_id=assignment_id
        )
    
    def get_tournament_staff(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None,
        role_code: Optional[str] = None,
        is_active: Optional[bool] = True
    ):
        """
        Get all staff assigned to a tournament (Epic 7.3).
        
        Delegates to StaffingService.get_tournament_staff().
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage filter
            role_code: Optional role filter
            is_active: Optional active status filter
            
        Returns:
            List[TournamentStaffAssignmentDTO]: Staff assignments
            
        Reference: Phase 7, Epic 7.3 - Staff Queries
        """
        return self.staffing_service.get_tournament_staff(
            tournament_id=tournament_id,
            stage_id=stage_id,
            role_code=role_code,
            is_active=is_active
        )
    
    def assign_match_referee(
        self,
        match_id: int,
        staff_assignment_id: int,
        assigned_by_user_id: int,
        is_primary: bool = False,
        notes: str = "",
        check_load: bool = True
    ):
        """
        Assign a referee to a match (Epic 7.3).
        
        Delegates to StaffingService.assign_referee_to_match().
        
        Assigns a referee (staff with referee role) to a specific match.
        Checks referee load and provides soft warning if overloaded.
        
        Args:
            match_id: Match ID
            staff_assignment_id: Staff assignment ID (must be referee role)
            assigned_by_user_id: User making the assignment
            is_primary: Whether this is the primary referee
            notes: Optional notes
            check_load: Whether to check load (default True)
            
        Returns:
            Tuple[MatchRefereeAssignmentDTO, Optional[str]]:
                - Created assignment
                - Optional warning message if referee overloaded
                
        Raises:
            ValueError: If validation fails
            
        Reference: Phase 7, Epic 7.3 - Referee Assignment
        """
        return self.staffing_service.assign_referee_to_match(
            match_id=match_id,
            staff_assignment_id=staff_assignment_id,
            assigned_by_user_id=assigned_by_user_id,
            is_primary=is_primary,
            notes=notes,
            check_load=check_load
        )
    
    def unassign_match_referee(self, referee_assignment_id: int):
        """
        Remove a referee from a match (Epic 7.3).
        
        Delegates to StaffingService.unassign_referee_from_match().
        
        Args:
            referee_assignment_id: Referee assignment ID to remove
            
        Raises:
            ValueError: If assignment not found
            
        Reference: Phase 7, Epic 7.3 - Referee Unassignment
        """
        return self.staffing_service.unassign_referee_from_match(
            referee_assignment_id=referee_assignment_id
        )
    
    def get_match_referees(self, match_id: int):
        """
        Get all referees assigned to a match (Epic 7.3).
        
        Delegates to StaffingService.get_match_referees().
        
        Args:
            match_id: Match ID
            
        Returns:
            List[MatchRefereeAssignmentDTO]: Referee assignments (primary first)
            
        Reference: Phase 7, Epic 7.3 - Match Staffing Queries
        """
        return self.staffing_service.get_match_referees(
            match_id=match_id
        )
    
    def calculate_staff_load(
        self,
        tournament_id: int,
        stage_id: Optional[int] = None
    ):
        """
        Calculate workload for all staff in a tournament (Epic 7.3).
        
        Delegates to StaffingService.calculate_staff_load().
        
        Aggregates match assignments to determine referee load,
        useful for load balancing and identifying overloaded staff.
        
        Args:
            tournament_id: Tournament ID
            stage_id: Optional stage filter
            
        Returns:
            List[StaffLoadDTO]: Staff load summaries (sorted by load descending)
            
        Reference: Phase 7, Epic 7.3 - Load Balancing
        """
        return self.staffing_service.calculate_staff_load(
            tournament_id=tournament_id,
            stage_id=stage_id
        )
    
    # -------------------------------------------------------------------------
    # Match Operations Command Center (Phase 7, Epic 7.4)
    # -------------------------------------------------------------------------
    
    def mark_match_live(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int
    ):
        """
        Mark a match as LIVE (in progress).
        
        Delegates to MatchOpsService.mark_match_live().
        
        Business Rules:
        - User must have can_modify_matches permission
        - Match must be in PENDING status
        - Logs operation and publishes MatchWentLiveEvent
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            operator_user_id: User performing operation
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in valid state
            
        Reference: Phase 7, Epic 7.4 - Live Match Control
        """
        return self.match_ops_service.mark_match_live(
            match_id=match_id,
            tournament_id=tournament_id,
            operator_user_id=operator_user_id
        )
    
    def pause_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        reason: Optional[str] = None
    ):
        """
        Pause a live match.
        
        Delegates to MatchOpsService.pause_match().
        
        Business Rules:
        - User must have can_pause permission
        - Match must be in LIVE status
        - Reason is recommended but optional
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            operator_user_id: User performing operation
            reason: Optional pause reason
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in LIVE state
            
        Reference: Phase 7, Epic 7.4 - Match Control
        """
        return self.match_ops_service.pause_match(
            match_id=match_id,
            tournament_id=tournament_id,
            operator_user_id=operator_user_id,
            reason=reason
        )
    
    def resume_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int
    ):
        """
        Resume a paused match.
        
        Delegates to MatchOpsService.resume_match().
        
        Business Rules:
        - User must have can_resume permission
        - Match must be in PAUSED status
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            operator_user_id: User performing operation
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If match not in PAUSED state
            
        Reference: Phase 7, Epic 7.4 - Match Control
        """
        return self.match_ops_service.resume_match(
            match_id=match_id,
            tournament_id=tournament_id,
            operator_user_id=operator_user_id
        )
    
    def force_complete_match(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        reason: str,
        result_data: Optional[Dict[str, Any]] = None
    ):
        """
        Force-complete a match (admin action).
        
        Delegates to MatchOpsService.force_complete_match().
        
        Business Rules:
        - User must have can_force_complete permission
        - Reason is required (audit trail)
        - Optional result data
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            operator_user_id: User performing operation
            reason: Required reason for force completion
            result_data: Optional result payload
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If reason missing
            
        Reference: Phase 7, Epic 7.4 - Admin Operations
        """
        return self.match_ops_service.force_complete_match(
            match_id=match_id,
            tournament_id=tournament_id,
            operator_user_id=operator_user_id,
            reason=reason,
            result_data=result_data
        )
    
    def add_match_note(
        self,
        match_id: int,
        tournament_id: int,
        author_user_id: int,
        content: str
    ):
        """
        Add a moderator note to a match.
        
        Delegates to MatchOpsService.add_moderator_note().
        
        Business Rules:
        - User must have can_add_note permission
        - Content cannot be empty
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            author_user_id: User adding note
            content: Note content
            
        Returns:
            MatchModeratorNoteDTO: Created note
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If content empty
            
        Reference: Phase 7, Epic 7.4 - Staff Communication
        """
        return self.match_ops_service.add_moderator_note(
            match_id=match_id,
            tournament_id=tournament_id,
            author_user_id=author_user_id,
            content=content
        )
    
    def get_match_timeline(
        self,
        match_id: int,
        limit: int = 50
    ):
        """
        Get aggregated timeline of match events.
        
        Delegates to MatchOpsService.get_match_timeline().
        
        Combines:
        - Operation logs
        - Result submissions (future integration)
        - Disputes (future integration)
        - Scheduling changes (future integration)
        
        Args:
            match_id: Match ID
            limit: Maximum events to return
            
        Returns:
            List[MatchTimelineEventDTO]: Timeline ordered by timestamp DESC
            
        Reference: Phase 7, Epic 7.4 - Match Timeline
        """
        return self.match_ops_service.get_match_timeline(
            match_id=match_id,
            limit=limit
        )
    
    def override_match_result(
        self,
        match_id: int,
        tournament_id: int,
        operator_user_id: int,
        new_result_data: Dict[str, Any],
        reason: str
    ):
        """
        Override match result (admin action).
        
        Delegates to MatchOpsService.override_match_result().
        
        Business Rules:
        - User must have can_override_result permission
        - Reason is required (critical audit trail)
        - Old result is preserved in operation log
        
        Args:
            match_id: Match ID
            tournament_id: Tournament ID
            operator_user_id: User performing operation
            new_result_data: New result payload
            reason: Required reason for override
            
        Returns:
            MatchOpsActionResultDTO: Operation result
            
        Raises:
            PermissionError: If user lacks permission
            ValueError: If reason missing or result invalid
            
        Reference: Phase 7, Epic 7.4 - Result Override
        """
        return self.match_ops_service.override_match_result(
            match_id=match_id,
            tournament_id=tournament_id,
            operator_user_id=operator_user_id,
            new_result_data=new_result_data,
            reason=reason
        )
    
    def view_match_operations_dashboard(
        self,
        tournament_id: int,
        user_id: int,
        status_filter: Optional[str] = None
    ):
        """
        Get match operations dashboard for tournament.
        
        Delegates to MatchOpsService.get_operations_dashboard().
        
        Provides overview of all matches with:
        - Match state
        - Assigned referee
        - Pending actions
        - Recent activity
        
        Args:
            tournament_id: Tournament ID
            user_id: User viewing dashboard (for permissions)
            status_filter: Optional filter (LIVE, PENDING, etc.)
            
        Returns:
            List[MatchOpsDashboardItemDTO]: Dashboard items
            
        Reference: Phase 7, Epic 7.4 - Operations Dashboard
        """
        return self.match_ops_service.get_operations_dashboard(
            tournament_id=tournament_id,
            user_id=user_id,
            status_filter=status_filter
        )
    
    # -------------------------------------------------------------------------
    # Audit Log System (Phase 7, Epic 7.5)
    # -------------------------------------------------------------------------
    
    def create_audit_log(
        self,
        user_id: Optional[int],
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        tournament_id: Optional[int] = None,
        match_id: Optional[int] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Create audit log entry.
        
        Delegates to AuditLogService.log_action().
        
        Records administrative actions with full context including:
        - User/actor
        - Action type
        - Tournament/match context
        - Before/after state (for change tracking)
        - Request metadata (IP, user agent, correlation ID)
        
        Args:
            user_id: User performing action (None for system)
            action: Action type (e.g., 'result_finalized')
            metadata: Additional action metadata
            ip_address: Client IP address
            user_agent: Client user agent
            tournament_id: Tournament context
            match_id: Match context
            before_state: State before action
            after_state: State after action
            correlation_id: Request correlation ID
            
        Returns:
            AuditLogDTO: Created audit log entry
            
        Reference: Phase 7, Epic 7.5 - Audit Log Creation
        """
        return self.audit_log_service.log_action(
            user_id=user_id,
            action=action,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            tournament_id=tournament_id,
            match_id=match_id,
            before_state=before_state,
            after_state=after_state,
            correlation_id=correlation_id
        )
    
    def get_audit_logs(
        self,
        filters
    ):
        """
        List audit logs with filtering.
        
        Delegates to AuditLogService.list_logs().
        
        Supports filtering by:
        - User
        - Action type
        - Tournament
        - Match
        - Date range
        - State changes
        
        Args:
            filters: AuditLogFilterDTO with filter parameters
            
        Returns:
            List[AuditLogDTO]: Filtered audit log entries
            
        Reference: Phase 7, Epic 7.5 - Audit Log Queries
        """
        return self.audit_log_service.list_logs(filters)
    
    def count_audit_logs(self, filters):
        """
        Count audit logs matching filters.
        
        Delegates to AuditLogService.count_logs().
        
        Args:
            filters: AuditLogFilterDTO with filter parameters
            
        Returns:
            int: Total count (for pagination)
            
        Reference: Phase 7, Epic 7.5 - Audit Log Pagination
        """
        return self.audit_log_service.count_logs(filters)
    
    def get_tournament_audit_trail(
        self,
        tournament_id: int,
        limit: int = 100
    ):
        """
        Get audit trail for specific tournament.
        
        Delegates to AuditLogService.get_tournament_audit_trail().
        
        Args:
            tournament_id: Tournament ID
            limit: Maximum entries
            
        Returns:
            List[AuditLogDTO]: Tournament audit trail
            
        Reference: Phase 7, Epic 7.5 - Tournament Audit Trail
        """
        return self.audit_log_service.get_tournament_audit_trail(
            tournament_id=tournament_id,
            limit=limit
        )
    
    def get_match_audit_trail(
        self,
        match_id: int,
        limit: int = 100
    ):
        """
        Get audit trail for specific match.
        
        Delegates to AuditLogService.get_match_audit_trail().
        
        Args:
            match_id: Match ID
            limit: Maximum entries
            
        Returns:
            List[AuditLogDTO]: Match audit trail
            
        Reference: Phase 7, Epic 7.5 - Match Audit Trail
        """
        return self.audit_log_service.get_match_audit_trail(
            match_id=match_id,
            limit=limit
        )
    
    def get_user_audit_trail(
        self,
        user_id: int,
        limit: int = 100
    ):
        """
        Get audit trail for specific user.
        
        Delegates to AuditLogService.get_user_audit_trail().
        
        Args:
            user_id: User ID
            limit: Maximum entries
            
        Returns:
            List[AuditLogDTO]: User audit trail
            
        Reference: Phase 7, Epic 7.5 - User Audit Trail
        """
        return self.audit_log_service.get_user_audit_trail(
            user_id=user_id,
            limit=limit
        )
    
    def export_audit_logs(self, filters):
        """
        Export audit logs in CSV format.
        
        Delegates to AuditLogService.export_logs_to_csv().
        
        Args:
            filters: AuditLogFilterDTO with filter parameters
            
        Returns:
            List[AuditLogExportDTO]: Export-ready audit data
            
        Reference: Phase 7, Epic 7.5 - Audit Log Export
        """
        return self.audit_log_service.export_logs_to_csv(filters)
    
    def get_recent_audit_activity(
        self,
        tournament_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20
    ):
        """
        Get recent audit activity for dashboard display.
        
        Delegates to AuditLogService.get_recent_activity().
        
        Args:
            tournament_id: Filter by tournament (optional)
            user_id: Filter by user (optional)
            limit: Maximum entries (default 20)
            
        Returns:
            List[AuditLogDTO]: Recent audit entries
            
        Reference: Phase 7, Epic 7.5 - Audit Activity Feed
        """
        return self.audit_log_service.get_recent_activity(
            tournament_id=tournament_id,
            user_id=user_id,
            limit=limit
        )
    
    # -------------------------------------------------------------------------
    # Help & Onboarding (Phase 7, Epic 7.6)
    # -------------------------------------------------------------------------
    
    def get_help_for_page(
        self,
        page_id: str,
        user_id: int,
        audience: str = 'organizer',
        tournament_id: Optional[int] = None
    ):
        """
        Get complete help bundle for a page.
        
        Delegates to HelpAndOnboardingService.get_help_bundle().
        Returns help content, overlays, and onboarding state.
        
        Args:
            page_id: Page identifier (e.g., 'results_inbox', 'scheduling')
            user_id: Current user ID
            audience: Target audience ('organizer', 'referee', 'player', 'global')
            tournament_id: Optional tournament ID for tournament-specific onboarding
            
        Returns:
            HelpBundleDTO: Complete help resources for the page
            
        Reference: Phase 7, Epic 7.6 - Help & Onboarding
        """
        return self.help_and_onboarding_service.get_help_bundle(
            page_id=page_id,
            user_id=user_id,
            audience=audience,
            tournament_id=tournament_id
        )
    
    def complete_onboarding_step(
        self,
        user_id: int,
        step_key: str,
        tournament_id: Optional[int] = None
    ):
        """
        Mark an onboarding step as completed.
        
        Delegates to HelpAndOnboardingService.complete_onboarding_step().
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier
            tournament_id: Optional tournament ID
            
        Returns:
            OnboardingStepDTO: Updated step state
            
        Reference: Phase 7, Epic 7.6 - Onboarding Wizard
        """
        return self.help_and_onboarding_service.complete_onboarding_step(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id
        )
    
    def dismiss_help_item(
        self,
        user_id: int,
        step_key: str,
        tournament_id: Optional[int] = None
    ):
        """
        Dismiss/skip an onboarding step.
        
        Delegates to HelpAndOnboardingService.dismiss_help_item().
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier
            tournament_id: Optional tournament ID
            
        Returns:
            OnboardingStepDTO: Updated step state
            
        Reference: Phase 7, Epic 7.6 - Help Dismissal
        """
        return self.help_and_onboarding_service.dismiss_help_item(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id
        )
    
    def get_onboarding_progress(
        self,
        user_id: int,
        tournament_id: Optional[int] = None
    ):
        """
        Get summary of user's onboarding progress.
        
        Delegates to HelpAndOnboardingService.get_onboarding_progress().
        
        Args:
            user_id: User ID
            tournament_id: Optional tournament ID
            
        Returns:
            dict: Progress summary with counts and percentage
            
        Reference: Phase 7, Epic 7.6 - Onboarding Progress
        """
        return self.help_and_onboarding_service.get_onboarding_progress(
            user_id=user_id,
            tournament_id=tournament_id
        )
    
    # -------------------------------------------------------------------------
    # User Stats Façade Methods (Phase 8, Epic 8.2)
    # -------------------------------------------------------------------------
    
    def get_user_stats(
        self,
        user_id: int,
        game_slug: str
    ):
        """
        Get user statistics for a specific game.
        
        Delegates to UserStatsService.get_user_stats().
        
        Args:
            user_id: User ID
            game_slug: Game identifier (e.g., 'valorant', 'csgo')
            
        Returns:
            UserStatsDTO or None if no stats exist
            
        Reference: Phase 8, Epic 8.2 - User Stats Retrieval
        """
        return self.user_stats_service.get_user_stats(
            user_id=user_id,
            game_slug=game_slug
        )
    
    def get_all_user_stats(self, user_id: int):
        """
        Get all statistics for a user across all games.
        
        Delegates to UserStatsService.get_all_user_stats().
        
        Args:
            user_id: User ID
            
        Returns:
            List of UserStatsDTO instances
            
        Reference: Phase 8, Epic 8.2 - Multi-Game Stats
        """
        return self.user_stats_service.get_all_user_stats(user_id=user_id)
    
    def get_user_stats_summary(
        self,
        user_id: int,
        game_slug: Optional[str] = None
    ):
        """
        Get summary statistics for a user.
        
        Delegates to UserStatsService.get_user_summary().
        
        Args:
            user_id: User ID
            game_slug: Optional game filter
            
        Returns:
            Dictionary with summary statistics
            
        Reference: Phase 8, Epic 8.2 - Stats Summary API
        """
        return self.user_stats_service.get_user_summary(
            user_id=user_id,
            game_slug=game_slug
        )
    
    def update_user_stats_from_match(
        self,
        match_update
    ):
        """
        Update user stats based on match completion.
        
        Delegates to UserStatsService.update_stats_for_match().
        Called by MatchCompletedEvent handler.
        
        Args:
            match_update: MatchStatsUpdateDTO with match outcome data
            
        Returns:
            Updated UserStatsDTO
            
        Reference: Phase 8, Epic 8.2 - Event-Driven Stats
        """
        return self.user_stats_service.update_stats_for_match(match_update)
    
    def get_top_stats_for_game(
        self,
        game_slug: str,
        limit: int = 100
    ):
        """
        Get top-performing users for a specific game.
        
        Delegates to UserStatsService.get_top_stats_for_game().
        Used for leaderboard generation.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results
            
        Returns:
            List of UserStatsDTO instances
            
        Reference: Phase 8, Epic 8.2 - Leaderboard Integration
        """
        return self.user_stats_service.get_top_stats_for_game(
            game_slug=game_slug,
            limit=limit
        )

    # -------------------------------------------------------------------------
    # Team Stats & Ranking Facade (Phase 8, Epic 8.3)
    # -------------------------------------------------------------------------

    def get_team_stats(self, team_id: int, game_slug: str):
        """
        Get statistics for a specific team + game.
        
        Delegates to TeamStatsService.get_team_stats().
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamStatsDTO or None
            
        Reference: Phase 8, Epic 8.3 - Team Stats
        """
        return self.team_stats_service.get_team_stats(
            team_id=team_id,
            game_slug=game_slug
        )

    def get_all_team_stats(self, team_id: int):
        """
        Get statistics for a team across all games.
        
        Delegates to TeamStatsService.get_all_team_stats().
        
        Args:
            team_id: Team primary key
            
        Returns:
            List of TeamStatsDTO instances
            
        Reference: Phase 8, Epic 8.3 - Team Stats
        """
        return self.team_stats_service.get_all_team_stats(team_id=team_id)

    def get_team_ranking(self, team_id: int, game_slug: str):
        """
        Get ELO ranking for a specific team + game.
        
        Delegates to TeamStatsService.get_team_ranking().
        
        Args:
            team_id: Team primary key
            game_slug: Game identifier
            
        Returns:
            TeamRankingDTO or None
            
        Reference: Phase 8, Epic 8.3 - Team Ranking
        """
        return self.team_stats_service.get_team_ranking(
            team_id=team_id,
            game_slug=game_slug
        )

    def update_team_stats_from_match(self, match_update):
        """
        Update team stats and ELO rating after match completion.
        
        Delegates to TeamStatsService.update_stats_for_match().
        Called by event handlers to update team statistics.
        
        Args:
            match_update: TeamMatchStatsUpdateDTO
            
        Returns:
            dict with stats, ranking, and elo_change
            
        Reference: Phase 8, Epic 8.3 - Match Stats Update
        """
        return self.team_stats_service.update_stats_for_match(match_update)

    def get_top_teams_by_elo(self, game_slug: str, limit: int = 100):
        """
        Get top-ranked teams for a specific game by ELO rating.
        
        Delegates to TeamStatsService.get_top_teams_by_elo().
        Used for leaderboard generation.
        
        Args:
            game_slug: Game identifier
            limit: Maximum number of results
            
        Returns:
            List of TeamRankingDTO instances ordered by ELO
            
        Reference: Phase 8, Epic 8.3 - Leaderboard Integration
        """
        return self.team_stats_service.get_top_teams_by_elo(
            game_slug=game_slug,
            limit=limit
        )

    def get_team_stats_summary(self, team_id: int, game_slug: Optional[str] = None):
        """
        Get comprehensive stats summary for a team.
        
        Delegates to TeamStatsService.get_team_summary().
        
        Args:
            team_id: Team primary key
            game_slug: Optional game identifier (None = all games)
            
        Returns:
            TeamStatsSummaryDTO or List[TeamStatsSummaryDTO]
            
        Reference: Phase 8, Epic 8.3 - Team Stats Summary
        """
        return self.team_stats_service.get_team_summary(
            team_id=team_id,
            game_slug=game_slug
        )

    # -------------------------------------------------------------------------
    # Match History (Phase 8, Epic 8.4)
    # -------------------------------------------------------------------------

    def get_user_match_history(
        self,
        user_id: int,
        game_slug: Optional[str] = None,
        tournament_id: Optional[int] = None,
        from_date=None,
        to_date=None,
        only_wins: bool = False,
        only_losses: bool = False,
        limit: int = 20,
        offset: int = 0,
    ):
        """
        Get user match history with filters and pagination.
        
        Delegates to MatchHistoryService.get_user_match_history().
        Returns (list of UserMatchHistoryDTO, total count) tuple.
        
        Args:
            user_id: User ID (required)
            game_slug: Filter by game (optional)
            tournament_id: Filter by tournament (optional)
            from_date: Filter by date range start (optional)
            to_date: Filter by date range end (optional)
            only_wins: Show only wins (optional)
            only_losses: Show only losses (optional)
            limit: Results per page (1-100, default 20)
            offset: Offset for pagination (default 0)
            
        Returns:
            Tuple of (list of UserMatchHistoryDTO, total count)
            
        Reference: Phase 8, Epic 8.4 - Match History Engine
        """
        return self.match_history_service.get_user_match_history(
            user_id=user_id,
            game_slug=game_slug,
            tournament_id=tournament_id,
            from_date=from_date,
            to_date=to_date,
            only_wins=only_wins,
            only_losses=only_losses,
            limit=limit,
            offset=offset,
        )

    def get_team_match_history(
        self,
        team_id: int,
        game_slug: Optional[str] = None,
        tournament_id: Optional[int] = None,
        from_date=None,
        to_date=None,
        only_wins: bool = False,
        only_losses: bool = False,
        limit: int = 20,
        offset: int = 0,
    ):
        """
        Get team match history with filters and pagination.
        
        Delegates to MatchHistoryService.get_team_match_history().
        Returns (list of TeamMatchHistoryDTO, total count) tuple.
        
        Args:
            team_id: Team ID (required)
            game_slug: Filter by game (optional)
            tournament_id: Filter by tournament (optional)
            from_date: Filter by date range start (optional)
            to_date: Filter by date range end (optional)
            only_wins: Show only wins (optional)
            only_losses: Show only losses (optional)
            limit: Results per page (1-100, default 20)
            offset: Offset for pagination (default 0)
            
        Returns:
            Tuple of (list of TeamMatchHistoryDTO, total count)
            
        Reference: Phase 8, Epic 8.4 - Match History Engine
        """
        return self.match_history_service.get_team_match_history(
            team_id=team_id,
            game_slug=game_slug,
            tournament_id=tournament_id,
            from_date=from_date,
            to_date=to_date,
            only_wins=only_wins,
            only_losses=only_losses,
            limit=limit,
            offset=offset,
        )

    def record_user_match_history(
        self,
        user_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_user_id: Optional[int],
        opponent_name: str,
        score_summary: str,
        kills: int = 0,
        deaths: int = 0,
        assists: int = 0,
        had_dispute: bool = False,
        is_forfeit: bool = False,
        completed_at=None,
    ):
        """
        Record a user match history entry.
        
        Delegates to MatchHistoryService.record_user_match_history().
        Called by event handlers after match completion.
        
        Args:
            user_id: User participating in match
            match_id: Match ID reference
            tournament_id: Tournament ID reference
            game_slug: Game identifier
            is_winner: Whether user won
            is_draw: Whether match was a draw
            opponent_user_id: Opponent user ID (for 1v1)
            opponent_name: Opponent display name
            score_summary: Score summary string
            kills/deaths/assists: Match stats
            had_dispute: Whether match had dispute
            is_forfeit: Whether match ended in forfeit
            completed_at: Match completion timestamp (defaults to now)
            
        Returns:
            UserMatchHistoryDTO of created/updated record
            
        Reference: Phase 8, Epic 8.4 - Match History Recording
        """
        return self.match_history_service.record_user_match_history(
            user_id=user_id,
            match_id=match_id,
            tournament_id=tournament_id,
            game_slug=game_slug,
            is_winner=is_winner,
            is_draw=is_draw,
            opponent_user_id=opponent_user_id,
            opponent_name=opponent_name,
            score_summary=score_summary,
            kills=kills,
            deaths=deaths,
            assists=assists,
            had_dispute=had_dispute,
            is_forfeit=is_forfeit,
            completed_at=completed_at,
        )

    def record_team_match_history(
        self,
        team_id: int,
        match_id: int,
        tournament_id: int,
        game_slug: str,
        is_winner: bool,
        is_draw: bool,
        opponent_team_id: Optional[int],
        opponent_team_name: str,
        score_summary: str,
        elo_before: Optional[int] = None,
        elo_after: Optional[int] = None,
        elo_change: int = 0,
        had_dispute: bool = False,
        is_forfeit: bool = False,
        completed_at=None,
    ):
        """
        Record a team match history entry.
        
        Delegates to MatchHistoryService.record_team_match_history().
        Called by event handlers after team match completion.
        
        Args:
            team_id: Team participating in match
            match_id: Match ID reference
            tournament_id: Tournament ID reference
            game_slug: Game identifier
            is_winner: Whether team won
            is_draw: Whether match was a draw
            opponent_team_id: Opponent team ID
            opponent_team_name: Opponent team name
            score_summary: Score summary string
            elo_before/after/change: ELO rating tracking
            had_dispute: Whether match had dispute
            is_forfeit: Whether match ended in forfeit
            completed_at: Match completion timestamp (defaults to now)
            
        Returns:
            TeamMatchHistoryDTO of created/updated record
            
        Reference: Phase 8, Epic 8.4 - Match History Recording
        """
        return self.match_history_service.record_team_match_history(
            team_id=team_id,
            match_id=match_id,
            tournament_id=tournament_id,
            game_slug=game_slug,
            is_winner=is_winner,
            is_draw=is_draw,
            opponent_team_id=opponent_team_id,
            opponent_team_name=opponent_team_name,
            score_summary=score_summary,
            elo_before=elo_before,
            elo_after=elo_after,
            elo_change=elo_change,
            had_dispute=had_dispute,
            is_forfeit=is_forfeit,
            completed_at=completed_at,
        )
    
    # ========================================================================
    # Phase 8, Epic 8.5: Advanced Analytics Methods
    # ========================================================================
    
    def get_user_analytics(
        self,
        user_id: int,
        game_slug: str
    ):
        """
        Get comprehensive analytics for a user in a specific game.
        
        Returns rich analytics snapshot with:
        - MMR/ELO snapshot
        - Win rates (overall + rolling 7d/30d)
        - KDA ratio
        - Match volume metrics
        - Streak detection
        - Tier assignment (Bronze/Silver/Gold/Diamond/Crown)
        - Percentile ranking
        
        Args:
            user_id: User ID
            game_slug: Game identifier
        
        Returns:
            UserAnalyticsDTO with computed analytics
        
        Reference: Phase 8, Epic 8.5 - Advanced Analytics
        """
        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
        from apps.tournament_ops.adapters import (
            AnalyticsAdapter,
            DjangoMatchHistoryAdapter,
        )
        
        # Initialize analytics engine
        analytics_engine = AnalyticsEngineService(
            analytics_adapter=AnalyticsAdapter(),
            user_stats_adapter=self.user_stats_service.adapter,
            team_stats_adapter=self.team_stats_service.adapter,
            team_ranking_adapter=self.team_stats_service.ranking_adapter,
            match_history_adapter=DjangoMatchHistoryAdapter(),
        )
        
        # Get or compute analytics snapshot
        analytics_adapter = AnalyticsAdapter()
        snapshot = analytics_adapter.get_user_snapshot(user_id, game_slug)
        
        if not snapshot:
            # Compute fresh analytics if not exists
            snapshot = analytics_engine.compute_user_analytics(user_id, game_slug)
        
        return snapshot
    
    def get_team_analytics(
        self,
        team_id: int,
        game_slug: str
    ):
        """
        Get comprehensive analytics for a team in a specific game.
        
        Returns rich analytics snapshot with:
        - Team ELO snapshot + volatility
        - Average member skill
        - Win rates (overall + rolling 7d/30d)
        - Synergy score (performance consistency)
        - Activity score (recent match participation)
        - Tier assignment
        - Percentile ranking
        
        Args:
            team_id: Team ID
            game_slug: Game identifier
        
        Returns:
            TeamAnalyticsDTO with computed analytics
        
        Reference: Phase 8, Epic 8.5 - Advanced Analytics
        """
        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
        from apps.tournament_ops.adapters import (
            AnalyticsAdapter,
            DjangoMatchHistoryAdapter,
        )
        
        # Initialize analytics engine
        analytics_engine = AnalyticsEngineService(
            analytics_adapter=AnalyticsAdapter(),
            user_stats_adapter=self.user_stats_service.adapter,
            team_stats_adapter=self.team_stats_service.adapter,
            team_ranking_adapter=self.team_stats_service.ranking_adapter,
            match_history_adapter=DjangoMatchHistoryAdapter(),
        )
        
        # Get or compute analytics snapshot
        analytics_adapter = AnalyticsAdapter()
        snapshot = analytics_adapter.get_team_snapshot(team_id, game_slug)
        
        if not snapshot:
            # Compute fresh analytics if not exists
            snapshot = analytics_engine.compute_team_analytics(team_id, game_slug)
        
        return snapshot
    
    def get_leaderboard(
        self,
        leaderboard_type: str,
        game_slug: Optional[str] = None,
        season_id: Optional[str] = None,
        limit: int = 100
    ):
        """
        Get leaderboard entries with filtering.
        
        Supported leaderboard types:
        - "global_user": Global user rankings (all games)
        - "game_user": Game-specific user rankings
        - "team": Team rankings
        - "seasonal": Seasonal user rankings
        - "mmr"/"elo": MMR/ELO-based rankings
        - "tier": Tier-based rankings (Crown → Diamond → Gold → Silver → Bronze)
        
        Args:
            leaderboard_type: Type of leaderboard
            game_slug: Optional game filter
            season_id: Optional season filter
            limit: Maximum entries
        
        Returns:
            List[LeaderboardEntryDTO] sorted by rank
        
        Reference: Phase 8, Epic 8.5 - Real-Time Leaderboards
        """
        from apps.tournament_ops.adapters import AnalyticsAdapter
        
        analytics_adapter = AnalyticsAdapter()
        return analytics_adapter.get_leaderboard(
            leaderboard_type=leaderboard_type,
            game_slug=game_slug,
            season_id=season_id,
            limit=limit,
        )
    
    def refresh_leaderboards(self):
        """
        Refresh all leaderboards (trigger background job).
        
        Queues leaderboard refresh job via Celery.
        Returns immediately with job ID.
        
        Returns:
            dict: {'job_id': str, 'status': 'queued'}
        
        Reference: Phase 8, Epic 8.5 - Leaderboard Refresh
        """
        from apps.leaderboards.tasks import hourly_leaderboard_refresh
        
        # Queue Celery task
        result = hourly_leaderboard_refresh.delay()
        
        return {
            'job_id': result.id,
            'status': 'queued',
        }
    
    def refresh_user_analytics(self, user_id: int, game_slug: str):
        """
        Refresh analytics for a specific user (synchronous).
        
        Computes fresh analytics snapshot and returns result.
        Use sparingly - prefer batch refresh via Celery jobs.
        
        Args:
            user_id: User ID
            game_slug: Game identifier
        
        Returns:
            UserAnalyticsDTO with fresh analytics
        
        Reference: Phase 8, Epic 8.5 - Analytics Refresh
        """
        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
        from apps.tournament_ops.adapters import (
            AnalyticsAdapter,
            DjangoMatchHistoryAdapter,
        )
        
        analytics_engine = AnalyticsEngineService(
            analytics_adapter=AnalyticsAdapter(),
            user_stats_adapter=self.user_stats_service.adapter,
            team_stats_adapter=self.team_stats_service.adapter,
            team_ranking_adapter=self.team_stats_service.ranking_adapter,
            match_history_adapter=DjangoMatchHistoryAdapter(),
        )
        
        return analytics_engine.compute_user_analytics(user_id, game_slug)
    
    def refresh_team_analytics(self, team_id: int, game_slug: str):
        """
        Refresh analytics for a specific team (synchronous).
        
        Computes fresh analytics snapshot and returns result.
        Use sparingly - prefer batch refresh via Celery jobs.
        
        Args:
            team_id: Team ID
            game_slug: Game identifier
        
        Returns:
            TeamAnalyticsDTO with fresh analytics
        
        Reference: Phase 8, Epic 8.5 - Analytics Refresh
        """
        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
        from apps.tournament_ops.adapters import (
            AnalyticsAdapter,
            DjangoMatchHistoryAdapter,
        )
        
        analytics_engine = AnalyticsEngineService(
            analytics_adapter=AnalyticsAdapter(),
            user_stats_adapter=self.user_stats_service.adapter,
            team_stats_adapter=self.team_stats_service.adapter,
            team_ranking_adapter=self.team_stats_service.ranking_adapter,
            match_history_adapter=DjangoMatchHistoryAdapter(),
        )
        
        return analytics_engine.compute_team_analytics(team_id, game_slug)


# ============================================================================
# Singleton Factory
# ============================================================================

_service_instance = None


def get_tournament_ops_service() -> TournamentOpsService:
    """
    Get singleton instance of TournamentOpsService.
    
    Used by API views to access the unified service façade.
    
    Returns:
        TournamentOpsService: Singleton service instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = TournamentOpsService()
    return _service_instance
