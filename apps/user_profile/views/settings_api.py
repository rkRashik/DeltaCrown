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
    
    Fields:
    - visibility_preset: 'PUBLIC', 'PROTECTED', or 'PRIVATE'
    - show_* toggles (various boolean fields)
    
    Returns:
        Redirect to privacy page with success message
    """
    from apps.user_profile.utils import get_user_profile_safe
    from apps.user_profile.models import PrivacySettings
    
    profile = get_user_profile_safe(request.user)
    
    # Get or create privacy settings
    privacy, created = PrivacySettings.objects.get_or_create(user_profile=profile)
    
    # Capture before state
    before_state = {
        'visibility_preset': privacy.visibility_preset,
        'show_social_links': privacy.show_social_links,
        'show_activity_feed': privacy.show_activity_feed,
        'show_teams': privacy.show_teams,
        'show_tournaments': privacy.show_tournaments,
    }
    
    # Update preset
    preset = request.POST.get('visibility_preset', 'PUBLIC')
    if preset in ['PUBLIC', 'PROTECTED', 'PRIVATE']:
        privacy.visibility_preset = preset
    
    # Update toggles (All 25 model fields)
    privacy.show_real_name = request.POST.get('show_real_name') == 'on'
    privacy.show_email = request.POST.get('show_email') == 'on'
    privacy.show_phone = request.POST.get('show_phone') == 'on'
    privacy.show_age = request.POST.get('show_age') == 'on'
    privacy.show_gender = request.POST.get('show_gender') == 'on'
    privacy.show_country = request.POST.get('show_country') == 'on'
    privacy.show_address = request.POST.get('show_address') == 'on'
    privacy.show_game_ids = request.POST.get('show_game_ids') == 'on'
    privacy.show_match_history = request.POST.get('show_match_history') == 'on'
    privacy.show_teams = request.POST.get('show_teams') == 'on'
    privacy.show_achievements = request.POST.get('show_achievements') == 'on'
    privacy.show_activity_feed = request.POST.get('show_activity_feed') == 'on'
    privacy.show_tournaments = request.POST.get('show_tournaments') == 'on'
    privacy.show_social_links = request.POST.get('show_social_links') == 'on'
    privacy.show_inventory_value = request.POST.get('show_inventory_value') == 'on'
    privacy.show_level_xp = request.POST.get('show_level_xp') == 'on'
    privacy.allow_team_invites = request.POST.get('allow_team_invites') == 'on'
    privacy.allow_friend_requests = request.POST.get('allow_friend_requests') == 'on'
    privacy.allow_direct_messages = request.POST.get('allow_direct_messages') == 'on'
    
    privacy.save()
    
    # Log audit event
    after_state = {
        'visibility_preset': privacy.visibility_preset,
        'show_social_links': privacy.show_social_links,
        'show_activity_feed': privacy.show_activity_feed,
        'show_teams': privacy.show_teams,
        'show_tournaments': privacy.show_tournaments,
    }
    
    privacy.save()
    
    messages.success(request, 'Privacy settings saved successfully')
    return redirect(reverse('user_profile:profile_privacy_v2'))
