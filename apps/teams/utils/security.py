"""
Task 10: Security utilities and permission checkers for Teams app
"""
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class TeamPermissions:
    """
    Centralized permission checking for team operations.
    Use these methods to ensure consistent security across the app.
    """
    
    @staticmethod
    def is_team_captain(user, team):
        """Check if user is the team captain."""
        if not user or not user.is_authenticated:
            return False
        
        return team.is_captain(user.userprofile)
    
    @staticmethod
    def is_team_member(user, team):
        """Check if user is an active team member."""
        if not user or not user.is_authenticated:
            return False
        
        return team.members.filter(
            profile__user=user,
            status='active'
        ).exists()
    
    @staticmethod
    def is_team_manager(user, team):
        """Check if user is captain or co-captain/manager."""
        if not user or not user.is_authenticated:
            return False
        
        # Captain check
        if TeamPermissions.is_team_captain(user, team):
            return True
        
        # Manager/Co-captain check
        return team.members.filter(
            profile__user=user,
            role__in=['manager', 'co_captain'],
            status='active'
        ).exists()
    
    @staticmethod
    def can_edit_team(user, team):
        """Check if user can edit team settings."""
        if not user or not user.is_authenticated:
            return False
        
        # Staff and superusers can always edit
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_captain(user, team)
    
    @staticmethod
    def can_manage_roster(user, team):
        """Check if user can add/remove team members."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_manager(user, team)
    
    @staticmethod
    def can_send_invites(user, team):
        """Check if user can send team invites."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_manager(user, team)
    
    @staticmethod
    def can_manage_sponsors(user, team):
        """Check if user can manage team sponsors."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_captain(user, team)
    
    @staticmethod
    def can_manage_promotions(user, team):
        """Check if user can manage team promotions."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_captain(user, team)
    
    @staticmethod
    def can_post_to_team(user, team):
        """Check if user can post to team page."""
        if not user or not user.is_authenticated:
            return False
        
        # Check if team allows posts
        if not team.allow_posts:
            return False
        
        # Team members can post
        return TeamPermissions.is_team_member(user, team)
    
    @staticmethod
    def can_moderate_posts(user, team):
        """Check if user can approve/delete team posts."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        return TeamPermissions.is_team_manager(user, team)
    
    @staticmethod
    def can_view_private_team(user, team):
        """Check if user can view private team details."""
        if not user or not user.is_authenticated:
            return False
        
        if user.is_staff or user.is_superuser:
            return True
        
        # Team members can always view
        if TeamPermissions.is_team_member(user, team):
            return True
        
        # Check if team is public
        return not getattr(team, 'is_private', False)


def require_team_permission(permission_check):
    """
    Decorator to check team permissions before allowing access.
    
    Usage:
        @require_team_permission(TeamPermissions.can_edit_team)
        def edit_team_view(request, slug):
            team = get_object_or_404(Team, slug=slug)
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Get team from kwargs (assumes 'team' or 'slug' parameter)
            team = kwargs.get('team')
            
            if not team:
                # Try to get team by slug
                slug = kwargs.get('slug') or kwargs.get('team_slug')
                if slug:
                    from apps.teams.models import Team
                    from django.shortcuts import get_object_or_404
                    team = get_object_or_404(Team, slug=slug)
                    kwargs['team'] = team
            
            if not team:
                raise PermissionDenied("Team not found")
            
            # Check permission
            if not permission_check(request.user, team):
                logger.warning(
                    f"Permission denied: {request.user.username} attempted "
                    f"{view_func.__name__} on team {team.name}"
                )
                raise PermissionDenied("You don't have permission to perform this action")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class FileUploadValidator:
    """
    Validate file uploads for security.
    """
    
    # Allowed file extensions
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
    
    # Maximum file sizes (in bytes)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_image(file):
        """
        Validate uploaded image file.
        Returns (is_valid, error_message)
        """
        import os
        
        # Check file size
        if file.size > FileUploadValidator.MAX_IMAGE_SIZE:
            return False, f"Image file too large. Maximum size is {FileUploadValidator.MAX_IMAGE_SIZE / 1024 / 1024}MB"
        
        # Check file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in FileUploadValidator.ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Invalid file type. Allowed types: {', '.join(FileUploadValidator.ALLOWED_IMAGE_EXTENSIONS)}"
        
        # Check file content type
        allowed_content_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_content_types:
            return False, "Invalid image content type"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitize uploaded filename to prevent directory traversal.
        """
        import os
        import re
        
        # Get just the filename, no path
        filename = os.path.basename(filename)
        
        # Remove any non-alphanumeric characters except dots, dashes, underscores
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:90] + ext
        
        return filename


class RateLimiter:
    """
    Simple rate limiting for write-heavy operations.
    """
    
    @staticmethod
    def check_rate_limit(user, action, limit=10, window=3600):
        """
        Check if user has exceeded rate limit for an action.
        
        Args:
            user: User object
            action: String identifier for the action (e.g., 'send_invite')
            limit: Maximum number of actions allowed
            window: Time window in seconds
        
        Returns:
            (is_allowed, remaining, reset_time)
        """
        from django.core.cache import cache
        from django.utils import timezone
        
        if not user or not user.is_authenticated:
            return False, 0, None
        
        cache_key = f"rate_limit:{user.id}:{action}"
        
        # Get current count
        data = cache.get(cache_key, {'count': 0, 'reset_at': timezone.now().timestamp() + window})
        
        current_time = timezone.now().timestamp()
        
        # Reset if window expired
        if current_time >= data['reset_at']:
            data = {'count': 0, 'reset_at': current_time + window}
        
        # Check if limit exceeded
        if data['count'] >= limit:
            remaining = 0
            is_allowed = False
        else:
            data['count'] += 1
            remaining = limit - data['count']
            is_allowed = True
        
        # Update cache
        cache.set(cache_key, data, window)
        
        reset_time = timezone.datetime.fromtimestamp(data['reset_at'], tz=timezone.get_current_timezone())
        
        return is_allowed, remaining, reset_time
    
    @staticmethod
    def get_rate_limit_info(user, action):
        """Get current rate limit info without incrementing."""
        from django.core.cache import cache
        from django.utils import timezone
        
        if not user or not user.is_authenticated:
            return {'count': 0, 'limit': 0, 'remaining': 0, 'reset_at': None}
        
        cache_key = f"rate_limit:{user.id}:{action}"
        data = cache.get(cache_key)
        
        if not data:
            return {'count': 0, 'limit': 10, 'remaining': 10, 'reset_at': None}
        
        return {
            'count': data.get('count', 0),
            'limit': 10,  # Default limit
            'remaining': max(0, 10 - data.get('count', 0)),
            'reset_at': timezone.datetime.fromtimestamp(data.get('reset_at', 0), tz=timezone.get_current_timezone())
        }


def require_rate_limit(action, limit=10, window=3600):
    """
    Decorator to enforce rate limiting on views.
    
    Usage:
        @require_rate_limit('send_invite', limit=5, window=3600)
        def send_invite_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            is_allowed, remaining, reset_time = RateLimiter.check_rate_limit(
                request.user, action, limit, window
            )
            
            if not is_allowed:
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'detail': f'You can perform this action {limit} times per hour',
                    'reset_at': reset_time.isoformat() if reset_time else None
                }, status=429)
            
            # Add rate limit info to request
            request.rate_limit_info = {
                'remaining': remaining,
                'reset_at': reset_time
            }
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


