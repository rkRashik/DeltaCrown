# apps/tournaments/views/registration_modern.py
"""
Modern Registration Views
Implements the new multi-step registration flow with auto-fill and validation
"""
from __future__ import annotations

import json
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from ..services.registration_service import RegistrationService
from ..services.approval_service import ApprovalService

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
RegistrationRequest = apps.get_model("tournaments", "RegistrationRequest")
UserProfile = apps.get_model("user_profile", "UserProfile")
Team = apps.get_model("teams", "Team")


@login_required
def modern_register_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Main registration view with V2 professional wizard form
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get registration context
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    # Check eligibility
    if not context.can_register:
        messages.error(request, context.error_message or "You cannot register for this tournament.")
        return redirect("tournaments:detail", slug=slug)
    
    # Get user profile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "Please complete your profile before registering.")
        return redirect("user_profile:profile")
    
    # Get game code for field configuration
    game_code = str(tournament.game).lower()
    
    # Get team data if team tournament
    user_team = None
    team_roster = []
    if context.is_team_event:
        # Get user's team FOR THIS SPECIFIC GAME
        from apps.teams.models import TeamMembership
        
        # Find teams where user is captain and team's game matches tournament game
        captain_memberships = TeamMembership.objects.filter(
            profile=profile,
            role='CAPTAIN',
            status='ACTIVE'
        ).select_related('team').all()
        
        # Filter for teams that match the tournament's game
        tournament_game = game_code  # Use already defined game_code
        
        for membership in captain_memberships:
            team_game = str(membership.team.game).lower() if hasattr(membership.team, 'game') else None
            if team_game == tournament_game:
                user_team = membership.team
                break
        
        if not user_team:
            messages.error(request, f"You must be a captain of a {tournament.game} team to register for this tournament.")
            return redirect("tournaments:detail", slug=slug)
        
        # Get team roster (all active members)
        roster_memberships = TeamMembership.objects.filter(
            team=user_team,
            status='ACTIVE'
        ).select_related('profile', 'profile__user').order_by('role', 'joined_at')
        
        # Format roster data for template/JavaScript
        for membership in roster_memberships:
            member_profile = membership.profile
            roster_member = {
                'profile_id': member_profile.id,
                'displayName': member_profile.display_name or member_profile.user.username,
                'role': membership.role,
                'isCaptain': membership.role == 'CAPTAIN',
            }
            
            # Add game-specific IDs
            if game_code == 'valorant':
                roster_member['riotId'] = getattr(member_profile, 'riot_id', '') or ""
                roster_member['discordId'] = getattr(member_profile, 'discord_id', '') or ""
            elif game_code in ['cs2', 'dota2']:
                roster_member['steamId'] = getattr(member_profile, 'steam_id', '') or ""
                roster_member['discordId'] = getattr(member_profile, 'discord_id', '') or ""
                if game_code == 'dota2':
                    roster_member['dotaFriendId'] = getattr(member_profile, 'dota_friend_id', '') or ""
            elif game_code == 'mlbb':
                roster_member['inGameName'] = getattr(member_profile, 'mlbb_ign', '') or ""
                roster_member['mlbbUserId'] = getattr(member_profile, 'mlbb_user_id', '') or ""
                roster_member['discordId'] = getattr(member_profile, 'discord_id', '') or ""
            elif game_code == 'pubg':
                roster_member['characterName'] = getattr(member_profile, 'pubg_character_name', '') or ""
                roster_member['pubgId'] = getattr(member_profile, 'pubg_id', '') or ""
                roster_member['discordId'] = getattr(member_profile, 'discord_id', '') or ""
            elif game_code == 'freefire':
                roster_member['inGameName'] = getattr(member_profile, 'freefire_ign', '') or ""
                roster_member['freeFireUid'] = getattr(member_profile, 'freefire_uid', '') or ""
                roster_member['discordId'] = getattr(member_profile, 'discord_id', '') or ""
            elif game_code == 'efootball':
                roster_member['efootballUsername'] = getattr(member_profile, 'efootball_username', '') or ""
                roster_member['efootballUserId'] = getattr(member_profile, 'efootball_user_id', '') or ""
            elif game_code == 'fc26':
                roster_member['platform'] = getattr(member_profile, 'fc26_platform', '') or ""
                roster_member['platformId'] = getattr(member_profile, 'fc26_platform_id', '') or ""
                roster_member['fc26Username'] = getattr(member_profile, 'fc26_username', '') or ""
            
            team_roster.append(roster_member)
    
    # Get profile data for auto-fill
    profile_data = {
        "displayName": profile.display_name or "",
        "email": request.user.email or "",
        "phone": getattr(profile, 'phone', '') or "",
        "discordId": getattr(profile, 'discord_id', '') or "",
    }
    
    # Get game-specific profile data if exists
    # game_code was already defined earlier for team tournaments
    if game_code == 'valorant':
        profile_data['riotId'] = getattr(profile, 'riot_id', '') or ""
    elif game_code in ['cs2', 'dota2']:
        profile_data['steamId'] = getattr(profile, 'steam_id', '') or ""
        if game_code == 'dota2':
            profile_data['dotaFriendId'] = getattr(profile, 'dota_friend_id', '') or ""
    elif game_code == 'mlbb':
        profile_data['inGameName'] = getattr(profile, 'mlbb_ign', '') or ""
        profile_data['mlbbUserId'] = getattr(profile, 'mlbb_user_id', '') or ""
    elif game_code == 'pubg':
        profile_data['characterName'] = getattr(profile, 'pubg_character_name', '') or ""
        profile_data['pubgId'] = getattr(profile, 'pubg_id', '') or ""
    elif game_code == 'freefire':
        profile_data['inGameName'] = getattr(profile, 'freefire_ign', '') or ""
        profile_data['freeFireUid'] = getattr(profile, 'freefire_uid', '') or ""
    elif game_code == 'efootball':
        profile_data['efootballUsername'] = getattr(profile, 'efootball_username', '') or ""
        profile_data['efootballUserId'] = getattr(profile, 'efootball_user_id', '') or ""
    elif game_code == 'fc26':
        profile_data['platform'] = getattr(profile, 'fc26_platform', '') or ""
        profile_data['platformId'] = getattr(profile, 'fc26_platform_id', '') or ""
        profile_data['fc26Username'] = getattr(profile, 'fc26_username', '') or ""
    
    # Prepare template context for V2
    template_context = {
        "tournament": tournament,
        "profile": profile,
        "user_team": user_team,
        "is_team_event": context.is_team_event,
        "profile_data": profile_data,  # Add profile data for auto-fill
        "team_roster": json.dumps(team_roster, cls=DjangoJSONEncoder),  # Serialize roster data as JSON
        "tournament_data": {
            "slug": tournament.slug,
            "name": tournament.name,
            "game": str(tournament.game),  # Convert to string (it's already a string, but ensure it)
            "isTeam": context.is_team_event,
            "isPaid": hasattr(tournament, 'entry_fee_bdt') and tournament.entry_fee_bdt and tournament.entry_fee_bdt > 0,
            "entryFee": getattr(tournament, 'entry_fee_bdt', 0) or 0,
            "minTeamSize": getattr(tournament, 'min_team_size', 5) if context.is_team_event else 1,
            "maxTeamSize": getattr(tournament, 'max_team_size', 7) if context.is_team_event else 1,
            "rules": tournament.rules if hasattr(tournament, 'rules') else "",
        }
    }
    
    # Use V2 template
    return render(request, "tournaments/registration_v2.html", template_context)


