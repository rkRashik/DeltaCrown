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
from .match_ops_service import MatchOpsService
from .audit_log_service import AuditLogService
from .help_service import HelpAndOnboardingService
from .user_stats_service import UserStatsService
from .team_stats_service import TeamStatsService
from .match_history_service import MatchHistoryService
from .tournament_ops_service import TournamentOpsService

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
    "MatchOpsService",
    "AuditLogService",
    "HelpAndOnboardingService",
    "UserStatsService",
    "TeamStatsService",
    "MatchHistoryService",
    "TournamentOpsService",
]