class CSRFValidator:
    """
    Additional CSRF validation for AJAX requests.
    """
    
    @staticmethod
    def validate_ajax_request(request):
        """
        Validate that AJAX request has proper CSRF token.
        """
        if not request.headers.get('X-CSRFToken'):
            logger.warning(f"AJAX request without CSRF token from {request.user}")
            return False
        
        return True
    
    @staticmethod
    def validate_origin(request):
        """
        Validate request origin matches expected domain.
        """
        from django.conf import settings
        
        origin = request.META.get('HTTP_ORIGIN')
        referer = request.META.get('HTTP_REFERER')
        
        allowed_hosts = settings.ALLOWED_HOSTS
        
        # Check if origin or referer matches allowed hosts
        if origin:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.hostname not in allowed_hosts:
                logger.warning(f"Request from invalid origin: {origin}")
                return False
        
        return True


class InputSanitizer:
    """
    Sanitize user input to prevent XSS and injection attacks.
    """
    
    @staticmethod
    def sanitize_html(html_content):
        """
        Sanitize HTML content to remove dangerous tags/attributes.
        """
        import bleach
        
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
        ]
        
        allowed_attributes = {
            'a': ['href', 'title'],
            'img': ['src', 'alt'],
        }
        
        return bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    
    @staticmethod
    def sanitize_user_input(text, max_length=None):
        """
        Basic sanitization for user text input.
        """
        import html
        
        # HTML escape
        text = html.escape(text)
        
        # Strip whitespace
        text = text.strip()
        
        # Limit length
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
