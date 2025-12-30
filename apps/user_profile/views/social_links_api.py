"""
UP-PHASE15-SESSION3: Social Links CRUD API
Extends settings_api.py with create/delete endpoints for individual social links.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def social_link_create_api(request):
    """
    Create a new social link.
    
    Route: POST /profile/api/social-links/create/
    
    Body (JSON):
    {
        "platform": "twitter",
        "url": "https://twitter.com/username",
        "display_text": "@username" // optional
    }
    
    Returns:
        JSON: {success: true, link: {...}}
    """
    from apps.user_profile.models import SocialLink
    
    try:
        data = json.loads(request.body)
        platform = data.get('platform', '').strip()
        url = data.get('url', '').strip()
        display_text = data.get('display_text', '').strip() or None
        
        # Validation
        if not platform or not url:
            return JsonResponse({
                'success': False,
                'error': 'Platform and URL are required'
            }, status=400)
        
        # Validate platform
        valid_platforms = [choice[0] for choice in SocialLink.PLATFORM_CHOICES]
        if platform not in valid_platforms:
            return JsonResponse({
                'success': False,
                'error': f'Invalid platform. Must be one of: {", ".join(valid_platforms)}'
            }, status=400)
        
        # Validate URL format
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError
        url_validator = URLValidator()
        try:
            url_validator(url)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid URL format'
            }, status=400)
        
        # Check if user already has link for this platform
        existing = SocialLink.objects.filter(user=request.user, platform=platform).first()
        if existing:
            return JsonResponse({
                'success': False,
                'error': f'You already have a {platform} link. Please edit it instead.'
            }, status=400)
        
        # Create link
        link = SocialLink.objects.create(
            user=request.user,
            platform=platform,
            url=url,
            display_text=display_text,
        )
        
        return JsonResponse({
            'success': True,
            'link': {
                'id': link.id,
                'platform': link.platform,
                'url': link.url,
                'display_text': link.display_text,
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating social link: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def social_link_update_single_api(request):
    """
    Update an existing social link.
    
    Route: POST /profile/api/social-links/update/
    
    Body (JSON):
    {
        "id": 123,
        "platform": "twitter",
        "url": "https://twitter.com/new_username",
        "display_text": "@new_username"
    }
    
    Returns:
        JSON: {success: true, link: {...}}
    """
    from apps.user_profile.models import SocialLink
    
    try:
        data = json.loads(request.body)
        link_id = data.get('id')
        
        if not link_id:
            return JsonResponse({
                'success': False,
                'error': 'Link ID is required'
            }, status=400)
        
        # Get link (must belong to user)
        try:
            link = SocialLink.objects.get(id=link_id, user=request.user)
        except SocialLink.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Social link not found or access denied'
            }, status=404)
        
        # Update fields
        platform = data.get('platform', '').strip()
        url = data.get('url', '').strip()
        display_text = data.get('display_text', '').strip() or None
        
        if platform:
            valid_platforms = [choice[0] for choice in SocialLink.PLATFORM_CHOICES]
            if platform not in valid_platforms:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid platform'
                }, status=400)
            link.platform = platform
        
        if url:
            from django.core.validators import URLValidator
            from django.core.exceptions import ValidationError
            url_validator = URLValidator()
            try:
                url_validator(url)
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid URL format'
                }, status=400)
            link.url = url
        
        link.display_text = display_text
        link.save()
        
        return JsonResponse({
            'success': True,
            'link': {
                'id': link.id,
                'platform': link.platform,
                'url': link.url,
                'display_text': link.display_text,
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating social link: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def social_link_delete_api(request):
    """
    Delete a social link.
    
    Route: POST /profile/api/social-links/delete/
    
    Body (JSON):
    {
        "id": 123
    }
    
    Returns:
        JSON: {success: true}
    """
    from apps.user_profile.models import SocialLink
    
    try:
        data = json.loads(request.body)
        link_id = data.get('id')
        
        if not link_id:
            return JsonResponse({
                'success': False,
                'error': 'Link ID is required'
            }, status=400)
        
        # Get and delete link (must belong to user)
        try:
            link = SocialLink.objects.get(id=link_id, user=request.user)
            link.delete()
        except SocialLink.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Social link not found or access denied'
            }, status=404)
        
        return JsonResponse({'success': True})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error deleting social link: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def social_links_list_api(request):
    """
    List all social links for current user.
    
    Route: GET /profile/api/social-links/
    
    Returns:
        JSON: {success: true, links: [{id, platform, url, display_text}, ...]}
    """
    from apps.user_profile.models import SocialLink
    
    try:
        links = SocialLink.objects.filter(user=request.user).order_by('platform')
        
        links_list = [{
            'id': link.id,
            'platform': link.platform,
            'url': link.url,
            'display_text': link.display_text,
        } for link in links]
        
        return JsonResponse({
            'success': True,
            'links': links_list
        })
    
    except Exception as e:
        logger.error(f"Error listing social links: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
