# apps/tournaments/views/registration_phase2.py
"""
Phase 2: Enhanced Registration Views
Integrates Phase 1 models into registration workflow

Key Enhancements:
- Uses RegistrationServicePhase2 for all Phase 1 model integration
- Provides richer context with schedule, capacity, finance, rules, media data
- Backward compatible with existing registration templates
- Enhanced validation using Phase 1 model constraints
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.tournaments.models import Tournament, Registration, RegistrationRequest
from apps.tournaments.services.registration_service_phase2 import RegistrationServicePhase2
from apps.user_profile.models import UserProfile

# Import approval service (if available)
try:
    from apps.tournaments.services.approval_service import ApprovalService
except ImportError:
    ApprovalService = None


@login_required
@require_http_methods(["GET", "POST"])
def modern_register_view_phase2(request: HttpRequest, slug: str):
    """
    Enhanced registration view using Phase 1 models
    
    GET: Display registration form with Phase 1 context
    POST: Handle form submission (for non-AJAX)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get registration context with Phase 1 data
    context_obj = RegistrationServicePhase2.get_registration_context(tournament, request.user)
    
    # Build template context
    context = {
        "tournament": tournament,
        "registration_context": context_obj,
        "context": context_obj,  # Alias for backward compatibility
        
        # Phase 1 model data
        "schedule": context_obj.schedule_info,
        "capacity": context_obj.capacity_info,
        "finance": context_obj.finance_info,
        "rules": context_obj.rules_info,
        "media": context_obj.media_info,
        "archive": context_obj.archive_info,
        
        # Auto-fill data
        "profile_data": RegistrationServicePhase2.auto_fill_profile_data(request.user),
        "team_data": RegistrationServicePhase2.auto_fill_team_data(context_obj.user_team) if context_obj.user_team else {},
        
        # Requirements list for template
        "requirements": context_obj.rules_info.get("requirements_list", []),
        
        # Display flags
        "show_payment_section": not context_obj.finance_info.get("is_free", False),
        "show_team_section": context_obj.is_team_event,
        "show_discord_field": context_obj.rules_info.get("require_discord", False),
        "show_game_id_field": context_obj.rules_info.get("require_game_id", False),
        
        # Capacity display
        "slots_remaining": context_obj.capacity_info.get("available_slots", 0),
        "fill_percentage": context_obj.capacity_info.get("fill_percentage", 0),
        
        # Timing display
        "closes_in": context_obj.registration_closes_in,
        "days_until_start": context_obj.schedule_info.get("days_until_start"),
    }
    
    # Handle POST (non-AJAX form submission)
    if request.method == "POST":
        try:
            data = request.POST.dict()
            
            registration = RegistrationServicePhase2.create_registration_phase2(
                tournament=tournament,
                user=request.user,
                data=data,
                team=context_obj.user_team if context_obj.is_team_event else None
            )
            
            return redirect("tournaments:registration_receipt", slug=slug)
            
        except ValidationError as e:
            errors = {}
            if hasattr(e, "message_dict"):
                errors = e.message_dict
            else:
                errors = {"non_field_errors": [str(e)]}
            
            context["errors"] = errors
    
    return render(request, "tournaments/registration_modern.html", context)


