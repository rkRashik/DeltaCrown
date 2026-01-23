"""
User Profile Models

UP-M2: Event-sourced activity tracking with derived stats.
UP-M5: Audit trail for compliance and change tracking.
UP-PHASE6-C: Settings models for notifications and wallet.
"""

# Import new models from subdirectory
from apps.user_profile.models.activity import UserActivity, EventType
from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.models.game_passport_schema import GamePassportSchema
from apps.user_profile.models.settings import NotificationPreferences, WalletSettings
from apps.user_profile.models.showcase import ProfileShowcase  # UP-PHASE14C
from apps.user_profile.models.about import ProfileAboutItem  # UP-PHASE15
from apps.user_profile.models.media import StreamConfig, HighlightClip, PinnedHighlight  # P0 Media
from apps.user_profile.models.loadout import HardwareGear, GameConfig, HardwareLoadout  # P0 Loadout + Phase 4 Simple Loadout
from apps.user_profile.models.trophy_showcase import TrophyShowcaseConfig  # P0 Trophy Showcase
from apps.user_profile.models.endorsements import (  # P0 Endorsements
    SkillEndorsement,
    EndorsementOpportunity,
    SkillType,
)
from apps.user_profile.models.bounties import (  # P0 Bounties
    Bounty,
    BountyAcceptance,
    BountyProof,
    BountyDispute,
    BountyStatus,
    DisputeStatus,
)
from apps.user_profile.models.delete_otp import GamePassportDeleteOTP  # Phase 9A-27
from apps.user_profile.models.cooldown import GamePassportCooldown  # Phase 9A-27
from apps.user_profile.models.career import (  # Phase 2A Career & Matchmaking
    CareerProfile,
    MatchmakingPreferences,
    CAREER_STATUS_CHOICES,
    AVAILABILITY_CHOICES,
    CONTRACT_TYPE_CHOICES,
    RECRUITER_VISIBILITY_CHOICES,
)

# Public ID Counter (for unique user ID generation)
from apps.user_profile.services.public_id import PublicIDCounter

# Re-export existing models from models_main.py to maintain backward compatibility
from apps.user_profile.models_main import (
    UserProfile,
    PrivacySettings,
    SocialLink,
    UserBadge,
    Badge,
    KYCSubmission,
    GameProfile,
    GameProfileAlias,
    GameProfileConfig,
    Follow,  # UP-PHASE10: Export Follow model (used by fe_v2.py)
    FollowRequest,  # UP-PHASE6A: Private account follow requests
    REGION_CHOICES,
    KYC_STATUS_CHOICES,
    GENDER_CHOICES,
    # Functions needed for migrations
    user_avatar_path,
    user_banner_path,
    kyc_document_path,
)

__all__ = [
    # UP-M2 models
    'UserActivity',
    'EventType',
    'UserProfileStats',
    
    # UP-M5 models
    'UserAuditEvent',
    
    # GP-0/GP-1 models
    'GameProfile',
    'GameProfileAlias',
    'GameProfileConfig',
    'GamePassportSchema',
    
    # UP-PHASE6-C models
    'NotificationPreferences',
    'WalletSettings',
    
    # UP-PHASE14C models
    'ProfileShowcase',
    
    # UP-PHASE15 models
    'ProfileAboutItem',
    
    # P0 Media models
    'StreamConfig',
    'HighlightClip',
    'PinnedHighlight',
    
    # P0 Loadout models
    'HardwareGear',
    'GameConfig',
    'HardwareLoadout',  # Phase 4 simple loadout
    
    # P0 Trophy Showcase models
    'TrophyShowcaseConfig',
    
    # P0 Endorsement models
    'SkillEndorsement',
    'EndorsementOpportunity',
    'SkillType',
    
    # P0 Bounty models
    'Bounty',
    'BountyAcceptance',
    'BountyProof',
    'BountyDispute',
    'BountyStatus',
    'DisputeStatus',
    
    # Existing models
    'UserProfile',
    'PrivacySettings',
    'SocialLink',
    'UserBadge',
    'Badge',
    'KYCSubmission',
    'Follow',  # UP-PHASE10: Follow model
    'FollowRequest',  # UP-PHASE6A: Private account follow requests
    'REGION_CHOICES',
    'KYC_STATUS_CHOICES',
    'GENDER_CHOICES',
    # Functions
    'user_avatar_path',
    'user_banner_path',
    'kyc_document_path',
    
    # Public ID Counter
    'PublicIDCounter',
]