@login_required
@require_http_methods(["GET"])
def registration_context_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    API endpoint to get registration context including game configuration
    GET /api/tournaments/<slug>/register/context/
    
    Returns:
        - Registration context (eligibility, team info, etc.)
        - Game configuration (fields, roles, validation rules)
        - Pre-filled data from user profile
    """
    from apps.tournaments.services import GameConfigService
    
    tournament = get_object_or_404(Tournament, slug=slug)
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    # Get game configuration
    game_config = GameConfigService.get_full_config(tournament.game)
    
    # Get auto-fill data from user profile
    profile_data = RegistrationService.auto_fill_profile_data(request.user)
    
    # Get team data if applicable
    team_data = None
    if context.is_team_event and context.user_team:
        team_data = RegistrationService.auto_fill_team_data(context.user_team)
    
    return JsonResponse({
        "success": True,
        "context": context.to_dict(),
        "game_config": game_config,
        "profile_data": profile_data,
        "team_data": team_data
    })


@login_required
@require_POST
def validate_registration_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    API endpoint to validate registration data
    POST /api/tournaments/<slug>/register/validate/
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get data from POST
    data = request.POST.dict()
    
    # Validate
    is_valid, errors = RegistrationService.validate_registration_data(
        tournament, request.user, data
    )
    
    return JsonResponse({
        "success": is_valid,
        "errors": errors
    })


@login_required
@require_POST
def submit_registration_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    API endpoint to submit registration (V2 - JSON-based)
    POST /api/tournaments/<slug>/register/
    
    Expects JSON body:
    {
        "player_data": {...},
        "roster_data": [...] (team tournaments only),
        "save_to_profile": bool
    }
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    try:
        # Parse JSON body
        body = json.loads(request.body)
        player_data = body.get("player_data", {})
        roster_data = body.get("roster_data", [])
        save_to_profile = body.get("save_to_profile", False)
        
        # Get user profile
        profile = UserProfile.objects.get(user=request.user)
        
        # Get team if team tournament
        team = None
        if context.is_team_event:
            from apps.teams.models import TeamMembership
            captain_membership = TeamMembership.objects.filter(
                profile=profile,
                role='CAPTAIN',
                status='ACTIVE'
            ).select_related('team').first()
            
            if not captain_membership:
                return JsonResponse({
                    "success": False,
                    "errors": {"team": ["You must be a team captain to register for team tournaments."]}
                }, status=400)
            
            team = captain_membership.team
        
        # Create registration
        with transaction.atomic():
            registration = RegistrationService.create_registration(
                tournament=tournament,
                user=request.user,
                data=player_data,
                team=team
            )
            
            # Save roster data if team tournament
            if context.is_team_event and roster_data:
                # Store roster data in registration (you may need to extend Registration model)
                # For now, we'll store it as JSON in a field or related model
                pass
            
            # Update profile if requested
            if save_to_profile and player_data:
                # Update profile fields
                if 'displayName' in player_data:
                    profile.display_name = player_data['displayName']
                # Add more field mappings as needed
                profile.save()
        
        return JsonResponse({
            "success": True,
            "registration_id": registration.id,
            "message": "Registration submitted successfully",
            "redirect_url": reverse("tournaments:detail", kwargs={"slug": slug})
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            "success": False,
            "errors": {"user": ["Profile not found. Please complete your profile first."]}
        }, status=400)
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, "message_dict"):
            errors = e.message_dict
        else:
            errors = {"non_field_errors": [str(e)]}
            
        return JsonResponse({
            "success": False,
            "errors": errors
        }, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "errors": {"json": ["Invalid JSON data"]}
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)


@login_required
@require_POST
def request_approval_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    API endpoint for non-captain to request registration approval
    POST /api/tournaments/<slug>/request-approval/
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get user profile
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        # Get context to find team
        context = RegistrationService.get_registration_context(tournament, request.user)
        if not context.user_team:
            return JsonResponse({
                "success": False,
                "errors": {"team": ["You are not part of a team"]}
            }, status=400)
        
        # Get message
        message = request.POST.get("message", "").strip()
        
        # Create request
        approval_request = ApprovalService.create_request(
            requester=profile,
            tournament=tournament,
            team=context.user_team,
            message=message
        )
        
        return JsonResponse({
            "success": True,
            "request_id": approval_request.id,
            "message": f"Request sent to {context.user_team.captain.display_name if hasattr(context.user_team, 'captain') else 'team captain'}"
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, "message_dict"):
            errors = e.message_dict
        else:
            errors = {"non_field_errors": [str(e)]}
            
        return JsonResponse({
            "success": False,
            "errors": errors
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)


@login_required
@require_http_methods(["GET"])
def pending_requests_api(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to get pending approval requests for captain
    GET /api/registration-requests/pending/
    """
    try:
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        requests = ApprovalService.get_pending_for_captain(profile)
        
        data = []
        for req in requests:
            data.append({
                "id": req.id,
                "requester": {
                    "id": req.requester.id,
                    "display_name": req.requester.display_name,
                },
                "tournament": {
                    "id": req.tournament.id,
                    "name": req.tournament.name,
                    "slug": req.tournament.slug,
                },
                "team": {
                    "id": req.team.id,
                    "name": req.team.name,
                },
                "message": req.message,
                "created_at": req.created_at.isoformat(),
                "expires_at": req.expires_at.isoformat(),
            })
        
        return JsonResponse({
            "success": True,
            "requests": data
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)


@login_required
@require_POST
def approve_request_api(request: HttpRequest, request_id: int) -> JsonResponse:
    """
    API endpoint to approve a registration request
    POST /api/registration-requests/<id>/approve/
    """
    try:
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        approval_request = get_object_or_404(RegistrationRequest, id=request_id)
        response_message = request.POST.get("response_message", "").strip()
        
        registration = ApprovalService.approve_request(
            request=approval_request,
            captain=profile,
            response_message=response_message,
            auto_register=True
        )
        
        return JsonResponse({
            "success": True,
            "message": "Request approved and team registered",
            "registration_id": registration.id if registration else None
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, "message_dict"):
            errors = e.message_dict
        else:
            errors = {"non_field_errors": [str(e)]}
            
        return JsonResponse({
            "success": False,
            "errors": errors
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)


@login_required
@require_POST
def reject_request_api(request: HttpRequest, request_id: int) -> JsonResponse:
    """
    API endpoint to reject a registration request
    POST /api/registration-requests/<id>/reject/
    """
    try:
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        approval_request = get_object_or_404(RegistrationRequest, id=request_id)
        response_message = request.POST.get("response_message", "").strip()
        
        ApprovalService.reject_request(
            request=approval_request,
            captain=profile,
            response_message=response_message
        )
        
        return JsonResponse({
            "success": True,
            "message": "Request rejected"
        })
        
    except ValidationError as e:
        errors = {}
        if hasattr(e, "message_dict"):
            errors = e.message_dict
        else:
            errors = {"non_field_errors": [str(e)]}
            
        return JsonResponse({
            "success": False,
            "errors": errors
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)
