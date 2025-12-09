"""
TournamentOps services package.

This package contains high-level orchestration services that coordinate cross-domain
operations for tournament workflows. Services use adapters to access domain data
and publish events to communicate state changes.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.4
"""

from .registration_service import RegistrationService
from .tournament_lifecycle_service import TournamentLifecycleService
from .match_service import MatchService
from .payment_service import PaymentOrchestrationService
from .result_submission_service import ResultSubmissionService
from .dispute_service import DisputeService
from .review_inbox_service import ReviewInboxService
from .result_verification_service import ResultVerificationService, ResultVerificationFailedError

__all__ = [
    "RegistrationService",
    "TournamentLifecycleService",
    "MatchService",
    "PaymentOrchestrationService",
    "ResultSubmissionService",
    "DisputeService",
    "ReviewInboxService",
    "ResultVerificationService",
    "ResultVerificationFailedError",
]
