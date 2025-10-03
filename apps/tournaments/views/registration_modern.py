# apps/tournaments/views/registration_modern.py
"""
Modern Registration Views
Implements the new multi-step registration flow with auto-fill and validation
"""
from __future__ import annotations

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

from ..services.registration_service import RegistrationService
from ..services.approval_service import ApprovalService

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
RegistrationRequest = apps.get_model("tournaments", "RegistrationRequest")
UserProfile = apps.get_model("user_profile", "UserProfile")


@login_required
def modern_register_view(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Main registration view with multi-step form
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get registration context
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    # Get auto-fill data
    profile_data = RegistrationService.auto_fill_profile_data(request.user)
    team_data = {}
    if context.user_team:
        team_data = RegistrationService.auto_fill_team_data(context.user_team)
    
    # Handle form submission
    if request.method == "POST":
        try:
            # Collect form data
            data = {
                "display_name": request.POST.get("display_name", "").strip(),
                "email": request.POST.get("email", "").strip(),
                "phone": request.POST.get("phone", "").strip(),
                "in_game_id": request.POST.get("in_game_id", "").strip(),
                "in_game_username": request.POST.get("in_game_username", "").strip(),
                "discord_id": request.POST.get("discord_id", "").strip(),
                "payment_method": request.POST.get("payment_method", "").strip(),
                "payer_account_number": request.POST.get("payer_account_number", "").strip(),
                "payment_reference": request.POST.get("payment_reference", "").strip(),
                "agree_rules": request.POST.get("agree_rules") == "on",
            }
            
            # Create registration
            registration = RegistrationService.create_registration(
                tournament=tournament,
                user=request.user,
                data=data,
                team=context.user_team if context.is_team_event else None
            )
            
            messages.success(
                request,
                "Registration submitted successfully! We'll verify your payment and confirm shortly."
            )
            
            return redirect(reverse("tournaments:registration_receipt", kwargs={"slug": slug}))
            
        except ValidationError as e:
            # Show validation errors
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            else:
                messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    # Prepare template context
    template_context = {
        "tournament": tournament,
        "context": context,
        "profile_data": profile_data,
        "team_data": team_data,
        "entry_fee": getattr(tournament, "entry_fee_bdt", None) or getattr(tournament, "entry_fee", None),
    }
    
    return render(request, "tournaments/modern_register.html", template_context)


@login_required
@require_http_methods(["GET"])
def registration_context_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    API endpoint to get registration context
    GET /api/tournaments/<slug>/register/context/
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    return JsonResponse({
        "success": True,
        "context": context.to_dict()
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
    API endpoint to submit registration
    POST /api/tournaments/<slug>/register/submit/
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    context = RegistrationService.get_registration_context(tournament, request.user)
    
    try:
        data = request.POST.dict()
        
        registration = RegistrationService.create_registration(
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
