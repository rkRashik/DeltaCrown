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

# Re-export existing models from models_main.py to maintain backward compatibility
from apps.user_profile.models_main import (
    UserProfile,
    PrivacySettings,
    SocialLink,
    UserBadge,
    Badge,
    VerificationRecord,
    GameProfile,
    GameProfileAlias,
    GameProfileConfig,
    Follow,  # UP-PHASE10: Export Follow model (used by fe_v2.py)
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
    
    # Existing models
    'UserProfile',
    'PrivacySettings',
    'SocialLink',
    'UserBadge',
    'Badge',
    'VerificationRecord',
    'Follow',  # UP-PHASE10: Follow model
    'REGION_CHOICES',
    'KYC_STATUS_CHOICES',
    'GENDER_CHOICES',
    # Functions
    'user_avatar_path',
    'user_banner_path',
    'kyc_document_path',
]



