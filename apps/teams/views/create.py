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
from apps.notifications.services import notify


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
                invited_users = []
                try:
                    invites = json.loads(roster_data)
                    for invite_data in invites:
                        invited_user = _process_invite(team, request.user, invite_data)
                        if invited_user:
                            invited_users.append(invited_user)
                except json.JSONDecodeError:
                    pass  # Roster is optional
                
                # Send notification to team creator
                notify(
                    recipients=[request.user],
                    event='team_created',
                    title='Team Created Successfully!',
                    body=f'Your team "{team.name}" has been created. You can now invite members and participate in tournaments.',
                    url=f'/teams/{team.slug}/'
                )
                
                # Send notifications to invited users
                if invited_users:
                    notify(
                        recipients=invited_users,
                        event='team_invite',
                        title='Team Invitation',
                        body=f'You have been invited to join {team.name}. Check your invitations to accept or decline.',
                        url='/teams/invitations/'
                    )
                
                messages.success(
                    request,
                    f"🎉 Team '{team.name}' created successfully! Welcome to your new team."
                )
                return redirect("teams:dashboard", slug=team.slug)
            
            except Exception as e:
                messages.error(request, f"Error creating team: {str(e)}")
        else:
            # Display specific field errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"{error}")
                    else:
                        field_label = form.fields.get(field).label if field in form.fields else field
                        messages.error(request, f"{field_label}: {error}")
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
    """
    Process a single invite from the creation form.
    Returns the invited user if successful, None otherwise.
    """
    try:
        identifier = invite_data.get('identifier', '').strip()
        role = invite_data.get('role', 'PLAYER')
        message = invite_data.get('message', '')
        
        if not identifier:
            return None
        
        # Find user by username or email
        profile = None
        if '@' in identifier:
            # Email lookup
            try:
                profile = UserProfile.objects.select_related('user').get(user__email__iexact=identifier)
            except UserProfile.DoesNotExist:
                return None
        else:
            # Username lookup
            try:
                profile = UserProfile.objects.select_related('user').get(user__username__iexact=identifier)
            except UserProfile.DoesNotExist:
                return None
        
        # Check if already a member
        if TeamMembership.objects.filter(team=team, profile=profile, status='ACTIVE').exists():
            return None
        
        # Check if already invited
        if TeamInvite.objects.filter(team=team, invited_user=profile, status='PENDING').exists():
            return None
        
        # Create invite
        invite = TeamInvite.objects.create(
            team=team,
            invited_user=profile,
            role=role,
            message=message,
            inviter=sender_user
        )
        
        # Return the user for notification
        return profile.user
        
    except Exception:
        return None


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
@require_http_methods(["GET"])
def check_existing_team(request):
    """
    AJAX endpoint to check if user already has a team for the selected game.
    Returns: {
        "has_team": bool,
        "team": {...} (if has_team=true),
        "can_create": bool
    }
    """
    try:
        game = request.GET.get('game', '').strip()
        
        if not game:
            return JsonResponse({
                'error': 'Game code is required'
            }, status=400)
        
        profile = _ensure_profile(request.user)
        if not profile:
            return JsonResponse({
                'error': 'Profile not found'
            }, status=404)
        
        # Check if user has an active team for this game
        existing_membership = TeamMembership.objects.filter(
            profile=profile,
            status='ACTIVE',
            team__game=game
        ).select_related('team').first()
        
        if existing_membership:
            team = existing_membership.team
            return JsonResponse({
                'has_team': True,
                'can_create': False,
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'tag': team.tag,
                    'slug': team.slug,
                    'game': team.game,
                    'logo': team.logo.url if team.logo else None,
                    'role': existing_membership.role,
                    'is_captain': existing_membership.role == 'CAPTAIN',
                },
                'message': f'You are already a member of "{team.name}" ({team.tag}) for this game. You can only have one active team per game.'
            })
        
        return JsonResponse({
            'has_team': False,
            'can_create': True,
            'message': 'You can create a team for this game'
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def validate_user_identifier(request):
    """
    AJAX endpoint to validate username/email for invites.
    Returns: {"valid": bool, "user_info": {...}, "message": str}
    Privacy: Only returns basic info until invite is accepted
    """
    try:
        # Support both GET and POST
        if request.method == "GET":
            identifier = request.GET.get('identifier', '').strip()
        else:
            data = json.loads(request.body)
            identifier = data.get('identifier', '').strip()
        
        if not identifier:
            return JsonResponse({
                'valid': False,
                'message': 'Username or email is required'
            })
        
        profile = None
        
        # Try email first
        if '@' in identifier:
            try:
                profile = UserProfile.objects.select_related('user').get(user__email__iexact=identifier)
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'message': 'No user found with this email'
                })
        else:
            # Try username
            try:
                profile = UserProfile.objects.select_related('user').get(user__username__iexact=identifier)
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'message': 'No user found with this username'
                })
        
        # Check if trying to invite self
        if profile.user == request.user:
            return JsonResponse({
                'valid': False,
                'message': 'You cannot invite yourself'
            })
        
        # Return limited info for privacy (more info revealed after acceptance)
        return JsonResponse({
            'valid': True,
            'user_info': {
                'username': profile.user.username,
                'display_name': profile.display_name or profile.user.username,
                # Don't expose email or full profile until invitation accepted
            },
            'message': 'User found and can be invited'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid request'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)}, status=500)
