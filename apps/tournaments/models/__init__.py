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
from .payment_config import (
    TournamentPaymentMethod,  # Detailed payment method configuration
)
from .staff import (
    TournamentStaffRole,  # Staff role definitions with permissions
    TournamentStaff,  # Staff assignments to tournaments
    StaffPermissionChecker,  # Utility for permission checking
)
from .announcement import (
    TournamentAnnouncement,  # Tournament announcements for participants
)
from .group import (
    Group,  # Group stage groups
    GroupStanding,  # Group standings tracking
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
from .template_rating import (
    TemplateRating,  # Template ratings and reviews
    RatingHelpful,  # Helpful vote tracking
)
from .webhooks import (
    FormWebhook,  # Webhook configurations
    WebhookDelivery,  # Webhook delivery tracking
)

__all__ = [
    'Game',
    'Tournament',
    'CustomField',
    'TournamentVersion',
    'TournamentTemplate',
    'Registration',
    'Payment',
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
    'TournamentLobby',
    'CheckIn',
    'LobbyAnnouncement',
    'RegistrationFormTemplate',
    'TournamentRegistrationForm',
    'FormResponse',
    'TemplateRating',
    'RatingHelpful',
    'FormWebhook',
    'WebhookDelivery',
]