@login_required
@require_http_methods(["GET"])
def registration_context_api_phase2(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Enhanced API endpoint to get registration context with Phase 1 data
    GET /api/tournaments/<slug>/registration-context/
    
    Returns comprehensive registration state including:
    - Button state and text
    - User/team eligibility
    - Schedule information
    - Capacity/slots
    - Finance/payment requirements
    - Rules/requirements
    - Media assets
    - Archive status
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        context = RegistrationServicePhase2.get_registration_context(tournament, request.user)
        
        # Add auto-fill data
        response_data = context.to_dict()
        response_data["profile_data"] = RegistrationServicePhase2.auto_fill_profile_data(request.user)
        
        if context.user_team:
            response_data["team_data"] = RegistrationServicePhase2.auto_fill_team_data(context.user_team)
        
        return JsonResponse({
            "success": True,
            "context": response_data
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "errors": {"non_field_errors": [str(e)]}
        }, status=500)


@login_required
@require_POST
def validate_registration_api_phase2(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Enhanced API endpoint to validate registration data using Phase 1 models
    POST /api/tournaments/<slug>/validate-registration/
    
    Validates against:
    - Schedule (timing constraints)
    - Capacity (slot availability)
    - Finance (payment requirements)
    - Rules (age, region, rank, Discord, game ID requirements)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get Phase 1 model info
        schedule_info = RegistrationServicePhase2._get_schedule_info(tournament)
        capacity_info = RegistrationServicePhase2._get_capacity_info(tournament)
        finance_info = RegistrationServicePhase2._get_finance_info(tournament)
        rules_info = RegistrationServicePhase2._get_rules_info(tournament)
        
        # Get form data
        data = request.POST.dict()
        
        # Validate
        is_valid, errors = RegistrationServicePhase2.validate_registration_data_phase2(
            tournament=tournament,
            user=request.user,
            data=data,
            schedule_info=schedule_info,
            capacity_info=capacity_info,
            finance_info=finance_info,
            rules_info=rules_info,
        )
        
        if is_valid:
            return JsonResponse({
                "success": True,
                "message": "Validation passed"
            })
        else:
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
def submit_registration_api_phase2(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Enhanced API endpoint to submit registration using Phase 1 models
    POST /api/tournaments/<slug>/submit-registration/
    
    Automatically:
    - Updates TournamentCapacity.current_teams
    - Records payment in TournamentFinance
    - Validates against all Phase 1 model constraints
    - Sends notifications
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get registration context
        context = RegistrationServicePhase2.get_registration_context(tournament, request.user)
        
        # Get form data
        data = request.POST.dict()
        
        # Create registration (with Phase 1 integration)
        registration = RegistrationServicePhase2.create_registration_phase2(
            tournament=tournament,
            user=request.user,
            data=data,
            team=context.user_team if context.is_team_event else None
        )
        
        return JsonResponse({
            "success": True,
            "registration_id": registration.id,
            "message": "Registration submitted successfully",
            "redirect_url": reverse("tournaments:registration_receipt", kwargs={"slug": slug})
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


# ============================================================================
# APPROVAL WORKFLOW VIEWS (Phase 2 Compatible)
# ============================================================================

@login_required
@require_POST
def request_approval_api_phase2(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Enhanced API endpoint for non-captain to request registration approval
    POST /api/tournaments/<slug>/request-approval/
    
    Uses Phase 1 context to determine eligibility
    """
    if not ApprovalService:
        return JsonResponse({
            "success": False,
            "errors": {"_system": ["Approval service not available"]}
        }, status=500)
    
    tournament = get_object_or_404(Tournament, slug=slug)
    
    try:
        # Get user profile
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        # Get context using Phase 2 service
        context = RegistrationServicePhase2.get_registration_context(tournament, request.user)
        if not context.user_team:
            return JsonResponse({
                "success": False,
                "errors": {"team": ["You are not part of a team"]}
            }, status=400)
        
        # Check if registration is open (Phase 1 validation)
        if not context.schedule_info.get("is_registration_open"):
            return JsonResponse({
                "success": False,
                "errors": {"_timing": ["Registration is not currently open"]}
            }, status=400)
        
        # Check if tournament is full
        if context.capacity_info.get("is_full"):
            return JsonResponse({
                "success": False,
                "errors": {"_capacity": ["Tournament is full"]}
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
        
        captain_name = context.user_team.captain.display_name if hasattr(context.user_team, 'captain') else 'team captain'
        
        return JsonResponse({
            "success": True,
            "request_id": approval_request.id,
            "message": f"Request sent to {captain_name}"
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
def pending_requests_api_phase2(request: HttpRequest) -> JsonResponse:
    """
    Enhanced API endpoint to get pending approval requests for captain
    GET /api/registration-requests/pending/
    
    Includes Phase 1 context for each tournament
    """
    if not ApprovalService:
        return JsonResponse({
            "success": False,
            "errors": {"_system": ["Approval service not available"]}
        }, status=500)
    
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
            # Get Phase 1 context for the tournament
            schedule_info = RegistrationServicePhase2._get_schedule_info(req.tournament)
            capacity_info = RegistrationServicePhase2._get_capacity_info(req.tournament)
            
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
                # Phase 1 context
                "tournament_status": {
                    "is_registration_open": schedule_info.get("is_registration_open", False),
                    "is_full": capacity_info.get("is_full", False),
                    "slots_available": capacity_info.get("available_slots", 0),
                },
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
def approve_request_api_phase2(request: HttpRequest, request_id: int) -> JsonResponse:
    """
    Enhanced API endpoint to approve a registration request
    POST /api/registration-requests/<id>/approve/
    
    Automatically updates Phase 1 capacity and finance models
    """
    if not ApprovalService:
        return JsonResponse({
            "success": False,
            "errors": {"_system": ["Approval service not available"]}
        }, status=500)
    
    try:
        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile:
            return JsonResponse({
                "success": False,
                "errors": {"user": ["Profile not found"]}
            }, status=400)
        
        approval_request = get_object_or_404(RegistrationRequest, id=request_id)
        response_message = request.POST.get("response_message", "").strip()
        
        # Check Phase 1 constraints before approving
        schedule_info = RegistrationServicePhase2._get_schedule_info(approval_request.tournament)
        capacity_info = RegistrationServicePhase2._get_capacity_info(approval_request.tournament)
        
        if not schedule_info.get("is_registration_open"):
            return JsonResponse({
                "success": False,
                "errors": {"_timing": ["Registration is no longer open"]}
            }, status=400)
        
        if capacity_info.get("is_full"):
            return JsonResponse({
                "success": False,
                "errors": {"_capacity": ["Tournament is now full"]}
            }, status=400)
        
        # Approve and auto-register
        registration = ApprovalService.approve_request(
            request=approval_request,
            captain=profile,
            response_message=response_message,
            auto_register=True
        )
        
        # Update Phase 1 capacity
        if capacity_info.get("has_phase1"):
            try:
                from apps.tournaments.models_phase1 import TournamentCapacity
                capacity = TournamentCapacity.objects.filter(tournament=approval_request.tournament).first()
                if capacity:
                    capacity.increment_teams()
            except Exception:
                pass
        
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
def reject_request_api_phase2(request: HttpRequest, request_id: int) -> JsonResponse:
    """
    API endpoint to reject a registration request
    POST /api/registration-requests/<id>/reject/
    """
    if not ApprovalService:
        return JsonResponse({
            "success": False,
            "errors": {"_system": ["Approval service not available"]}
        }, status=500)
    
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
