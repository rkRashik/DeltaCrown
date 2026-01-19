"""
UP PHASE 8: Settings Completion Service

Calculate profile completion percentage and provide actionable checklist.
Used by Profile Status widget in left sidebar (owner-only).
"""
from django.contrib.auth import get_user_model
from typing import Dict, List
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SettingsCompletionService:
    """
    Service to calculate profile completion and generate improvement checklist.
    
    Checklist Items:
    - Avatar (profile picture)
    - Bio (about me text)
    - Social Links (at least one platform)
    - Game Passports (at least one game identity)
    - Hardware Gear (at least one setup item)
    - Email Verification
    - Identity Verification (KYC)
    - Stream Settings (optional, bonus points)
    """
    
    @staticmethod
    def calculate(user_profile) -> Dict:
        """
        Calculate profile completion for a user.
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            dict: {
                'percentage': 85,  # 0-100
                'completed_count': 6,
                'total_count': 8,
                'checklist': [
                    {
                        'key': 'avatar',
                        'label': 'Profile Picture',
                        'completed': True,
                        'url': '/me/settings/#avatar',
                        'priority': 'high'
                    },
                    ...
                ],
                'missing_items': ['hardware', 'kyc'],
                'next_action': {
                    'label': 'Add Hardware Gear',
                    'url': '/me/settings/#hardware',
                    'icon': 'fa-gamepad'
                }
            }
        """
        if not user_profile:
            return {
                'percentage': 0,
                'completed_count': 0,
                'total_count': 8,
                'checklist': [],
                'missing_items': [],
                'next_action': None
            }
        
        user = user_profile.user
        checklist_items = []
        
        # 1. Avatar (HIGH PRIORITY)
        has_avatar = bool(user_profile.avatar)
        checklist_items.append({
            'key': 'avatar',
            'label': 'Profile Picture',
            'completed': has_avatar,
            'url': '/me/settings/#avatar',
            'priority': 'high',
            'icon': 'fa-user-circle'
        })
        
        # 2. Bio (HIGH PRIORITY)
        has_bio = bool(user_profile.bio and len(user_profile.bio.strip()) > 10)
        checklist_items.append({
            'key': 'bio',
            'label': 'Bio / About Me',
            'completed': has_bio,
            'url': '/me/settings/#bio',
            'priority': 'high',
            'icon': 'fa-file-lines'
        })
        
        # 3. Social Links (MEDIUM PRIORITY)
        try:
            from apps.user_profile.models import SocialLink
            has_social_links = SocialLink.objects.filter(user=user).exists()
        except:
            has_social_links = False
        
        checklist_items.append({
            'key': 'social_links',
            'label': 'Social Links',
            'completed': has_social_links,
            'url': '/me/settings/#social',
            'priority': 'medium',
            'icon': 'fa-link'
        })
        
        # 4. Game Passports (HIGH PRIORITY)
        try:
            from apps.user_profile.models_main import GameProfile
            has_game_passports = GameProfile.objects.filter(user=user).exists()
        except:
            has_game_passports = False
        
        checklist_items.append({
            'key': 'game_passports',
            'label': 'Game Passports',
            'completed': has_game_passports,
            'url': '/me/settings/#game-passports',
            'priority': 'high',
            'icon': 'fa-gamepad'
        })
        
        # 5. Hardware Gear (MEDIUM PRIORITY)
        try:
            from apps.user_profile.models_main import HardwareGear
            has_hardware = HardwareGear.objects.filter(user=user).exists()
        except:
            has_hardware = False
        
        checklist_items.append({
            'key': 'hardware',
            'label': 'Hardware Gear',
            'completed': has_hardware,
            'url': '/me/settings/#hardware',
            'priority': 'medium',
            'icon': 'fa-keyboard'
        })
        
        # 6. Email Verification (HIGH PRIORITY)
        has_verified_email = user.email and getattr(user, 'is_email_verified', False)
        checklist_items.append({
            'key': 'email_verified',
            'label': 'Email Verification',
            'completed': has_verified_email,
            'url': '/me/settings/#email',
            'priority': 'high',
            'icon': 'fa-envelope-circle-check'
        })
        
        # 7. KYC Verification (LOW PRIORITY - Optional)
        has_kyc = user_profile.kyc_status == 'verified'
        checklist_items.append({
            'key': 'kyc',
            'label': 'Identity Verification',
            'completed': has_kyc,
            'url': '/me/settings/#kyc',
            'priority': 'low',
            'icon': 'fa-id-card'
        })
        
        # 8. Stream Settings (LOW PRIORITY - Optional Bonus)
        try:
            from apps.user_profile.models import SocialLink
            has_stream_settings = SocialLink.objects.filter(
                user=user,
                platform__in=['twitch', 'youtube', 'kick', 'facebook_gaming']
            ).exists()
        except:
            has_stream_settings = False
        
        checklist_items.append({
            'key': 'stream_settings',
            'label': 'Stream Settings',
            'completed': has_stream_settings,
            'url': '/me/settings/#stream',
            'priority': 'low',
            'icon': 'fa-video'
        })
        
        # Calculate completion percentage
        completed_items = [item for item in checklist_items if item['completed']]
        completed_count = len(completed_items)
        total_count = len(checklist_items)
        percentage = int((completed_count / total_count) * 100)
        
        # Get missing items (prioritize high priority)
        missing_items = [
            item for item in checklist_items 
            if not item['completed']
        ]
        missing_items.sort(key=lambda x: {
            'high': 0,
            'medium': 1,
            'low': 2
        }[x['priority']])
        
        # Get next recommended action (first missing high priority item)
        next_action = missing_items[0] if missing_items else None
        
        return {
            'percentage': percentage,
            'completed_count': completed_count,
            'total_count': total_count,
            'checklist': checklist_items,
            'missing_items': [item['key'] for item in missing_items],
            'next_action': {
                'label': next_action['label'],
                'url': next_action['url'],
                'icon': next_action['icon']
            } if next_action else None
        }
    
    @staticmethod
    def get_top_missing(user_profile, limit: int = 3) -> List[Dict]:
        """
        Get top N missing items for quick display.
        
        Args:
            user_profile: UserProfile instance
            limit: Number of items to return
            
        Returns:
            list: Top missing items sorted by priority
        """
        completion_data = SettingsCompletionService.calculate(user_profile)
        missing_items = [
            item for item in completion_data['checklist']
            if not item['completed']
        ]
        missing_items.sort(key=lambda x: {
            'high': 0,
            'medium': 1,
            'low': 2
        }[x['priority']])
        
        return missing_items[:limit]
