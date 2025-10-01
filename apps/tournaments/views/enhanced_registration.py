"""
Enhanced Tournament Registration Views
Handles both solo and team registrations with proper validation and email notifications
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.enhanced_registration import create_registration_with_email
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership

@login_required
def enhanced_register(request, slug):
    """
    Enhanced registration view that handles both solo and team tournaments
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    user = request.user
    
    # Get user profile
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(
            user=user,
            display_name=user.get_full_name() or user.username
        )
    
    # Check if already registered
    existing_registration = Registration.objects.filter(
        tournament=tournament,
        user=user_profile
    ).first()
    
    if existing_registration:
        messages.info(request, "You are already registered for this tournament!")
        return redirect('tournaments:detail', slug=tournament.slug)
    
    # Check registration window
    if not tournament.registration_open:
        messages.error(request, "Registration is not currently open for this tournament.")
        return redirect('tournaments:detail', slug=tournament.slug)
    
    # Determine if this is a team tournament
    is_team_tournament = _is_team_tournament(tournament)
    
    context = {
        'tournament': tournament,
        'user_profile': user_profile,
        'is_team_tournament': is_team_tournament,
        'entry_fee': tournament.entry_fee_bdt or 0,
        'prize_pool': tournament.prize_pool_bdt or 0,
    }
    
    if request.method == 'POST':
        return _handle_registration_submission(request, tournament, user_profile, is_team_tournament)
    
    # GET request - show registration form
    # Check for type parameter to override detection
    registration_type = request.GET.get('type', '')
    if registration_type == 'team':
        is_team_tournament = True
    elif registration_type == 'solo':
        is_team_tournament = False
    
    if is_team_tournament:
        # Get user's team for this game
        user_team, membership, is_captain = _get_user_team_for_game(user_profile, tournament.game)
        context.update({
            'user_team': user_team,
            'membership': membership,
            'is_captain': is_captain,
            'can_create_team': not user_team,
        })
        
        return render(request, 'tournaments/enhanced_team_register.html', context)
    else:
        return render(request, 'tournaments/enhanced_solo_register.html', context)

def _is_team_tournament(tournament):
    """Determine if tournament requires teams"""
    # Check various possible indicators
    if tournament.game == 'valorant':
        return True  # Valorant is typically team-based
    
    # Check tournament settings
    if hasattr(tournament, 'settings'):
        policy = getattr(tournament.settings, 'registration_policy', None)
        if policy and hasattr(policy, 'mode'):
            return policy.mode in ('team', 'duo')
    
    # Check for team-related fields
    team_indicators = ['team_size', 'min_team_size', 'max_team_size', 'team_mode']
    for indicator in team_indicators:
        if hasattr(tournament, indicator):
            value = getattr(tournament, indicator)
            if value and (isinstance(value, int) and value > 1 or 
                         isinstance(value, bool) and value):
                return True
    
    return False

def _get_user_team_for_game(user_profile, game):
    """Get user's team for specific game"""
    if not Team or not TeamMembership:
        return None, None, False
    
    try:
        membership = TeamMembership.objects.select_related('team').filter(
            profile=user_profile,
            status='ACTIVE',
            team__game=game
        ).first()
        
        if membership:
            return membership.team, membership, membership.role == 'CAPTAIN'
    except Exception:
        pass
    
    return None, None, False

@transaction.atomic
def _handle_registration_submission(request, tournament, user_profile, is_team_tournament):
    """Handle POST registration submission"""
    try:
        if is_team_tournament:
            return _handle_team_registration(request, tournament, user_profile)
        else:
            return _handle_solo_registration(request, tournament, user_profile)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('tournaments:register', slug=tournament.slug)
    except Exception as e:
        messages.error(request, f"Registration failed: {str(e)}")
        return redirect('tournaments:register', slug=tournament.slug)

