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
        
        return JsonResponse({
            'success': True,
            'url': url,
            'preview_url': url,
            'message': f'{media_type.capitalize()} uploaded successfully'
        })
    
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
        "privacy_settings": {
            "show_real_name": false,
            "show_email": false,
            ...
        }
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
        settings_data = data.get('privacy_settings', {})
        
        # Get or create privacy settings
        privacy, created = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        # Update preset if provided
        if 'visibility_preset' in settings_data:
            preset = settings_data['visibility_preset']
            if preset in ['PUBLIC', 'PROTECTED', 'PRIVATE']:
                privacy.visibility_preset = preset
        
        # Update all toggles (accept both camelCase and snake_case)
        boolean_fields = [
            'show_real_name', 'show_email', 'show_phone', 'show_age', 'show_gender',
            'show_country', 'show_address', 'show_game_ids', 'show_match_history',
            'show_teams', 'show_achievements', 'show_activity_feed', 'show_tournaments',
            'show_social_links', 'show_inventory_value', 'show_level_xp',
            'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages'
        ]
        
        for field in boolean_fields:
            if field in settings_data:
                setattr(privacy, field, bool(settings_data[field]))
        
        privacy.save()
        
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
            'show_real_name': privacy.show_real_name,
            'show_email': privacy.show_email,
            'show_bio': privacy.show_bio if hasattr(privacy, 'show_bio') else True,
            'show_passports': privacy.show_game_ids if hasattr(privacy, 'show_game_ids') else True,
            'show_socials': privacy.show_social_links if hasattr(privacy, 'show_social_links') else True,
            'allow_team_invites': privacy.allow_team_invites if hasattr(privacy, 'allow_team_invites') else True,
        }
        
        return JsonResponse({
            'success': True,
            'settings': settings
        })
    
    except Exception as e:
        logger.error(f"Error loading privacy settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
