# apps/teams/views/create.py
"""
Team Creation Views & AJAX Endpoints
Production-ready team creation with dynamic roster management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import re

from ..models import Team, TeamMembership, TeamInvite
from ..forms import TeamCreationForm, TeamInviteForm
from ..game_config import GAME_CONFIGS, get_game_config, get_available_roles
from apps.user_profile.models import UserProfile


def _ensure_profile(user):
    """Helper to get or create user profile."""
    if not user.is_authenticated:
        return None
    return getattr(user, 'profile', None) or getattr(user, 'userprofile', None)


@login_required
def team_create_view(request):
    """
    Main team creation view with full formset support.
    Renders modern responsive UI with game-specific roster management.
    """
    profile = _ensure_profile(request.user)
    
    if not profile:
        messages.error(request, "Please complete your profile before creating a team.")
        return redirect('user_profile:edit')
    
    if request.method == "POST":
        form = TeamCreationForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            try:
                team = form.save()
                
                # Process roster data from V2 form
                roster_data = request.POST.get('roster_data', '[]')
                try:
                    invites = json.loads(roster_data)
                    for invite_data in invites:
                        _process_invite(team, request.user, invite_data)
                except json.JSONDecodeError:
                    pass  # Roster is optional
                
                messages.success(
                    request,
                    f"🎉 Team '{team.name}' created successfully! Welcome to your new team."
                )
                return redirect("teams:dashboard", slug=team.slug)
            
            except Exception as e:
                messages.error(request, f"Error creating team: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill game from query string
        initial = {}
        game = request.GET.get("game", "").strip()
        if game and game in GAME_CONFIGS:
            initial["game"] = game
        
        form = TeamCreationForm(user=request.user, initial=initial)
    
    # Prepare context with game configurations
    game_configs_json = {}
    for code, config in GAME_CONFIGS.items():
        game_configs_json[code] = {
            'name': config.name,
            'code': config.code,
            'display_name': config.name,
            'team_size': config.min_starters,
            'min_starters': config.min_starters,
            'max_starters': config.max_starters,
            'max_substitutes': config.max_substitutes,
            'max_roster': config.max_starters + config.max_substitutes,
            'roster': {
                'min': config.min_starters,
                'max': config.max_starters + config.max_substitutes
            },
            'roles': config.roles,
            'role_descriptions': config.role_descriptions,
            'regions': config.regions,  # Add regions
            'requires_unique_roles': config.requires_unique_roles,
            'allows_multi_role': config.allows_multi_role,
            'icon': f'/static/teams/img/game-icons/{code}.svg',
            'color': _get_game_color(code),
        }
    
    context = {
        'form': form,
        'game_configs': json.dumps(game_configs_json),  # Serialize for JavaScript
        'available_games': list(GAME_CONFIGS.keys()),
        'profile': profile,
    }
    
    return render(request, "teams/team_create.html", context)


def _process_invite(team, sender_user, invite_data):
    """Process a single invite from the creation form."""
    try:
        identifier = invite_data.get('identifier', '').strip()
        role = invite_data.get('role', 'PLAYER')
        message = invite_data.get('message', '')
        
        if not identifier:
            return
        
        # Find user by username or email
        profile = None
        if '@' in identifier:
            # Email lookup
            try:
                profile = UserProfile.objects.get(user__email__iexact=identifier)
            except UserProfile.DoesNotExist:
                return
        else:
            # Username lookup
            try:
                profile = UserProfile.objects.get(user__username__iexact=identifier)
            except UserProfile.DoesNotExist:
                return
        
        # Check if already a member
        if TeamMembership.objects.filter(team=team, profile=profile, status='ACTIVE').exists():
            return
        
        # Check if already invited
        if TeamInvite.objects.filter(team=team, invited_user=profile, status='PENDING').exists():
            return
        
        # Create invite
        invite = TeamInvite.objects.create(
            team=team,
            invited_user=profile,
            role=role,
            message=message,
            inviter=sender_user
        )
        
    except Exception:
        pass  # Silently skip failed invites


def _get_game_color(game_code):
    """Get color code for game."""
    colors = {
        'valorant': '#FF4655',
        'cs2': '#F7941D',
        'csgo': '#F7941D',
        'dota2': '#B01E26',
        'mlbb': '#4169E1',
        'pubg': '#F7B733',
        'freefire': '#FF6B35',
        'efootball': '#00A0DC',
        'fc26': '#00A0DC',
        'codm': '#000000',
    }
    return colors.get(game_code, '#6366F1')


# ============================================================================
# AJAX ENDPOINTS
# ============================================================================

@require_http_methods(["GET", "POST"])
def validate_team_name(request):
    """
    AJAX endpoint to validate team name availability.
    Returns: {"valid": bool, "message": str}
    """
    try:
        # Support both GET (V2) and POST (V1) requests
        if request.method == "GET":
            name = request.GET.get('name', '').strip()
            game = request.GET.get('game', '').strip()
        else:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            game = data.get('game', '').strip()
        
        if not name:
            return JsonResponse({
                'valid': False,
                'message': 'Team name is required'
            })
        
        if len(name) < 3:
            return JsonResponse({
                'valid': False,
                'message': 'Team name must be at least 3 characters'
            })
        
        if len(name) > 50:
            return JsonResponse({
                'valid': False,
                'message': 'Team name cannot exceed 50 characters'
            })
        
        # Check uniqueness (optionally per game)
        query = Team.objects.filter(name__iexact=name)
        if game:
            query = query.filter(game=game)
        
        exists = query.exists()
        
        return JsonResponse({
            'valid': not exists,
            'message': 'Team name already exists' if exists else 'Team name is available'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid request'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
def validate_team_tag(request):
    """
    AJAX endpoint to validate team tag availability.
    Returns: {"valid": bool, "message": str}
    """
    try:
        # Support both GET (V2) and POST (V1) requests
        if request.method == "GET":
            tag = request.GET.get('tag', '').strip().upper()
            game = request.GET.get('game', '').strip()
        else:
            data = json.loads(request.body)
            tag = data.get('tag', '').strip().upper()
            game = data.get('game', '').strip()
        
        if not tag:
            return JsonResponse({
                'valid': False,
                'message': 'Team tag is required'
            })
        
        if len(tag) < 2:
            return JsonResponse({
                'valid': False,
                'message': 'Team tag must be at least 2 characters'
            })
        
        if len(tag) > 10:
            return JsonResponse({
                'valid': False,
                'message': 'Team tag cannot exceed 10 characters'
            })
        
        # Check format (alphanumeric only)
        if not re.match(r'^[A-Z0-9]+$', tag):
            return JsonResponse({
                'valid': False,
                'message': 'Team tag can only contain letters and numbers'
            })
        
        # Check uniqueness (optionally per game)
        query = Team.objects.filter(tag__iexact=tag)
        if game:
            query = query.filter(game=game)
        
        exists = query.exists()
        
        return JsonResponse({
            'valid': not exists,
            'message': 'Team tag already exists' if exists else 'Team tag is available'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid request'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def get_game_config_api(request, game_code):
    """
    AJAX endpoint to get game-specific configuration.
    Returns: Game config JSON with roles, roster sizes, etc.
    """
    try:
        if game_code not in GAME_CONFIGS:
            return JsonResponse({'error': f'Unsupported game: {game_code}'}, status=404)
        
        config = GAME_CONFIGS[game_code]
        
        return JsonResponse({
            'game': config.code,
            'display_name': config.name,
            'icon': f'/static/teams/img/game-icons/{config.code}.svg',
            'color': _get_game_color(config.code),
            'team_size': config.min_starters,
            'min_starters': config.min_starters,
            'max_starters': config.max_starters,
            'max_substitutes': config.max_substitutes,
            'max_roster': config.max_starters + config.max_substitutes,
            'roles': config.roles,
            'role_descriptions': config.role_descriptions,
            'requires_unique_roles': config.requires_unique_roles,
            'allows_multi_role': config.allows_multi_role,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def validate_user_identifier(request):
    """
    AJAX endpoint to validate username/email for invites.
    Returns: {"valid": bool, "user": {...}, "reason": str}
    """
    try:
        data = json.loads(request.body)
        identifier = data.get('identifier', '').strip()
        
        if not identifier:
            return JsonResponse({
                'valid': False,
                'reason': 'Username or email is required'
            })
        
        profile = None
        
        # Try email first
        if '@' in identifier:
            try:
                profile = UserProfile.objects.select_related('user').get(user__email__iexact=identifier)
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'reason': 'No user found with this email'
                })
        else:
            # Try username
            try:
                profile = UserProfile.objects.select_related('user').get(user__username__iexact=identifier)
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'reason': 'No user found with this username'
                })
        
        # Check if trying to invite self
        if profile.user == request.user:
            return JsonResponse({
                'valid': False,
                'reason': 'You cannot invite yourself'
            })
        
        return JsonResponse({
            'valid': True,
            'user': {
                'id': profile.id,
                'username': profile.user.username,
                'display_name': profile.display_name or profile.user.username,
                'email': profile.user.email,
                'avatar': profile.avatar.url if profile.avatar else None,
            },
            'reason': 'User found'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'reason': 'Invalid request'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'reason': str(e)}, status=500)