def _handle_solo_registration(request, tournament, user_profile):
    """Handle solo player registration"""
    payment_method = request.POST.get('payment_method')
    payment_reference = request.POST.get('payment_reference')
    
    # Validate required game IDs
    game_id_field = f"{tournament.game}_id"
    game_id = request.POST.get(game_id_field)
    
    if not game_id:
        raise ValidationError(f"Please provide your {tournament.get_game_display()} ID")
    
    # Update user profile with game ID
    setattr(user_profile, game_id_field, game_id)
    user_profile.save()
    
    # Create registration
    registration = create_registration_with_email(
        tournament=tournament,
        user_profile=user_profile,
        payment_method=payment_method,
        payment_reference=payment_reference
    )
    
    messages.success(request, 
        f"Registration successful! Check your email for confirmation and payment instructions.")
    
    return redirect('tournaments:detail', slug=tournament.slug)

def _handle_team_registration(request, tournament, user_profile):
    """Handle team registration"""
    action = request.POST.get('action', 'register_existing')
    
    if action == 'create_team':
        return _handle_team_creation_and_registration(request, tournament, user_profile)
    else:
        return _handle_existing_team_registration(request, tournament, user_profile)

def _handle_existing_team_registration(request, tournament, user_profile):
    """Register existing team"""
    user_team, membership, is_captain = _get_user_team_for_game(user_profile, tournament.game)
    
    if not user_team:
        raise ValidationError("You don't belong to any team for this game")
    
    if not is_captain:
        raise ValidationError("Only team captains can register the team")
    
    # Check if team already registered
    existing_reg = Registration.objects.filter(tournament=tournament, team=user_team).first()
    if existing_reg:
        raise ValidationError("Your team is already registered for this tournament")
    
    payment_method = request.POST.get('payment_method')
    payment_reference = request.POST.get('payment_reference')
    
    # Create team registration
    registration = create_registration_with_email(
        tournament=tournament,
        team=user_team,
        payment_method=payment_method,
        payment_reference=payment_reference
    )
    
    messages.success(request, 
        f"Team registration successful! Check your email for confirmation and payment instructions.")
    
    return redirect('tournaments:detail', slug=tournament.slug)

def _handle_team_creation_and_registration(request, tournament, user_profile):
    """Create new team and register it"""
    team_name = request.POST.get('team_name', '').strip()
    if not team_name:
        raise ValidationError("Team name is required")
    
    # Check if user already has a team for this game
    user_team, _, _ = _get_user_team_for_game(user_profile, tournament.game)
    if user_team:
        raise ValidationError(f"You already belong to a team for {tournament.get_game_display()}")
    
    # Create team
    team = _create_team_for_user(user_profile, team_name, tournament.game)
    
    payment_method = request.POST.get('payment_method')
    payment_reference = request.POST.get('payment_reference')
    
    # Create team registration
    registration = create_registration_with_email(
        tournament=tournament,
        team=team,
        payment_method=payment_method,
        payment_reference=payment_reference
    )
    
    messages.success(request, 
        f"Team '{team_name}' created and registered successfully! Check your email for confirmation.")
    
    return redirect('tournaments:detail', slug=tournament.slug)

def _create_team_for_user(user_profile, team_name, game):
    """Create a new team with user as captain"""
    from django.utils.text import slugify
    import re
    
    # Generate unique tag
    tag = re.sub(r'[^A-Z0-9]', '', team_name.upper())[:5]
    if not tag:
        tag = "TEAM"
    
    # Ensure tag is unique
    base_tag = tag
    counter = 1
    while Team.objects.filter(tag=tag).exists():
        tag = f"{base_tag}{counter}"
        counter += 1
    
    # Create team
    team = Team.objects.create(
        name=team_name,
        tag=tag,
        captain=user_profile,
        game=game,
        slug=slugify(team_name)
    )
    
    # Create captain membership
    TeamMembership.objects.create(
        team=team,
        profile=user_profile,
        role='CAPTAIN',
        status='ACTIVE'
    )
    
    return team

@require_http_methods(["POST"])
@login_required  
def ajax_register(request, slug):
    """AJAX registration endpoint"""
    try:
        tournament = get_object_or_404(Tournament, slug=slug)
        user_profile = UserProfile.objects.get(user=request.user)
        
        is_team_tournament = _is_team_tournament(tournament)
        
        registration = _handle_registration_submission(request, tournament, user_profile, is_team_tournament)
        
        return JsonResponse({
            'success': True,
            'message': 'Registration successful!',
            'redirect_url': tournament.get_absolute_url()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)