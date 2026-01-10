# apps/user_profile/views/settings_debug.py
"""
Phase 4B.1: Debug endpoint for verifying settings persistence
Staff-only endpoint for round-trip testing of all settings models.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.user_profile.models import UserProfile, PrivacySettings, CareerProfile, HardwareLoadout
import logging

logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def settings_debug_dump(request):
    """
    GET /me/settings/debug-dump/ - Staff-only debug endpoint
    
    Returns complete settings state for current user across all models:
    - UserProfile fields (including About fields)
    - PrivacySettings (all toggles)
    - CareerProfile (recruitment settings)
    - HardwareLoadout (gear brands)
    
    Security: Requires staff permissions
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        # Get related models (create if missing for debugging)
        privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        career_profile, _ = CareerProfile.objects.get_or_create(user_profile=profile)
        hardware_loadout, _ = HardwareLoadout.objects.get_or_create(user_profile=profile)
        
        # Build comprehensive dump
        data = {
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'is_staff': request.user.is_staff,
            },
            'user_profile': {
                # Identity
                'display_name': profile.display_name,
                'gender': profile.gender,
                'bio': profile.bio,
                'city': profile.city,
                'country': profile.country,
                'pronouns': profile.pronouns,
                
                # Connections
                'phone': profile.phone,
                'whatsapp': profile.whatsapp,
                'secondary_email': profile.secondary_email,
                'preferred_contact_method': profile.preferred_contact_method,
                'emergency_contact_name': profile.emergency_contact_name,
                'emergency_contact_phone': profile.emergency_contact_phone,
                'emergency_contact_relation': profile.emergency_contact_relation,
                
                # Social
                'discord_id': profile.discord_id,
                'youtube_link': profile.youtube_link,
                'twitch_link': profile.twitch_link,
                'twitter': profile.twitter,
                'facebook': profile.facebook,
                'instagram': profile.instagram,
                'tiktok': profile.tiktok,
                
                # Platform
                'preferred_language': profile.preferred_language,
                'timezone_pref': profile.timezone_pref,
                'time_format': profile.time_format,
                
                # Phase 4B: About fields
                'device_platform': profile.device_platform,
                'play_style': profile.play_style,
                'lan_availability': profile.lan_availability,
                'main_role': profile.main_role,
                'secondary_role': profile.secondary_role,
                'communication_languages': profile.communication_languages,
                'active_hours': profile.active_hours,
            },
            'privacy_settings': {
                # Core privacy
                'visibility_preset': privacy_settings.visibility_preset,
                'is_private_account': privacy_settings.is_private_account,
                
                # Personal info visibility
                'show_real_name': privacy_settings.show_real_name,
                'show_phone': privacy_settings.show_phone,
                'show_email': privacy_settings.show_email,
                'show_age': privacy_settings.show_age,
                'show_gender': privacy_settings.show_gender,
                'show_country': privacy_settings.show_country,
                'show_address': privacy_settings.show_address,
                
                # Gaming visibility
                'show_game_ids': privacy_settings.show_game_ids,
                'show_match_history': privacy_settings.show_match_history,
                'show_teams': privacy_settings.show_teams,
                'show_achievements': privacy_settings.show_achievements,
                'show_activity_feed': privacy_settings.show_activity_feed,
                'show_tournaments': privacy_settings.show_tournaments,
                
                # Economy visibility
                'show_inventory_value': privacy_settings.show_inventory_value,
                'show_level_xp': privacy_settings.show_level_xp,
                'inventory_visibility': privacy_settings.inventory_visibility,
                
                # Social visibility
                'show_social_links': privacy_settings.show_social_links,
                'show_followers_count': privacy_settings.show_followers_count,
                'show_following_count': privacy_settings.show_following_count,
                'show_followers_list': privacy_settings.show_followers_list,
                'show_following_list': privacy_settings.show_following_list,
                
                # Interaction permissions
                'allow_team_invites': privacy_settings.allow_team_invites,
                'allow_friend_requests': privacy_settings.allow_friend_requests,
                'allow_direct_messages': privacy_settings.allow_direct_messages,
                
                # Phase 4B: About section privacy
                'show_pronouns': privacy_settings.show_pronouns,
                'show_nationality': privacy_settings.show_nationality,
                'show_device_platform': privacy_settings.show_device_platform,
                'show_play_style': privacy_settings.show_play_style,
                'show_roles': privacy_settings.show_roles,
                'show_active_hours': privacy_settings.show_active_hours,
                'show_preferred_contact': privacy_settings.show_preferred_contact,
            },
            'career_profile': {
                'career_status': career_profile.career_status,
                'lft_enabled': career_profile.lft_enabled,
                'primary_roles': career_profile.primary_roles,
                'secondary_roles': career_profile.secondary_roles,
                'preferred_region': career_profile.preferred_region,
                'availability': career_profile.availability,
                'salary_expectation_min': career_profile.salary_expectation_min,
                'contract_type': career_profile.contract_type,
                'recruiter_visibility': career_profile.recruiter_visibility,
                'allow_direct_contracts': career_profile.allow_direct_contracts,
            },
            'hardware_loadout': {
                'mouse_brand': hardware_loadout.mouse_brand,
                'keyboard_brand': hardware_loadout.keyboard_brand,
                'headset_brand': hardware_loadout.headset_brand,
                'monitor_brand': hardware_loadout.monitor_brand,
                'is_complete': hardware_loadout.is_complete,
            },
            'meta': {
                'timestamp': str(timezone.now()),
                'phase': '4B.1',
                'models_checked': ['UserProfile', 'PrivacySettings', 'CareerProfile', 'HardwareLoadout'],
            }
        }
        
        return JsonResponse(data, json_dumps_params={'indent': 2})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'error': 'User profile not found',
            'user': request.user.username
        }, status=404)
    except Exception as e:
        logger.error(f"Debug dump error for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Server error',
            'details': str(e)
        }, status=500)
