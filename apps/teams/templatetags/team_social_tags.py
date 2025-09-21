"""
Team Social Template Tags
"""
from django import template
from django.contrib.auth.models import User
from apps.user_profile.models import UserProfile

register = template.Library()


@register.filter
def user_has_liked(likes, user_profile):
    """Check if user has liked a post."""
    if not user_profile:
        return False
    return likes.filter(user=user_profile).exists()


@register.filter  
def get_user_initial(user):
    """Get user's first initial for avatars."""
    if hasattr(user, 'first_name') and user.first_name:
        return user.first_name[0].upper()
    elif hasattr(user, 'username') and user.username:
        return user.username[0].upper()
    return 'U'


@register.filter
def time_ago(timestamp):
    """Convert timestamp to readable time ago format."""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    if not timestamp:
        return ""
        
    now = timezone.now()
    diff = now - timestamp
    
    if diff.days > 0:
        if diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    
    return "Just now"


@register.inclusion_tag('teams/partials/activity_icon.html')
def activity_icon(activity_type):
    """Render activity type icon."""
    icon_map = {
        'post_created': 'fas fa-edit',
        'comment_created': 'fas fa-comment', 
        'post_liked': 'fas fa-heart',
        'team_followed': 'fas fa-user-plus',
        'member_joined': 'fas fa-users',
        'banner_updated': 'fas fa-image',
        'tournament_joined': 'fas fa-trophy',
        'match_won': 'fas fa-medal',
        'match_lost': 'fas fa-times-circle',
    }
    
    return {
        'icon_class': icon_map.get(activity_type, 'fas fa-bell'),
        'activity_type': activity_type
    }


@register.filter
def truncate_smart(text, length=100):
    """Smart truncation that breaks at word boundaries."""
    if len(text) <= length:
        return text
    
    truncated = text[:length].rsplit(' ', 1)[0]
    return truncated + '...' if truncated else text[:length] + '...'


@register.simple_tag
def post_media_count(post):
    """Get media count for a post."""
    if hasattr(post, 'media'):
        return post.media.count()
    return 0


@register.filter
def visibility_icon(visibility):
    """Get icon for post visibility."""
    icons = {
        'public': 'fas fa-globe text-success',
        'followers': 'fas fa-users text-info', 
        'members': 'fas fa-lock text-warning',
        'private': 'fas fa-eye-slash text-danger'
    }
    return icons.get(visibility, 'fas fa-question')


@register.filter
def visibility_label(visibility):
    """Get human readable label for visibility."""
    labels = {
        'public': 'Public',
        'followers': 'Followers Only',
        'members': 'Members Only', 
        'private': 'Private'
    }
    return labels.get(visibility, visibility.title())


@register.inclusion_tag('teams/partials/user_avatar.html')
def user_avatar(user, size='md', show_name=False):
    """Render user avatar with optional name."""
    size_classes = {
        'xs': 'avatar-xs',  # 24px
        'sm': 'avatar-sm',  # 32px  
        'md': 'avatar-md',  # 48px
        'lg': 'avatar-lg',  # 64px
        'xl': 'avatar-xl'   # 96px
    }
    
    return {
        'user': user,
        'size_class': size_classes.get(size, 'avatar-md'),
        'show_name': show_name,
        'initial': get_user_initial(user)
    }


@register.simple_tag
def team_role_badge(team, user_profile):
    """Get role badge for user in team context."""
    if team.is_captain(user_profile):
        return '<span class="badge bg-warning"><i class="fas fa-crown"></i> Captain</span>'
    elif team.is_member(user_profile):
        return '<span class="badge bg-primary">Member</span>'
    return ''


@register.filter
def is_team_captain(team, member):
    """Check if a member is captain of the team."""
    try:
        return team.is_captain(member)
    except (AttributeError, TypeError):
        return False


@register.filter
def pluralize_smart(count, singular, plural=None):
    """Smart pluralization."""
    if plural is None:
        plural = singular + 's'
    return singular if count == 1 else plural


@register.simple_tag
def follower_count(team):
    """Get follower count for a team."""
    try:
        from apps.teams.models.social import TeamFollower
        return TeamFollower.objects.filter(team=team).count()
    except ImportError:
        # Fallback if social models don't exist yet
        return 0


@register.simple_tag
def recent_posts(team, limit=3):
    """Get recent posts for a team."""
    try:
        from apps.teams.models.social import TeamPost
        return TeamPost.objects.filter(
            team=team, 
            visibility='public'
        ).select_related('author', 'author__user').order_by('-created_at')[:limit]
    except ImportError:
        # Fallback if social models don't exist yet
        return []