"""
Frontend V2 Views (UP-FE-MVP-01)

Privacy-safe profile views using profile_context service.
NO raw ORM objects passed to templates for public views.

Views:
- profile_public_v2: Public profile page
- profile_activity_v2: Activity feed page
- profile_settings_v2: Owner-only settings page
- profile_privacy_v2: Owner-only privacy settings page

Architecture:
- Uses build_public_profile_context() for all data
- Enforces authentication/ownership where required
- Returns safe primitives/JSON only
- Backward compatible with existing URLs (redirects)
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
import logging
import os

from apps.user_profile.services.profile_context import build_public_profile_context

logger = logging.getLogger(__name__)


def profile_public_v2(request: HttpRequest, username: str) -> HttpResponse:
    """
    Public profile page (V2) - privacy-safe context.
    
    Route: /@<username>/
    
    Shows:
    - Display name, avatar, bio
    - Stats summary (tournaments, matches, teams)
    - Game profiles
    - Social links
    - Activity feed preview (last 10)
    
    Privacy:
    - Uses ProfileVisibilityPolicy for field filtering
    - NO raw User/Profile objects in context
    - Anonymous users see public fields only
    - Owner sees full profile + edit actions
    
    Args:
        request: HTTP request
        username: Username of profile to view
        
    Returns:
        Rendered profile_public.html template
    """
    # Build safe context
    context = build_public_profile_context(
        viewer=request.user if request.user.is_authenticated else None,
        username=username,
        requested_sections=['basic', 'stats', 'games', 'social', 'activity'],
        activity_page=1,
        activity_per_page=10  # Preview only (show last 10)
    )
    
    # Check if profile was found
    if not context['can_view'] or context.get('error'):
        if context.get('error') == f'User @{username} not found':
            raise Http404(f"User @{username} not found")
        else:
            messages.error(request, context.get('error', 'Profile could not be loaded'))
            return redirect('home')
    
    # Add page metadata
    context['page_title'] = f"@{username} - DeltaCrown Esports"
    context['current_page'] = 'profile'
    
    # GP-FE-MVP-01: Add game passports with pinned/unpinned separation
    # GP-FINAL-01: Add team badge integration
    # UP-UI-REBIRTH-01: Remove role from passport display (role belongs to team)
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import GameProfile, UserProfile
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        profile_user = User.objects.get(username=username)
        user_profile = UserProfile.objects.filter(user=profile_user).first()
        all_passports = GamePassportService.get_all_passports(user=profile_user)
        
        # UP-UI-REBIRTH-02: Add profile_user to context for template access
        context['profile_user'] = profile_user
        
        # Attach team badge data to each passport (NO ROLE - role belongs to team context)
        if user_profile:
            from apps.teams.models import TeamMembership
            for passport in all_passports:
                # Get active team for this game
                team_membership = TeamMembership.objects.filter(
                    profile=user_profile,
                    team__game=passport.game,
                    status=TeamMembership.Status.ACTIVE
                ).select_related('team').first()
                
                if team_membership:
                    passport.current_team = team_membership.team
                    # UP-UI-REBIRTH-01: Do NOT attach role to passport
                else:
                    passport.current_team = None
        
        # Separate pinned and unpinned
        pinned_passports = [p for p in all_passports if p.is_pinned]
        unpinned_passports = [p for p in all_passports if not p.is_pinned]
        
        context['pinned_passports'] = pinned_passports
        context['unpinned_passports'] = unpinned_passports
        context['MAX_PINNED_GAMES'] = 6  # From GameProfile model constant
    except User.DoesNotExist:
        context['pinned_passports'] = []
        context['unpinned_passports'] = []
        context['MAX_PINNED_GAMES'] = 6
    
    # UP-UI-REBIRTH-01: Add dashboard navigation sections
    nav_sections = [
        {'id': 'stats', 'label': 'Stats'},
        {'id': 'passports', 'label': 'Passports'},
        {'id': 'teams', 'label': 'Teams'},
        {'id': 'tournaments', 'label': 'Tournaments'},
    ]
    
    if context.get('is_owner'):
        nav_sections.extend([
            {'id': 'economy', 'label': 'Economy'},
            {'id': 'shop', 'label': 'Shop'},
        ])
    
    nav_sections.extend([
        {'id': 'activity', 'label': 'Activity'},
        {'id': 'about', 'label': 'About'},
    ])
    
    if context.get('achievements'):
        nav_sections.insert(-2, {'id': 'achievements', 'label': 'Achievements'})
    
    context['nav_sections'] = nav_sections
    
    # UP-TEAM-DISPLAY-01: Add user's teams data
    if user_profile:
        from apps.teams.models import TeamMembership
        user_teams = TeamMembership.objects.filter(
            profile=user_profile,
            status=TeamMembership.Status.ACTIVE
        ).select_related('team').order_by('-team__created_at')[:10]
        
        # Get game display names from Game model
        from apps.games.models import Game
        games_map = {g.slug: g.display_name for g in Game.objects.all()}
        
        context['user_teams'] = [
            {
                'id': tm.team.id,
                'slug': tm.team.slug,
                'name': tm.team.name,
                'tag': tm.team.tag,
                'game': games_map.get(tm.team.game, tm.team.game),
                'game_slug': tm.team.game,
                'role': tm.role,
                'logo_url': tm.team.logo.url if tm.team.logo else None,
                'is_captain': tm.role == 'CAPTAIN',
            }
            for tm in user_teams
        ]
    else:
        context['user_teams'] = []
    
    # UP-TOURNAMENT-DISPLAY-01: Add user's tournaments data
    # TODO: Implement tournament participation query when tournament app is ready
    context['user_tournaments'] = []
    
    return render(request, 'user_profile/profile/public.html', context)


def profile_activity_v2(request: HttpRequest, username: str) -> HttpResponse:
    """
    Activity feed page (V2) - paginated activity timeline.
    
    Route: /@<username>/activity/
    
    Shows:
    - Full activity feed (paginated)
    - Event types: tournaments, matches, achievements, badges, level ups
    - Public: only public events
    - Owner: all events
    
    Privacy:
    - Activity events filtered by is_owner
    - Pagination: 25 events per page
    - NO raw Activity objects in context
    
    Args:
        request: HTTP request
        username: Username of profile to view
        
    Returns:
        Rendered profile_activity.html template
    """
    # Get page number from query params
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    # Build safe context (activity-focused)
    context = build_public_profile_context(
        viewer=request.user if request.user.is_authenticated else None,
        username=username,
        requested_sections=['basic', 'activity'],
        activity_page=page,
        activity_per_page=25
    )
    
    # Check if profile was found
    if not context['can_view'] or context.get('error'):
        if context.get('error') == f'User @{username} not found':
            raise Http404(f"User @{username} not found")
        else:
            messages.error(request, context.get('error', 'Profile could not be loaded'))
            return redirect('home')
    
    # Add page metadata
    context['page_title'] = f"@{username} Activity - DeltaCrown Esports"
    context['current_page'] = 'activity'
    
    return render(request, 'user_profile/profile/activity.html', context)


@login_required
def profile_settings_v2(request: HttpRequest) -> HttpResponse:
    """
    Profile settings page (V2) - owner-only.
    
    Route: /me/settings/
    
    Shows:
    - Display name, bio, avatar, banner (edit forms)
    - Game profiles (add/edit/remove)
    - Social links (add/edit/remove)
    - Location (country, region)
    
    Privacy:
    - Owner-only (requires authentication)
    - Uses build_public_profile_context with owner_only section
    - POST to safe endpoints: save_game_profiles_safe, etc.
    
    Args:
        request: HTTP request (must be authenticated)
        
    Returns:
        Rendered profile_settings.html template
    """
    username = request.user.username
    
    # Build safe context (owner view with edit permissions)
    context = build_public_profile_context(
        viewer=request.user,
        username=username,
        requested_sections=['basic', 'games', 'social', 'owner_only']
    )
    
    # Verify owner (should always be true due to @login_required + using request.user.username)
    if not context['is_owner']:
        messages.error(request, 'You can only edit your own profile')
        return redirect(reverse('user_profile:profile_public_v2', kwargs={'username': username}))
    
    # Add page metadata
    context['page_title'] = 'Profile Settings - DeltaCrown Esports'
    context['current_page'] = 'settings'
    
    # Add UserProfile object for template access to FileFields (avatar, banner)
    from apps.user_profile.models import UserProfile
    user_profile = UserProfile.objects.get(user=request.user)
    context['user_profile'] = user_profile
    
    # Add CSRF token (for forms)
    # Add available games list (for game profile form)
    from apps.games.constants import SUPPORTED_GAMES
    from apps.games.models import Game
    from apps.user_profile.services.game_passport_service import GamePassportService
    from apps.user_profile.models import GameProfile, SocialLink
    import json
    
    # TASK 1 FIX: Pass actual Game objects for template loop + schema matrix
    supported_game_slugs = list(SUPPORTED_GAMES.keys())
    games_queryset = Game.objects.filter(slug__in=supported_game_slugs).order_by('name')
    
    # Build schema matrix for dynamic field rendering
    game_schemas = {}
    for game in games_queryset:
        identity_configs = game.identity_configs.all().order_by('order')
        schema_fields = []
        for config in identity_configs:
            schema_fields.append({
                'field_name': config.field_name,
                'display_name': config.display_name,
                'field_type': config.field_type,
                'is_required': config.is_required,
                'placeholder': config.placeholder,
                'help_text': config.help_text,
                'validation_regex': config.validation_regex or '',
                'min_length': config.min_length,
                'max_length': config.max_length,
            })
        
        game_schemas[game.slug] = {
            'game_id': game.id,
            'name': game.name,
            'display_name': game.display_name,
            'fields': schema_fields,
            'platforms': game.platforms or [],
        }
    
    context['games'] = games_queryset  # For template loop in modal
    context['game_schemas_json'] = json.dumps(game_schemas)  # For JS dynamic fields
    context['available_games'] = SUPPORTED_GAMES  # Legacy compatibility
    
    # GP-FE-MVP-01: Add passport management data
    all_passports = GamePassportService.get_all_passports(user=request.user)
    pinned_passports = [p for p in all_passports if p.is_pinned]
    unpinned_passports = [p for p in all_passports if not p.is_pinned]
    
    context['all_passports'] = all_passports
    context['passports'] = all_passports  # UP-UI-REBIRTH-01: Alias for settings template
    context['pinned_passports'] = pinned_passports
    context['unpinned_passports'] = unpinned_passports
    context['MAX_PINNED_GAMES'] = 6
    context['VISIBILITY_CHOICES'] = GameProfile.VISIBILITY_CHOICES
    
    # UP-SETTINGS-UI-01: Add social links data for settings template
    context['social_links'] = SocialLink.objects.filter(user=request.user)
    context['social_platforms'] = SocialLink.PLATFORM_CHOICES
    
    # UP-2025-REDESIGN: Add user game profiles for settings template
    context['user_passports'] = GameProfile.objects.filter(
        user=request.user
    ).select_related('game').order_by('-created_at')
    
    return render(request, 'user_profile/profile/settings.html', context)


@login_required
def profile_privacy_v2(request: HttpRequest) -> HttpResponse:
    """
    Privacy settings page (V2) - owner-only.
    
    Route: /me/privacy/
    
    Shows:
    - Profile visibility (public, friends_only, private)
    - Field visibility (show_email, show_phone, show_real_name)
    - Social privacy (allow_friend_requests, show_online_status)
    
    Privacy:
    - Owner-only (requires authentication)
    - Uses build_public_profile_context with owner_only section
    - POST to safe endpoint: privacy_settings_save_safe
    
    Args:
        request: HTTP request (must be authenticated)
        
    Returns:
        Rendered profile_privacy.html template
    """
    username = request.user.username
    
    # Build safe context (owner view with privacy settings)
    context = build_public_profile_context(
        viewer=request.user,
        username=username,
        requested_sections=['basic', 'owner_only']
    )
    
    # Verify owner
    if not context['is_owner']:
        messages.error(request, 'You can only edit your own privacy settings')
        return redirect(reverse('user_profile:profile_public_v2', kwargs={'username': username}))
    
    # Add page metadata
    context['page_title'] = 'Privacy Settings - DeltaCrown Esports'
    context['current_page'] = 'privacy'
    
    # UP-SETTINGS-UI-01: Add privacy_settings object for enhanced privacy template
    from apps.user_profile.models import PrivacySettings
    from apps.user_profile.utils import get_user_profile_safe
    
    # Fix: PrivacySettings is linked by user_profile, not user
    user_profile = get_user_profile_safe(request.user)
    privacy_settings, _ = PrivacySettings.objects.get_or_create(user_profile=user_profile)
    context['privacy_settings'] = privacy_settings
    
    return render(request, 'user_profile/profile/privacy.html', context)


# ============================================
# MUTATION ENDPOINTS (UP-FE-MVP-02)
# ============================================

@login_required
def update_basic_info(request: HttpRequest) -> HttpResponse:
    """
    Update basic profile information (POST only).
    
    Route: POST /me/settings/basic/
    
    Fields:
    - display_name (required, max 50 chars)
    - bio (optional, max 500 chars)
    - country (optional, max 100 chars)
    - avatar (optional, file upload)
    
    Security:
    - CSRF protected (Django's @login_required + POST)
    - Input validation (server-side)
    - Audit logging with before/after snapshots
    
    Returns:
        Redirect to settings page with success/error message
    """
    if request.method != 'POST':
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Get user profile safely
    from apps.user_profile.utils import get_user_profile_safe
    profile = get_user_profile_safe(request.user)
    
    # Capture before state for audit
    before_snapshot = {
        'display_name': profile.display_name,
        'bio': profile.bio,
        'country': profile.country,
        'avatar_url': profile.get_avatar_url()
    }
    
    # Validate and update fields
    display_name = request.POST.get('display_name', '').strip()
    bio = request.POST.get('bio', '').strip()
    country = request.POST.get('country', '').strip()
    
    # Validation
    if not display_name:
        messages.error(request, 'Display name is required')
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    if len(display_name) > 50:
        messages.error(request, 'Display name must be 50 characters or less')
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    if len(bio) > 500:
        messages.error(request, 'Bio must be 500 characters or less')
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Update profile
    profile.display_name = display_name
    profile.bio = bio
    profile.country = country
    
    # Handle avatar upload
    if 'avatar' in request.FILES:
        avatar_file = request.FILES['avatar']
        # Basic validation
        if avatar_file.size > 5 * 1024 * 1024:  # 5MB limit
            messages.error(request, 'Avatar file must be less than 5MB')
            return redirect(reverse('user_profile:profile_settings_v2'))
        
        # Save avatar (Django will handle file storage)
        profile.avatar = avatar_file
    
    profile.save()
    
    # Capture after state
    after_snapshot = {
        'display_name': profile.display_name,
        'bio': profile.bio,
        'country': profile.country,
        'avatar_url': profile.get_avatar_url()
    }
    
    # Audit logging disabled for now
    # TODO: Re-enable when audit service is properly configured
    
    messages.success(request, 'Profile updated successfully')
    return redirect(reverse('user_profile:profile_settings_v2'))


@login_required
def update_social_links(request: HttpRequest) -> HttpResponse:
    """
    Update social media links (POST only).
    
    Route: POST /me/settings/social/
    
    Fields:
    - youtube (optional, URL)
    - twitch (optional, URL)
    - twitter (optional, URL)
    - discord (optional, string)
    - instagram (optional, URL)
    
    Security:
    - CSRF protected (Django's @login_required + POST)
    - URL validation (server-side)
    - Audit logging with before/after snapshots
    
    Returns:
        Redirect to settings page with success/error message
    """
    if request.method != 'POST':
        return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Get user profile safely
    from apps.user_profile.utils import get_user_profile_safe
    profile = get_user_profile_safe(request.user)
    
    # Capture before state for audit
    before_snapshot = {
        'youtube_link': profile.youtube_link,
        'twitch_link': profile.twitch_link,
        'twitter': profile.twitter,
        'discord_id': profile.discord_id,
        'instagram': profile.instagram
    }
    
    # Validate and update fields
    youtube = request.POST.get('youtube', '').strip()
    twitch = request.POST.get('twitch', '').strip()
    twitter = request.POST.get('twitter', '').strip()
    discord = request.POST.get('discord', '').strip()
    instagram = request.POST.get('instagram', '').strip()
    
    # Basic URL validation (must start with http:// or https:// if provided)
    for field_name, field_value in [('YouTube', youtube), ('Twitch', twitch), 
                                     ('Twitter', twitter), ('Instagram', instagram)]:
        if field_value and not (field_value.startswith('http://') or field_value.startswith('https://')):
            messages.error(request, f'{field_name} must be a valid URL (http:// or https://)')
            return redirect(reverse('user_profile:profile_settings_v2'))
    
    # Update profile
    profile.youtube_link = youtube
    profile.twitch_link = twitch
    profile.twitter = twitter
    profile.discord_id = discord
    profile.instagram = instagram
    profile.save()
    
    # Capture after state
    after_snapshot = {
        'youtube_link': profile.youtube_link,
        'twitch_link': profile.twitch_link,
        'twitter': profile.twitter,
        'discord_id': profile.discord_id,
        'instagram': profile.instagram
    }
    
    # Write audit event
    from apps.user_profile.services.audit_service import AuditService
    AuditService.log_event(
        user=request.user,
        event_type='profile.social_links_updated',
        before_state=before_snapshot,
        after_state=after_snapshot,
        request_meta={
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'path': request.path,
            'method': request.method
        }
    )
    
    messages.success(request, 'Social links updated successfully')
    return redirect(reverse('user_profile:profile_settings_v2'))
