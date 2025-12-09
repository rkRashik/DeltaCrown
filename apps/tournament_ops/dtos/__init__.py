"""
DTOs for TournamentOps cross-domain data exchange.

This package contains Data Transfer Objects used by service adapters to communicate
across domain boundaries without coupling to Django ORM models.
"""

from .game_identity import GamePlayerIdentityConfigDTO
from .team import TeamDTO
from .user import UserProfileDTO
from .common import ValidationResult
from .tournament import TournamentDTO
from .match import MatchDTO
from .registration import RegistrationDTO
from .eligibility import EligibilityResultDTO
from .payment import PaymentResultDTO
from .stage import StageDTO
from .smart_registration import (
    RegistrationQuestionDTO,
    RegistrationRuleDTO,
    RegistrationDraftDTO,
)
from .result_submission import (
    MatchResultSubmissionDTO,
    ResultVerificationResultDTO,
)
from .dispute import (
    DisputeDTO,
    DisputeEvidenceDTO,
    OpponentVerificationDTO,
)
from .review import (
    OrganizerReviewItemDTO,
    OrganizerInboxFilterDTO,
)
from .dispute_resolution import (
    DisputeResolutionDTO,
    RESOLUTION_TYPE_APPROVE_ORIGINAL,
    RESOLUTION_TYPE_APPROVE_DISPUTE,
    RESOLUTION_TYPE_CUSTOM_RESULT,
    RESOLUTION_TYPE_DISMISS_DISPUTE,
)
from .staffing import (
    StaffRoleDTO,
    TournamentStaffAssignmentDTO,
    MatchRefereeAssignmentDTO,
    StaffLoadDTO,
)
from .match_ops import (
    MatchOperationLogDTO,
    MatchModeratorNoteDTO,
    MatchOpsActionResultDTO,
    MatchOpsPermissionDTO,
    MatchTimelineEventDTO,
    MatchOpsDashboardItemDTO,
)
from .audit import (
    AuditLogDTO,
    AuditLogFilterDTO,
    AuditLogExportDTO,
)
from .help import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
    HelpBundleDTO,
)

__all__ = [
    "GamePlayerIdentityConfigDTO",
    "TeamDTO",
    "UserProfileDTO",
    "ValidationResult",
    "TournamentDTO",
    "MatchDTO",
    "RegistrationDTO",
    "EligibilityResultDTO",
    "PaymentResultDTO",
    "StageDTO",
    "RegistrationQuestionDTO",
    "RegistrationRuleDTO",
    "RegistrationDraftDTO",
    "MatchResultSubmissionDTO",
    "ResultVerificationResultDTO",
    "DisputeDTO",
    "DisputeEvidenceDTO",
    "OpponentVerificationDTO",
    "OrganizerReviewItemDTO",
    "OrganizerInboxFilterDTO",
    "DisputeResolutionDTO",
    "RESOLUTION_TYPE_APPROVE_ORIGINAL",
    "RESOLUTION_TYPE_APPROVE_DISPUTE",
    "RESOLUTION_TYPE_CUSTOM_RESULT",
    "RESOLUTION_TYPE_DISMISS_DISPUTE",
    "StaffRoleDTO",
    "TournamentStaffAssignmentDTO",
    "MatchRefereeAssignmentDTO",
    "StaffLoadDTO",
    "MatchOperationLogDTO",
    "MatchModeratorNoteDTO",
    "MatchOpsActionResultDTO",
    "MatchOpsPermissionDTO",
    "MatchTimelineEventDTO",
    "MatchOpsDashboardItemDTO",
    "AuditLogDTO",
    "AuditLogFilterDTO",
    "AuditLogExportDTO",
    "HelpContentDTO",
    "HelpOverlayDTO",
    "OnboardingStepDTO",
    "HelpBundleDTO",
]
