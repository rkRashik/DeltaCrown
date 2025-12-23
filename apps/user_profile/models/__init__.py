"""
User Profile Models

UP-M2: Event-sourced activity tracking with derived stats.
UP-M5: Audit trail for compliance and change tracking.
"""

# Import new models from subdirectory
from apps.user_profile.models.activity import UserActivity, EventType
from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.models.audit import UserAuditEvent

# Re-export existing models from models_main.py to maintain backward compatibility
from apps.user_profile.models_main import (
    UserProfile,
    PrivacySettings,
    UserBadge,
    Badge,
    VerificationRecord,
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
    'UserProfileStats',
    # Existing models
    'UserProfile',
    'PrivacySettings',
    'UserBadge',
    'Badge',
    'VerificationRecord',
    'REGION_CHOICES',
    'KYC_STATUS_CHOICES',
    'GENDER_CHOICES',
    # Functions
    'user_avatar_path',
    'user_banner_path',
    'kyc_document_path',
]



