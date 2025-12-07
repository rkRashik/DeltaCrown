"""
DeltaCrown Team Creation Module - Modern Implementation
========================================================

This module handles the complete team creation flow with:
- 6-step wizard with real-time validation
- AJAX endpoints for name/tag uniqueness checking
- One-team-per-game enforcement
- Draft auto-save functionality
- Game-specific region loading
- Enhanced error handling and user guidance

Version: 2.0 (December 2024)
"""

import json
import logging
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from apps.teams.models import Team, TeamMembership
from apps.teams.forms import TeamCreationForm
from apps.teams.services.team_service import TeamService
from apps.games.services.game_service import GameService
from apps.common.region_config import get_regions_for_game
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)

# ==================== MAIN TEAM CREATE VIEW ====================

@login_required
@require_http_methods(["GET", "POST"])
def team_create_view(request):
    """
    Modern team creation view with 6-step wizard.
    
    GET: Renders the team creation wizard
    POST: Processes form submission and creates team
    
    Features:
    - Real-time validation via AJAX
    - Draft auto-save/restore
    - One-team-per-game enforcement
    - Live preview
    - Mobile-optimized
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == "POST":
        return _handle_team_creation_post(request, profile)
    
    # GET request - render wizard
    return _handle_team_creation_get(request, profile)


def _handle_team_creation_get(request, profile):
    """Handle GET request for team creation wizard."""
    
    # Check for existing draft
    draft_data = _load_draft_from_cache(request.user.id)
    
    # Prepare game configurations for JavaScript using NEW GameService
    game_configs = {}
    games = GameService.list_active_games()
    
    for game in games:
        # Get roster config for team size info
        roster_config = GameService.get_roster_config(game)
        default_team_size = roster_config.min_team_size if roster_config else 5
        
        # Get identity configuration for player ID field
        identity_configs = GameService.get_identity_validation_rules(game)
        player_id_label = identity_configs[0].display_name if identity_configs else "Game ID"
        player_id_placeholder = identity_configs[0].placeholder if identity_configs else ""
        
        # Use actual game image URLs or fallback
        image_url = ''
        if game.card_image:
            image_url = game.card_image.url
        elif game.icon:
            image_url = game.icon.url
        else:
            image_url = f"/static/img/game_cards/default.jpg"
        
        game_configs[game.slug] = {
            'name': game.display_name,
            'slug': game.slug,
            'platform': 'pc',  # Default, can be extended in Game model if needed
            'team_size': default_team_size,
            'roster_size': (roster_config.max_team_size + 2) if roster_config else (default_team_size + 2),
            'player_id_label': player_id_label,
            'player_id_format': player_id_placeholder,
            'color_primary': game.primary_color or '#00d9ff',
            'color_secondary': game.secondary_color or '#7000ff',
            'card_image': image_url,
        }
    
    # Check which games user already has teams for
    existing_teams = {}
    active_memberships = TeamMembership.objects.filter(
        profile=profile,
        status='ACTIVE'
    ).select_related('team')
    
    for membership in active_memberships:
        game_code = membership.team.game
        existing_teams[game_code] = {
            'name': membership.team.name,
            'tag': membership.team.tag,
            'slug': membership.team.slug,
        }
    
    # Prepare initial form
    initial = {}
    if draft_data:
        initial = {
            'name': draft_data.get('name', ''),
            'tag': draft_data.get('tag', ''),
            'tagline': draft_data.get('tagline', ''),
            'description': draft_data.get('description', ''),
            'game': draft_data.get('game', ''),
            'region': draft_data.get('region', ''),
            'twitter': draft_data.get('twitter', ''),
            'instagram': draft_data.get('instagram', ''),
            'discord': draft_data.get('discord', ''),
            'youtube': draft_data.get('youtube', ''),
            'twitch': draft_data.get('twitch', ''),
        }
    
    form = TeamCreationForm(user=request.user, initial=initial)
    
    # Prepare user profile data for game ID autofill
    user_profile_data = {
        'riot_id': profile.riot_id or '',
        'steam_id': profile.steam_id or '',
        'mlbb_id': profile.mlbb_id or '',
        'pubg_mobile_id': profile.pubg_mobile_id or '',
        'free_fire_id': profile.free_fire_id or '',
        'codm_uid': profile.codm_uid or '',
        'efootball_id': profile.efootball_id or '',
        'ea_id': profile.ea_id or '',
    }
    
    context = {
        'form': form,
        'game_configs': json.dumps(game_configs),
        'existing_teams': json.dumps(existing_teams),
        'has_draft': 'true' if draft_data else 'false',
        'draft_data': json.dumps(draft_data if draft_data else {}),
        'user_profile': json.dumps(user_profile_data),
        'profile': profile,
        'STATIC_URL': settings.STATIC_URL,
    }
    
    return render(request, 'teams/team_create/index.html', context)


def _handle_team_creation_post(request, profile):
    """Handle POST request for team creation."""
    
    # Check if AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    form = TeamCreationForm(request.POST, request.FILES, user=request.user)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                # Create team via service layer (SINGLE SOURCE OF TRUTH)
                team = TeamService.create_team(
                    name=form.cleaned_data['name'],
                    captain_profile=profile,
                    game=form.cleaned_data['game'],
                    tag=form.cleaned_data.get('tag'),
                    tagline=form.cleaned_data.get('tagline', ''),
                    description=form.cleaned_data.get('description', ''),
                    logo=form.cleaned_data.get('logo'),
                    banner_image=form.cleaned_data.get('banner_image'),
                    region=form.cleaned_data.get('region', ''),
                    twitter=form.cleaned_data.get('twitter', ''),
                    instagram=form.cleaned_data.get('instagram', ''),
                    discord=form.cleaned_data.get('discord', ''),
                    youtube=form.cleaned_data.get('youtube', ''),
                    twitch=form.cleaned_data.get('twitch', ''),
                )
                
                # Save game ID to user profile if provided
                game_id = request.POST.get('game_id', '').strip()
                if game_id:
                    game_code = team.game
                    
                    # Map game slugs to profile fields (using actual slugs from Game model)
                    game_id_fields = {
                        'valorant': 'riot_id',
                        'counter-strike-2': 'steam_id',
                        'dota-2': 'steam_id',
                        'mobile-legends': 'mlbb_id',
                        'pubg-mobile': 'pubg_mobile_id',
                        'free-fire': 'free_fire_id',
                        'call-of-duty-mobile': 'codm_uid',
                        'efootball': 'efootball_id',
                        'ea-sports-fc-26': 'ea_id',
                    }
                    
                    field_name = game_id_fields.get(game_code)
                    if field_name and not getattr(profile, field_name):
                        setattr(profile, field_name, game_id)
                        profile.save(update_fields=[field_name])
                        logger.info(f"Saved {field_name} to profile for user {request.user.id}")
                
                # Clear draft from cache
                _clear_draft_from_cache(request.user.id)
                
                # Success message
                messages.success(
                    request,
                    f"🎉 Team '{team.name}' created successfully! Welcome to the competition."
                )
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'redirect_url': f'/teams/setup/{team.slug}/',
                        'team': {
                            'name': team.name,
                            'tag': team.tag,
                            'slug': team.slug,
                        }
                    })
                
                return redirect('teams:setup', slug=team.slug)
                
        except Exception as e:
            logger.exception(f"Team creation failed: {type(e).__name__}: {e}")
            
            # In development, show actual error; in production, use generic message
            from django.conf import settings
            if settings.DEBUG:
                error_message = f"Team creation failed: {type(e).__name__}: {str(e)}"
            else:
                error_message = "An error occurred while creating your team. Please try again."
            
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': error_message,
                    'exception_type': type(e).__name__ if settings.DEBUG else None,
                }, status=500)
            
            messages.error(request, error_message)
    
    else:
        # Form has validation errors
        if is_ajax:
            # Map errors to steps for navigation
            error_step = _get_error_step(form.errors)
            
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'error_step': error_step,
                'error': "Please correct the errors below."
            }, status=400)
        
        # Non-AJAX: render form with errors
        messages.error(request, "Please correct the errors below.")
    
    # Re-render form with errors - reconstruct game configs
    active_games = GameService.list_active_games()
    game_configs = {}
    for game in active_games:
        roster_config = GameService.get_roster_config(game)
        default_team_size = roster_config.min_team_size if roster_config else 5
        identity_configs = GameService.get_identity_validation_rules(game)
        player_id_label = identity_configs[0].display_name if identity_configs else "Game ID"
        player_id_placeholder = identity_configs[0].placeholder if identity_configs else ""
        
        image_url = ''
        if game.card_image:
            image_url = game.card_image.url
        elif game.icon:
            image_url = game.icon.url
        else:
            image_url = "/static/img/game_cards/default.jpg"
        
        game_configs[game.slug] = {
            'name': game.display_name,
            'slug': game.slug,
            'platform': 'pc',
            'team_size': default_team_size,
            'roster_size': (roster_config.max_team_size + 2) if roster_config else (default_team_size + 2),
            'player_id_label': player_id_label,
            'player_id_format': player_id_placeholder,
            'color_primary': game.primary_color or '#00d9ff',
            'color_secondary': game.secondary_color or '#7000ff',
            'card_image': image_url,
        }
    
    context = {
        'form': form,
        'game_configs': json.dumps(game_configs),
        'profile': profile,
        'STATIC_URL': settings.STATIC_URL,
    }
    
    return render(request, 'teams/team_create/index.html', context)


def _get_error_step(errors):
    """Map form errors to wizard step numbers."""
    
    # Step 1: Name, Tag, Tagline
    if any(field in errors for field in ['name', 'tag', 'tagline']):
        return 1
    
    # Step 2-3: Game, Region
    if any(field in errors for field in ['game', 'region']):
        return 2
    
    # Step 4: Branding, Description, Social
    if any(field in errors for field in ['logo', 'banner_image', 'description', 'twitter', 'instagram', 'discord', 'youtube', 'twitch']):
        return 4
    
    # Step 6: Terms
    if 'accept_terms' in errors:
        return 6
    
    # Default to step 1
    return 1


# ==================== AJAX VALIDATION ENDPOINTS ====================

@login_required
@require_GET
def validate_team_name(request):
    """
    AJAX endpoint to validate team name uniqueness.
    
    GET params:
        name: Team name to validate
    
    Returns:
        JSON: {valid: bool, message: str, suggestions: [str]}
    """
    from apps.teams.validators import validate_team_name as canonical_validate_name
    from django.core.exceptions import ValidationError
    
    name = request.GET.get('name', '').strip()
    
    if not name:
        return JsonResponse({
            'valid': False,
            'message': 'Team name is required.'
        })
    
    try:
        # Use canonical validator
        canonical_validate_name(name, check_uniqueness=True)
        return JsonResponse({
            'valid': True,
            'message': 'Perfect! This name is available.'
        })
    except ValidationError as e:
        # Generate suggestions if name is taken
        if 'already taken' in str(e).lower() or 'exists' in str(e).lower():
            suggestions = [
                f"{name} Gaming",
                f"{name} Esports",
                f"{name} Squad",
                f"{name} Team",
            ]
            return JsonResponse({
                'valid': False,
                'message': str(e),
                'suggestions': suggestions
            })
        else:
            return JsonResponse({
                'valid': False,
                'message': str(e)
            })


@login_required
@require_GET
def validate_team_tag(request):
    """
    AJAX endpoint to validate team tag uniqueness.
    
    GET params:
        tag: Team tag to validate
    
    Returns:
        JSON: {valid: bool, message: str, suggestions: [str]}
    """
    from apps.teams.validators import validate_team_tag as canonical_validate_tag
    from django.core.exceptions import ValidationError
    
    tag = request.GET.get('tag', '').strip().upper()
    
    if not tag:
        return JsonResponse({
            'valid': False,
            'message': 'Team tag is required.'
        })
    
    try:
        # Use canonical validator
        canonical_validate_tag(tag, check_uniqueness=True)
        return JsonResponse({
            'valid': True,
            'message': 'Nice! This tag is available.'
        })
    except ValidationError as e:
        # Generate suggestions if tag is taken
        if 'already in use' in str(e).lower() or 'exists' in str(e).lower():
            suggestions = [
                f"{tag}E",
                f"{tag}GG",
                f"{tag}X",
                f"{tag}PH",
                f"{tag}BD",
            ]
            return JsonResponse({
                'valid': False,
                'message': str(e),
                'suggestions': suggestions
            })
        else:
            return JsonResponse({
                'valid': False,
                'message': str(e)
            })


@login_required
@require_GET
def check_existing_team(request):
    """
    Check if user already has a team for the selected game.
    
    GET params:
        game: Game code (VALORANT, CS2, etc.)
    
    Returns:
        JSON: {
            has_team: bool,
            team: {name, tag, slug} or null,
            can_create: bool,
            message: str
        }
    """
    game_code = request.GET.get('game', '').strip().upper()
    
    if not game_code:
        return JsonResponse({
            'has_team': False,
            'can_create': True
        })
    
    profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check for existing active membership
    existing = TeamMembership.objects.filter(
        profile=profile,
        team__game=game_code,
        status='ACTIVE'
    ).select_related('team').first()
    
    if existing:
        team = existing.team
        game = GameService.get_game(game_code)
        game_name = game.display_name if game else game_code
        
        return JsonResponse({
            'has_team': True,
            'team': {
                'name': team.name,
                'tag': team.tag,
                'slug': team.slug,
            },
            'can_create': False,
            'message': f"You're already a member of {team.name} ({team.tag}) for {game_name}. You can only have one active team per game."
        })
    
    return JsonResponse({
        'has_team': False,
        'team': None,
        'can_create': True,
        'message': 'You can create a team for this game.'
    })


@login_required
@require_GET
def get_game_regions_api(request, game_code):
    """
    Get available regions for a specific game.
    
    URL params:
        game_code: Game code (VALORANT, CS2, etc.)
    
    Returns:
        JSON: {
            success: bool,
            game: str,
            regions: [[code, name], ...]
        }
    """
    game_code = game_code.upper()
    
    # Validate game exists
    game = GameService.get_game(game_code.lower())
    if not game:
        return JsonResponse({
            'success': False,
            'error': f'Invalid game code: {game_code}'
        }, status=400)
    
    regions = get_regions_for_game(game_code)
    
    return JsonResponse({
        'success': True,
        'game': game_code,
        'game_name': game.display_name,
        'regions': regions
    })


# ==================== DRAFT AUTO-SAVE SYSTEM ====================

@login_required
@require_POST
def save_draft_api(request):
    """
    Save team creation draft to cache.
    
    POST data: JSON with form fields
    
    Returns:
        JSON: {success: bool, message: str}
    """
    try:
        data = json.loads(request.body)
        
        # Validate data
        draft_data = {
            'name': data.get('name', ''),
            'tag': data.get('tag', ''),
            'tagline': data.get('tagline', ''),
            'description': data.get('description', ''),
            'game': data.get('game', ''),
            'region': data.get('region', ''),
            'twitter': data.get('twitter', ''),
            'instagram': data.get('instagram', ''),
            'discord': data.get('discord', ''),
            'youtube': data.get('youtube', ''),
            'twitch': data.get('twitch', ''),
            'saved_at': timezone.now().isoformat(),
        }
        
        # Save to cache (7 days expiry)
        cache_key = f'team_create_draft_{request.user.id}'
        cache.set(cache_key, draft_data, timeout=60 * 60 * 24 * 7)  # 7 days
        
        return JsonResponse({
            'success': True,
            'message': 'Draft saved successfully.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data.'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Draft save error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to save draft.'
        }, status=500)


@login_required
@require_GET
def load_draft_api(request):
    """
    Load team creation draft from cache.
    
    Returns:
        JSON: {
            success: bool,
            has_draft: bool,
            draft: {form_fields} or null
        }
    """
    draft_data = _load_draft_from_cache(request.user.id)
    
    if draft_data:
        # Calculate time ago
        saved_at = draft_data.get('saved_at')
        if saved_at:
            saved_time = timezone.datetime.fromisoformat(saved_at)
            time_ago = _humanize_timedelta(timezone.now() - saved_time)
            draft_data['time_ago'] = time_ago
        
        return JsonResponse({
            'success': True,
            'has_draft': True,
            'draft': draft_data
        })
    
    return JsonResponse({
        'success': True,
        'has_draft': False,
        'draft': None
    })


@login_required
@require_POST
def clear_draft_api(request):
    """
    Clear team creation draft from cache.
    
    Returns:
        JSON: {success: bool}
    """
    _clear_draft_from_cache(request.user.id)
    
    return JsonResponse({
        'success': True,
        'message': 'Draft cleared successfully.'
    })


# ==================== HELPER FUNCTIONS ====================

def _load_draft_from_cache(user_id):
    """Load draft data from cache."""
    cache_key = f'team_create_draft_{user_id}'
    return cache.get(cache_key)


def _clear_draft_from_cache(user_id):
    """Clear draft data from cache."""
    cache_key = f'team_create_draft_{user_id}'
    cache.delete(cache_key)


def _humanize_timedelta(delta):
    """Convert timedelta to human-readable string."""
    seconds = int(delta.total_seconds())
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
