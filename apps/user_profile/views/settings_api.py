"""
Settings API Endpoints
Handles avatar/banner uploads, social links, and profile updates.
"""
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def upload_media(request):
    """
    Upload avatar or banner image.
    
    Route: POST /me/settings/media/
    
    Fields:
    - media_type: 'avatar' or 'banner'
    - file: Image file (JPEG, PNG, WebP)
    
    Validation:
    - Avatar: max 5MB, min 100x100px, square recommended
    - Banner: max 10MB, min 1200x300px, 4:1 ratio recommended
    
    Returns:
        JSON: {success: true, url: '/media/...', preview_url: '/media/...'}
    """
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    media_type = request.POST.get('media_type')
    
    if media_type not in ['avatar', 'banner']:
        return JsonResponse({'success': False, 'error': 'Invalid media_type'}, status=400)
    
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    # Validate file size
    max_size = 10 * 1024 * 1024 if media_type == 'banner' else 5 * 1024 * 1024
    if file.size > max_size:
        max_mb = 10 if media_type == 'banner' else 5
        return JsonResponse({'success': False, 'error': f'File must be less than {max_mb}MB'}, status=400)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        return JsonResponse({'success': False, 'error': 'File must be JPEG, PNG, or WebP'}, status=400)
    
    # Validate dimensions
    try:
        image = Image.open(file)
        width, height = image.size
        
        if media_type == 'avatar':
            if width < 100 or height < 100:
                return JsonResponse({'success': False, 'error': 'Avatar must be at least 100x100 pixels'}, status=400)
        else:  # banner
            if width < 1200 or height < 300:
                return JsonResponse({'success': False, 'error': 'Banner must be at least 1200x300 pixels'}, status=400)
        
        # Reset file pointer after PIL read
        file.seek(0)
    except Exception as e:
        logger.error(f"Error validating image: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid image file'}, status=400)
    
    # Save to profile
    try:
        if media_type == 'avatar':
            # Delete old avatar if exists
            if profile.avatar:
                try:
                    default_storage.delete(profile.avatar.name)
                except Exception:
                    pass
            profile.avatar = file
        else:
            # Delete old banner if exists
            if profile.banner:
                try:
                    default_storage.delete(profile.banner.name)
                except Exception:
                    pass
            profile.banner = file
        
        profile.save()
        
        # Get URL
        url = profile.avatar.url if media_type == 'avatar' else profile.banner.url
        
        # Return both generic 'url' and explicit keys expected by frontend/tests
        resp = {
            'success': True,
            'url': url,
            'preview_url': url,
            'message': f'{media_type.capitalize()} uploaded successfully'
        }
        if media_type == 'avatar':
            resp['avatar_url'] = url
        else:
            resp['banner_url'] = url

        return JsonResponse(resp)
    
    except Exception as e:
        logger.error(f"Error saving {media_type}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Failed to save file'}, status=500)


@login_required
@require_http_methods(["POST"])
def remove_media_api(request):
    """
    Remove avatar or banner.
    
    Route: POST /me/settings/media/remove/
    
    POST params:
    - media_type: 'avatar' or 'banner'
    
    Returns:
        JSON response with success status
    """
    from apps.user_profile.utils import get_user_profile_safe
    from django.core.files.storage import default_storage
    
    profile = get_user_profile_safe(request.user)
    media_type = request.POST.get('media_type', 'avatar')
    
    if media_type not in ['avatar', 'banner']:
        return JsonResponse({'success': False, 'error': 'Invalid media type'}, status=400)
    
    try:
        # Delete file from storage
        if media_type == 'avatar' and profile.avatar:
            try:
                default_storage.delete(profile.avatar.name)
            except Exception:
                pass
            profile.avatar = None
        elif media_type == 'banner' and profile.banner:
            try:
                default_storage.delete(profile.banner.name)
            except Exception:
                pass
            profile.banner = None
        
        profile.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{media_type.capitalize()} removed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error removing {media_type}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Failed to remove file'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_social_links(request):
    """
    Get current social links for the authenticated user.
    
    Route: GET /api/social-links/
    
    Returns:
        JSON: {
            success: true,
            links: {
                twitch: "https://twitch.tv/username",
                youtube: "https://youtube.com/@username",
                ...
            }
        }
    """
    from apps.user_profile.models import SocialLink
    
    try:
        social_links = SocialLink.objects.filter(user=request.user)
        
        links = {}
        for link in social_links:
            links[link.platform] = link.url
        
        return JsonResponse({
            'success': True,
            'links': links
        })
    
    except Exception as e:
        logger.error(f"Error loading social links: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_social_links_api(request):
    """
    Update social links (API version with JSON response).
    
    Route: POST /api/social-links/update/
    
    Body (JSON):
    {
        "links": [
            {"platform": "twitch", "url": "https://twitch.tv/username"},
            {"platform": "youtube", "url": "https://youtube.com/@username"}
        ]
    }
    
    Returns:
        JSON: {success: true, links: [...]}
    """
    import json
    from apps.user_profile.models import SocialLink
    
    try:
        data = json.loads(request.body)
        links_data = data.get('links', [])
        
        # Delete existing links for this user
        SocialLink.objects.filter(user=request.user).delete()
        
        # Create new links
        created_links = []
        for link_data in links_data:
            platform = link_data.get('platform')
            url = link_data.get('url', '').strip()
            
            if not url:
                continue
            
            # Validate platform
            valid_platforms = [choice[0] for choice in SocialLink.PLATFORM_CHOICES]
            if platform not in valid_platforms:
                continue
            
            # Create link
            link = SocialLink.objects.create(
                user=request.user,
                platform=platform,
                url=url,
                handle=link_data.get('handle', '')
            )
            
            # Validate
            try:
                link.full_clean()
                created_links.append({
                    'platform': link.platform,
                    'platform_display': link.get_platform_display(),
                    'url': link.url,
                    'handle': link.handle
                })
            except Exception as e:
                link.delete()
                logger.warning(f"Invalid social link: {e}")
        
        return JsonResponse({
            'success': True,
            'links': created_links,
            'message': 'Social links updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating social links: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_privacy_settings(request):
    """
    Update privacy settings.
    
    Route: POST /me/settings/privacy/save/
    
    Body (JSON):
    {
        "visibility_preset": "PUBLIC",
        "show_real_name": false,
        "show_email": false,
        ...
    }
    
    Returns:
        JSON: {success: true, message: '...'}
    """
    import json
    from apps.user_profile.utils import get_user_profile_safe
    from apps.user_profile.models import PrivacySettings
    
    profile = get_user_profile_safe(request.user)
    
    try:
        # Parse JSON body
        data = json.loads(request.body)
        
        # Get or create privacy settings (linked to UserProfile, not User)
        privacy, created = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        # Update preset if provided
        if 'visibility_preset' in data:
            preset = data['visibility_preset']
            if preset in ['PUBLIC', 'PROTECTED', 'PRIVATE']:
                privacy.visibility_preset = preset
        
        # Update all toggles (including Phase 6A private account)
        boolean_fields = [
            'show_real_name', 'show_email', 'show_phone', 'show_age', 'show_gender',
            'show_country', 'show_address', 'show_game_ids', 'show_match_history',
            'show_teams', 'show_achievements', 'show_activity_feed', 'show_tournaments',
            'show_social_links', 'show_inventory_value', 'show_level_xp',
            'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages',
            'show_followers_count', 'show_following_count', 'show_followers_list', 'show_following_list',
            'is_private_account'  # Phase 6A: Private Account toggle
        ]
        
        for field in boolean_fields:
            if field in data:
                setattr(privacy, field, bool(data[field]))
        
        # UP-PHASE2B: Update inventory_visibility choice field
        if 'inventory_visibility' in data:
            value = data['inventory_visibility']
            if value in ['PUBLIC', 'FRIENDS', 'PRIVATE']:
                privacy.inventory_visibility = value
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Invalid inventory_visibility value: '{value}'. Must be one of: PUBLIC, FRIENDS, PRIVATE"
                }, status=400)
        
        privacy.save()
        
        logger.info(f"Privacy settings updated for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Privacy settings saved successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating privacy settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_privacy_settings(request):
    """
    Get current privacy settings for the authenticated user.
    
    Route: GET /me/settings/privacy/
    
    Returns:
        JSON: {
            success: true,
            settings: {
                visibility_preset: "PUBLIC",
                show_real_name: false,
                show_email: false,
                ...
            }
        }
    """
    from apps.user_profile.utils import get_user_profile_safe
    from apps.user_profile.models import PrivacySettings
    
    profile = get_user_profile_safe(request.user)
    
    try:
        privacy, created = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        settings = {
            'visibility_preset': privacy.visibility_preset,
            'show_real_name': privacy.show_real_name,
            'show_email': privacy.show_email,
            'show_phone': privacy.show_phone,
            'show_age': privacy.show_age,
            'show_gender': privacy.show_gender,
            'show_country': privacy.show_country,
            'show_address': privacy.show_address,
            'show_game_ids': privacy.show_game_ids,
            'show_match_history': privacy.show_match_history,
            'show_teams': privacy.show_teams,
            'show_achievements': privacy.show_achievements,
            'show_activity_feed': privacy.show_activity_feed,
            'show_tournaments': privacy.show_tournaments,
            'show_social_links': privacy.show_social_links,
            'inventory_visibility': privacy.inventory_visibility,  # Phase 7C
            'show_inventory_value': privacy.show_inventory_value,
            'show_level_xp': privacy.show_level_xp,
            'show_following_list': privacy.show_following_list,  # Phase 7C
            'allow_team_invites': privacy.allow_team_invites,
            'allow_friend_requests': privacy.allow_friend_requests,
            'allow_direct_messages': privacy.allow_direct_messages,
            'is_private_account': privacy.is_private_account,  # Phase 6A: Private Account
        }
        
        return JsonResponse({
            'success': True,
            'privacy': settings  # Changed from 'settings' to 'privacy' for Phase 7C test compatibility
        })
    
    except Exception as e:
        logger.error(f"Error loading privacy settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_profile_data(request):
    """
    Get current profile data for the authenticated user.
    
    Route: GET /api/profile/data/
    
    Returns:
        JSON: {
            success: true,
            profile: {
                display_name: "...",
                bio: "...",
                country: "...",
                ...
            }
        }
    """
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        data = {
            'display_name': profile.display_name,
            'bio': profile.bio,
            'country': profile.country,
            'city': profile.city,
            'postal_code': profile.postal_code,
            'address': profile.address,
            'phone': profile.phone,
            'real_full_name': profile.real_full_name,
            'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else '',
            'nationality': profile.nationality,
            'gender': profile.gender,
            'emergency_contact_name': profile.emergency_contact_name,
            'emergency_contact_phone': profile.emergency_contact_phone,
            'emergency_contact_relation': profile.emergency_contact_relation,
            'kyc_status': profile.kyc_status,
        }
        
        return JsonResponse({
            'success': True,
            'profile': data
        })
    
    except Exception as e:
        logger.error(f"Error loading profile data: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_platform_settings(request):
    """
    Update platform settings (language, timezone, time format, notifications).
    
    Route: POST /me/settings/platform/
    
    Body (JSON):
    {
        "language": "bn",
        "timezone": "Asia/Dhaka",
        "time_format": "12",
        "email_tournament_updates": true,
        "email_team_invites": true,
        "push_match_reminders": true,
        ...
    }
    
    Returns:
        JSON: {success: true, message: 'Platform settings updated successfully'}
    """
    import json
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        data = json.loads(request.body)
        
        # Get or initialize system_settings
        system_settings = profile.system_settings or {}
        
        # Update language
        if 'language' in data:
            language = data['language']
            valid_languages = ['en', 'bn', 'es', 'fr', 'de', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi']
            if language in valid_languages:
                system_settings['language'] = language
        
        # Update timezone
        if 'timezone' in data:
            timezone = data['timezone']
            # Basic validation (could be more comprehensive)
            if timezone and len(timezone) < 100:
                system_settings['timezone'] = timezone
        
        # Update time format
        if 'time_format' in data:
            time_format = data['time_format']
            if time_format in ['12', '24']:
                system_settings['time_format'] = time_format
        
        # Update notification preferences
        notification_fields = [
            'email_tournament_updates',
            'email_team_invites',
            'email_announcements',
            'email_marketing',
            'push_match_reminders',
            'push_messages',
            'push_friend_requests'
        ]
        
        notifications = system_settings.get('notifications', {})
        for field in notification_fields:
            if field in data:
                notifications[field] = bool(data[field])
        system_settings['notifications'] = notifications
        
        # Save to profile
        profile.system_settings = system_settings
        profile.save()
        
        logger.info(f"Platform settings updated for user {request.user.username}: {system_settings}")
        
        return JsonResponse({
            'success': True,
            'message': 'Platform settings updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating platform settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_platform_settings(request):
    """
    Get current platform settings for the authenticated user.
    
    Route: GET /me/settings/platform/
    
    Returns:
        JSON: {
            success: true,
            settings: {
                language: "en",
                timezone: "UTC",
                time_format: "12",
                notifications: {...}
            }
        }
    """
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        system_settings = profile.system_settings or {}
        
        # Default settings
        settings = {
            'language': system_settings.get('language', 'en'),
            'timezone': system_settings.get('timezone', 'UTC'),
            'time_format': system_settings.get('time_format', '12'),
            'notifications': system_settings.get('notifications', {
                'email_tournament_updates': True,
                'email_team_invites': True,
                'email_announcements': False,
                'email_marketing': False,
                'push_match_reminders': True,
                'push_messages': True,
                'push_friend_requests': False
            })
        }
        
        return JsonResponse({
            'success': True,
            'settings': settings
        })
    
    except Exception as e:
        logger.error(f"Error loading platform settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


# ============================================
# UP-PHASE6-C: Settings Redesign API Endpoints
# ============================================

@login_required
@require_http_methods(["POST"])
def update_notification_preferences(request):
    """
    Update notification preferences for the authenticated user.
    
    Route: POST /me/settings/notifications/
    
    Body (JSON):
    {
        "email_tournament_reminders": true,
        "email_match_results": true,
        "email_team_invites": true,
        "email_achievements": false,
        "email_platform_updates": true,
        "notify_tournament_start": true,
        "notify_team_messages": true,
        "notify_follows": true,
        "notify_achievements": true
    }
    
    Returns:
        JSON: {success: true, message: 'Notification preferences updated successfully'}
    """
    import json
    from apps.user_profile.models import NotificationPreferences
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        data = json.loads(request.body)
        
        # Get or create notification preferences
        prefs, created = NotificationPreferences.objects.get_or_create(user_profile=profile)
        
        # Update fields if present in request
        email_fields = [
            'email_tournament_reminders', 'email_match_results', 'email_team_invites',
            'email_achievements', 'email_platform_updates'
        ]
        platform_fields = [
            'notify_tournament_start', 'notify_team_messages', 'notify_follows', 'notify_achievements'
        ]
        
        for field in email_fields + platform_fields:
            if field in data:
                setattr(prefs, field, bool(data[field]))
        
        prefs.save()
        
        logger.info(f"Notification preferences updated for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notification preferences updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_notification_preferences(request):
    """
    Get current notification preferences for the authenticated user.
    
    Route: GET /me/settings/notifications/
    
    Returns:
        JSON: {
            success: true,
            preferences: {
                email_tournament_reminders: true,
                email_match_results: true,
                ...
            }
        }
    """
    from apps.user_profile.models import NotificationPreferences
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        # Get or create with defaults
        prefs, created = NotificationPreferences.objects.get_or_create(user_profile=profile)
        
        preferences = {
            'email_tournament_reminders': prefs.email_tournament_reminders,
            'email_match_results': prefs.email_match_results,
            'email_team_invites': prefs.email_team_invites,
            'email_achievements': prefs.email_achievements,
            'email_platform_updates': prefs.email_platform_updates,
            'notify_tournament_start': prefs.notify_tournament_start,
            'notify_team_messages': prefs.notify_team_messages,
            'notify_follows': prefs.notify_follows,
            'notify_achievements': prefs.notify_achievements,
        }
        
        return JsonResponse({
            'success': True,
            'preferences': preferences
        })
    
    except Exception as e:
        logger.error(f"Error loading notification preferences: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_platform_preferences(request):
    """
    Update platform preferences (language, timezone, time format, theme).
    
    Route: POST /me/settings/platform-prefs/
    
    Body (JSON):
    {
        "preferred_language": "en",
        "timezone_pref": "Asia/Dhaka",
        "time_format": "12h",
        "theme_preference": "dark"
    }
    
    Returns:
        JSON: {success: true, message: 'Platform preferences updated successfully'}
    """
    import json
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        data = json.loads(request.body)
        
        # Update preferred language
        if 'preferred_language' in data:
            language = data['preferred_language']
            if language in ['en', 'bn']:  # Only English for now, Bengali "Coming Soon"
                profile.preferred_language = language
        
        # Update timezone
        if 'timezone_pref' in data:
            timezone = data['timezone_pref']
            if timezone and len(timezone) < 100:
                profile.timezone_pref = timezone
        
        # Update time format
        if 'time_format' in data:
            time_format = data['time_format']
            if time_format in ['12h', '24h']:
                profile.time_format = time_format
        
        # Update theme preference
        if 'theme_preference' in data:
            theme = data['theme_preference']
            if theme in ['light', 'dark', 'system']:
                profile.theme_preference = theme
        
        profile.save()
        
        logger.info(f"Platform preferences updated for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Platform preferences updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating platform preferences: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_platform_preferences(request):
    """
    Get current platform preferences for the authenticated user.
    
    Route: GET /me/settings/platform-prefs/
    
    Returns:
        JSON: {
            success: true,
            preferences: {
                preferred_language: "en",
                timezone_pref: "Asia/Dhaka",
                time_format: "12h",
                theme_preference: "dark"
            }
        }
    """
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        preferences = {
            'preferred_language': profile.preferred_language,
            'timezone_pref': profile.timezone_pref,
            'time_format': profile.time_format,
            'theme_preference': profile.theme_preference,
        }
        
        return JsonResponse({
            'success': True,
            'preferences': preferences
        })
    
    except Exception as e:
        logger.error(f"Error loading platform preferences: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_wallet_settings(request):
    """
    Update wallet settings (mobile banking accounts, withdrawal preferences).
    
    Route: POST /me/settings/wallet/
    
    Body (JSON):
    {
        "bkash_enabled": true,
        "bkash_account": "01712345678",
        "nagad_enabled": false,
        "nagad_account": "",
        "rocket_enabled": true,
        "rocket_account": "01812345678",
        "auto_withdrawal_threshold": 1000,
        "auto_convert_to_usd": false
    }
    
    Returns:
        JSON: {success: true, message: 'Wallet settings updated successfully'}
    """
    import json
    from apps.user_profile.models import WalletSettings
    from apps.user_profile.utils import get_user_profile_safe
    from django.core.exceptions import ValidationError
    
    profile = get_user_profile_safe(request.user)
    
    try:
        data = json.loads(request.body)
        
        # Get or create wallet settings
        wallet, created = WalletSettings.objects.get_or_create(user_profile=profile)
        
        # Update bKash settings
        if 'bkash_enabled' in data:
            wallet.bkash_enabled = bool(data['bkash_enabled'])
        if 'bkash_account' in data:
            wallet.bkash_account = data['bkash_account'].strip()
        
        # Update Nagad settings
        if 'nagad_enabled' in data:
            wallet.nagad_enabled = bool(data['nagad_enabled'])
        if 'nagad_account' in data:
            wallet.nagad_account = data['nagad_account'].strip()
        
        # Update Rocket settings
        if 'rocket_enabled' in data:
            wallet.rocket_enabled = bool(data['rocket_enabled'])
        if 'rocket_account' in data:
            wallet.rocket_account = data['rocket_account'].strip()
        
        # Update withdrawal preferences
        if 'auto_withdrawal_threshold' in data:
            threshold = int(data['auto_withdrawal_threshold'])
            if threshold >= 0:
                wallet.auto_withdrawal_threshold = threshold
        
        if 'auto_convert_to_usd' in data:
            wallet.auto_convert_to_usd = bool(data['auto_convert_to_usd'])
        
        # Validate before saving (validators will run)
        try:
            wallet.full_clean()
        except ValidationError as ve:
            return JsonResponse({
                'success': False,
                'error': 'Validation failed',
                'details': ve.message_dict
            }, status=400)
        
        wallet.save()
        
        logger.info(f"Wallet settings updated for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Wallet settings updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Invalid value: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error updating wallet settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_wallet_settings(request):
    """
    Get current wallet settings for the authenticated user.
    
    Route: GET /me/settings/wallet/
    
    Returns:
        JSON: {
            success: true,
            settings: {
                bkash_enabled: false,
                bkash_account: "",
                ...
                enabled_methods: ["bkash", "rocket"]
            }
        }
    """
    from apps.user_profile.models import WalletSettings
    from apps.user_profile.utils import get_user_profile_safe
    
    profile = get_user_profile_safe(request.user)
    
    try:
        # Get or create with defaults
        wallet, created = WalletSettings.objects.get_or_create(user_profile=profile)
        
        settings = {
            'bkash_enabled': wallet.bkash_enabled,
            'bkash_account': wallet.bkash_account,
            'nagad_enabled': wallet.nagad_enabled,
            'nagad_account': wallet.nagad_account,
            'rocket_enabled': wallet.rocket_enabled,
            'rocket_account': wallet.rocket_account,
            'auto_withdrawal_threshold': wallet.auto_withdrawal_threshold,
            'auto_convert_to_usd': wallet.auto_convert_to_usd,
            'enabled_methods': wallet.get_enabled_methods(),
        }
        
        return JsonResponse({
            'success': True,
            'settings': settings
        })
    
    except Exception as e:
        logger.error(f"Error loading wallet settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

