"""
Tournament models package.

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 4.1)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 3, 4)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-003, ADR-004)

Exports all tournament-related models for easy importing.
"""

from .tournament import (
    Game,
    Tournament,
    CustomField,
    TournamentVersion,
)
from .template import (
    TournamentTemplate,  # Full implementation (Module 2.3)
)
from .registration import (
    Registration,  # Full implementation (Module 1.3)
    Payment,       # Full implementation (Module 1.3)
)
from .team_invitation import (
    TournamentTeamInvitation,  # Tournament organizer invites teams
)
from .payment_verification import (
    PaymentVerification,  # Payment proof submission (Module 3.x)
)
from .bracket import (
    Bracket,       # Full implementation (Module 1.5)
    BracketNode,   # Full implementation (Module 1.5)
)
from .match import (
    Match,    # Full implementation (Module 1.4)
    Dispute,  # Full implementation (Module 1.4)
)
from .security import (
    AuditLog,  # Full implementation (Module 2.4)
)
from .result import (
    TournamentResult,  # Module 5.1: Winner Determination
)
from .prize import (
    PrizeTransaction,  # Module 5.2: Prize Payouts & Reconciliation
)
from .certificate import (
    Certificate,  # Module 5.3: Certificates & Achievement Proofs
)
from .result_submission import (
    MatchResultSubmission,  # Phase 6, Epic 6.1: Match result submissions
    ResultVerificationLog,  # Phase 6, Epic 6.4: Result verification audit trail
)
from .dispute import (
    DisputeRecord,  # Phase 6, Epic 6.2: Dispute records
    DisputeEvidence,  # Phase 6, Epic 6.2: Evidence attached to disputes
)
from .payment_config import (
    TournamentPaymentMethod,  # Detailed payment method configuration
)
from .staff import (
    TournamentStaffRole,  # Staff role definitions with permissions
    TournamentStaff,  # Staff assignments to tournaments
    StaffPermissionChecker,  # Utility for permission checking
)
from .staffing import (
    StaffRole,  # Phase 7 Epic 7.3: Capability-based staff roles
    TournamentStaffAssignment,  # Phase 7 Epic 7.3: Per-tournament staff assignments
    MatchRefereeAssignment,  # Phase 7 Epic 7.3: Per-match referee assignments
)
from .match_ops import (
    MatchOperationLog,  # Phase 7 Epic 7.4: Match operations audit log
    MatchModeratorNote,  # Phase 7 Epic 7.4: Staff/referee notes on matches
)
from .announcement import (
    TournamentAnnouncement,  # Tournament announcements for participants
)
from .group import (
    Group,  # Group stage groups
    GroupStanding,  # Group standings tracking
    GroupStage,  # Epic 3.2: Group stage management
)
from .stage import (
    TournamentStage,  # Epic 3.4: Multi-stage tournament phases
)
from .lobby import (
    TournamentLobby,  # Tournament lobby/participant hub
    CheckIn,  # Check-in tracking
    LobbyAnnouncement,  # Lobby announcements
)
from .form_template import (
    RegistrationFormTemplate,  # Dynamic form templates
    TournamentRegistrationForm,  # Per-tournament form config
    FormResponse,  # Registration submissions
)
# NOTE: TemplateRating removed - deprecated marketplace feature
from .webhooks import (
    FormWebhook,  # Webhook configurations
    WebhookDelivery,  # Webhook delivery tracking
)
from .form_configuration import (
    TournamentFormConfiguration,  # Tournament registration form configuration
)
from .permission_request import (
    TeamRegistrationPermissionRequest,  # Team registration permission requests
)
from .bracket_edit_log import (
    BracketEditLog,  # Epic 3.3: Bracket editor audit log
)
from .smart_registration import (
    RegistrationQuestion,  # Phase 5: Dynamic registration questions
    RegistrationDraft,  # Phase 5: Draft persistence
    RegistrationAnswer,  # Phase 5: Question answers
    RegistrationRule,  # Phase 5: Auto-approval rules
)

__all__ = [
    'Game',
    'Tournament',
    'CustomField',
    'TournamentVersion',
    'TournamentTemplate',
    'Registration',
    'Payment',
    'TournamentTeamInvitation',
    'PaymentVerification',
    'Bracket',
    'BracketNode',
    'Match',
    'Dispute',
    'AuditLog',
    'TournamentResult',
    'PrizeTransaction',
    'Certificate',
    'TournamentPaymentMethod',
    'TournamentStaffRole',
    'TournamentStaff',
    'StaffPermissionChecker',
    'TournamentAnnouncement',
    'Group',
    'GroupStanding',
    'GroupStage',
    'TournamentStage',
    'TournamentLobby',
    'CheckIn',
    'LobbyAnnouncement',
    'RegistrationFormTemplate',
    'TournamentRegistrationForm',
    'FormResponse',
    'FormWebhook',
    'WebhookDelivery',
    'TournamentFormConfiguration',
    'TeamRegistrationPermissionRequest',
    'BracketEditLog',
    'RegistrationQuestion',
    'RegistrationDraft',
    'RegistrationAnswer',
    'RegistrationRule',
    'MatchResultSubmission',
    'ResultVerificationLog',
    'DisputeRecord',
    'DisputeEvidence',
    # Phase 7 Epic 7.3: Staff & Referee System
    'StaffRole',
    'TournamentStaffAssignment',
    'MatchRefereeAssignment',
    # Phase 7 Epic 7.4: Match Operations Command Center
    'MatchOperationLog',
    'MatchModeratorNote',
]
