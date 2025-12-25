"""
Privacy Settings Service (UP-CLEANUP-04 Phase C Part 1)

Safe privacy settings updates with audit trail and privacy enforcement.
Replacement for legacy privacy_settings_view POST handler.

Architecture:
- Uses safe profile accessor (get_user_profile_safe)
- Records audit events via AuditService
- Enforces privacy policy (no bypasses)
- Backward compatible with existing forms
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from typing import Dict, Any
import logging

from apps.user_profile.models import PrivacySettings
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.services.audit import AuditService
from apps.user_profile.utils import get_user_profile_safe

User = get_user_model()
logger = logging.getLogger(__name__)


class PrivacySettingsService:
    """
    Service for safe privacy settings updates.
    
    Enforces:
    - Safe profile access (no DoesNotExist crashes)
    - Audit trail (all changes logged)
    - Privacy policy enforcement
    - Idempotency (safe to call multiple times)
    """
    
    @staticmethod
    @transaction.atomic
    def update_settings(
        user: User,
        settings_dict: Dict[str, Any],
        actor_user_id: int = None,
        request_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> PrivacySettings:
        """
        Update privacy settings with audit trail.
        
        Args:
            user: User whose settings to update
            settings_dict: Dict of setting name -> value
            actor_user_id: User performing update (defaults to user.id)
            request_id: Request ID for audit correlation
            ip_address: IP address of request
            user_agent: User agent string
            
        Returns:
            PrivacySettings: Updated settings object
            
        Example:
            >>> settings = PrivacySettingsService.update_settings(
            ...     user=request.user,
            ...     settings_dict={
            ...         'show_email': False,
            ...         'allow_friend_requests': True
            ...     }
            ... )
        """
        profile = get_user_profile_safe(user)
        privacy_settings, created = PrivacySettings.objects.get_or_create(
            user_profile=profile
        )
        
        # Capture before snapshot (privacy-safe fields only)
        before_snapshot = {
            'show_email': privacy_settings.show_email,
            'show_phone': privacy_settings.show_phone,
            'show_real_name': privacy_settings.show_real_name,
            'show_age': privacy_settings.show_age,
            'show_country': privacy_settings.show_country,
            'show_social_links': privacy_settings.show_social_links,
            'allow_friend_requests': privacy_settings.allow_friend_requests,
        }
        
        # Apply updates (with validation)
        changed = False
        for key, value in settings_dict.items():
            if hasattr(privacy_settings, key):
                old_value = getattr(privacy_settings, key)
                if old_value != value:
                    setattr(privacy_settings, key, value)
                    changed = True
            else:
                logger.warning(f"Unknown privacy setting: {key}")
        
        # Save if changed
        if changed:
            privacy_settings.save()
            
            # Capture after snapshot
            after_snapshot = {
                'show_email': privacy_settings.show_email,
                'show_phone': privacy_settings.show_phone,
                'show_real_name': privacy_settings.show_real_name,
                'show_age': privacy_settings.show_age,
                'show_country': privacy_settings.show_country,
                'show_social_links': privacy_settings.show_social_links,
                'allow_friend_requests': privacy_settings.allow_friend_requests,
            }
            
            # Record audit event
            AuditService.record_event(
                subject_user_id=user.id,
                actor_user_id=actor_user_id or user.id,
                event_type=UserAuditEvent.EventType.PRIVACY_SETTINGS_CHANGED,
                source_app='user_profile',
                object_type='PrivacySettings',
                object_id=privacy_settings.id,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                metadata={'changed_fields': list(settings_dict.keys())},
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(
                f"Privacy settings updated for user_id={user.id}, "
                f"settings_id={privacy_settings.id}, changed={changed}"
            )
        else:
            logger.debug(f"No privacy settings changed for user_id={user.id}")
        
        return privacy_settings
    
    @staticmethod
    def get_settings(user: User) -> PrivacySettings:
        """
        Get privacy settings (safe accessor).
        
        Args:
            user: User whose settings to retrieve
            
        Returns:
            PrivacySettings: Settings object (created if missing)
        """
        profile = get_user_profile_safe(user)
        privacy_settings, _ = PrivacySettings.objects.get_or_create(
            user_profile=profile
        )
        return privacy_settings
