"""
User Profile model exports.

In minimal SQLite test mode we only load the models needed for OAuth tests so
the app registry does not pull in unrelated cross-app model graphs.
"""

import os

from apps.user_profile.models.oauth import GameOAuthConnection
from apps.user_profile.models_main import (
    Badge,
    Follow,
    FollowRequest,
    GENDER_CHOICES,
    GameProfile,
    GameProfileAlias,
    GameProfileConfig,
    KYC_STATUS_CHOICES,
    KYCSubmission,
    PrivacySettings,
    REGION_CHOICES,
    SocialLink,
    UserBadge,
    UserProfile,
    kyc_document_path,
    user_avatar_path,
    user_banner_path,
)
from apps.user_profile.services.public_id import PublicIDCounter

_MINIMAL_TEST_APPS = os.environ.get("DELTA_MINIMAL_TEST_APPS") == "1"

__all__ = [
    'GameOAuthConnection',
    'UserProfile',
    'PrivacySettings',
    'SocialLink',
    'UserBadge',
    'Badge',
    'KYCSubmission',
    'GameProfile',
    'GameProfileAlias',
    'GameProfileConfig',
    'Follow',
    'FollowRequest',
    'REGION_CHOICES',
    'KYC_STATUS_CHOICES',
    'GENDER_CHOICES',
    'user_avatar_path',
    'user_banner_path',
    'kyc_document_path',
    'PublicIDCounter',
]

if not _MINIMAL_TEST_APPS:
    from apps.user_profile.models.activity import UserActivity, EventType
    from apps.user_profile.models.stats import UserProfileStats
    from apps.user_profile.models.audit import UserAuditEvent
    from apps.user_profile.models.game_passport_schema import GameChoiceConfig, GamePassportSchema  # noqa: F401 — alias kept for backward compat
    from apps.user_profile.models.settings import NotificationPreferences, WalletSettings
    from apps.user_profile.models.showcase import ProfileShowcase
    from apps.user_profile.models.about import ProfileAboutItem
    from apps.user_profile.models.media import StreamConfig, HighlightClip, PinnedHighlight
    from apps.user_profile.models.loadout import HardwareGear, GameConfig, HardwareLoadout
    from apps.user_profile.models.trophy_showcase import TrophyShowcaseConfig
    from apps.user_profile.models.endorsements import SkillEndorsement, EndorsementOpportunity, SkillType
    from apps.user_profile.models.bounties import (
        Bounty,
        BountyAcceptance,
        BountyProof,
        BountyDispute,
        BountyStatus,
        BountyType,
        DisputeStatus,
    )
    from apps.user_profile.models.delete_otp import GamePassportDeleteOTP
    from apps.user_profile.models.cooldown import GamePassportCooldown
    from apps.user_profile.models.career import (
        CareerProfile,
        MatchmakingPreferences,
        CAREER_STATUS_CHOICES,
        AVAILABILITY_CHOICES,
        CONTRACT_TYPE_CHOICES,
        RECRUITER_VISIBILITY_CHOICES,
    )

    __all__.extend([
        'UserActivity',
        'EventType',
        'UserProfileStats',
        'UserAuditEvent',
        'GameChoiceConfig',
        'GamePassportSchema',  # backward-compat alias
        'NotificationPreferences',
        'WalletSettings',
        'ProfileShowcase',
        'ProfileAboutItem',
        'StreamConfig',
        'HighlightClip',
        'PinnedHighlight',
        'HardwareGear',
        'GameConfig',
        'HardwareLoadout',
        'TrophyShowcaseConfig',
        'SkillEndorsement',
        'EndorsementOpportunity',
        'SkillType',
        'Bounty',
        'BountyAcceptance',
        'BountyProof',
        'BountyDispute',
        'BountyStatus',
        'BountyType',
        'DisputeStatus',
        'GamePassportDeleteOTP',
        'GamePassportCooldown',
        'CareerProfile',
        'MatchmakingPreferences',
        'CAREER_STATUS_CHOICES',
        'AVAILABILITY_CHOICES',
        'CONTRACT_TYPE_CHOICES',
        'RECRUITER_VISIBILITY_CHOICES',
    ])



