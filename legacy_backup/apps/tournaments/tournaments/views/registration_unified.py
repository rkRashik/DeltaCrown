# apps/tournaments/views/registration_unified.py
"""
Unified tournament registration system implementing the revised flow:
1. Authentication check -> redirect to login if not authenticated
2. Tournament type determination (1v1 vs team)
3. Team membership checks and status validation
4. Dynamic form generation based on organizer requirements
5. Team creation functionality during registration
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.exceptions import ValidationError

from .helpers import read_title, read_fee_amount, coin_policy_of, rules_pdf_of, maybe_text

# Use service for creating registrations + emails
try:
    from apps.tournaments.services.enhanced_registration import create_registration_with_email
except Exception:  # pragma: no cover
    create_registration_with_email = None

# Use service for registration requests
try:
    from apps.tournaments.services.registration_request import create_registration_request
except Exception:  # pragma: no cover
    create_registration_request = None

# Use service for registration requests
try:
    from apps.tournaments.services.registration_request import create_registration_request
except Exception:  # pragma: no cover
    create_registration_request = None

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")

def _get_model(app_label: str, name: str):
    try:
        return apps.get_model(app_label, name)
    except Exception:
        return None

Team = _get_model("tournaments", "Team") or _get_model("teams", "Team")
TeamMembership = _get_model("tournaments", "TeamMembership") or _get_model("teams", "TeamMembership")
UserProfile = _get_model("user_profile", "UserProfile")
PaymentVerification = _get_model("tournaments", "PaymentVerification")


def _get_user_profile(user):
    """Get or create user profile for the authenticated user."""
    if not getattr(user, "is_authenticated", False):
        return None
    
    if UserProfile:
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(
                user=user,
                display_name=getattr(user, "get_full_name", lambda: "")() or user.username or ""
            )
        return profile
    return None


def _get_user_team(user) -> Tuple[Optional[Any], Optional[Any], bool]:
    """
    Return (team, membership, is_captain) for the current user.
    Uses the teams app's model structure with UserProfile references.
    """
    if not Team or not TeamMembership or not getattr(user, "is_authenticated", False):
        return None, None, False
    
    try:
        profile = _get_user_profile(user)
        if not profile:
            return None, None, False
            
        # Find active membership (prefer captain role)
        memberships = TeamMembership.objects.select_related("team").filter(
            profile=profile,
            status="ACTIVE"
        ).order_by(
            # Captain first, then by join date
            "-role",  # CAPTAIN sorts before PLAYER 
            "joined_at"
        )
        
        membership = memberships.first()
        if membership:
            is_captain = membership.role == "CAPTAIN"
            return membership.team, membership, is_captain
            
    except Exception:
        pass
    
    return None, None, False


def _is_team_tournament(tournament) -> bool:
    """
    Determine if this tournament requires teams based on various possible fields.
    """
    # Check registration policy first
    policy = getattr(tournament, "registration_policy", None)
    if policy:
        mode = getattr(policy, "mode", "").lower()
        if mode in ("team", "duo"):
            return True
        if mode == "solo":
            return False
    
    # Fallback to tournament-level attributes
    for attr in ("is_team_event", "team_mode"):
        if hasattr(tournament, attr) and getattr(tournament, attr):
            return True
    
    # Check team size requirements
    for attr in ("team_size_min", "min_team_size"):
        if hasattr(tournament, attr):
            min_size = getattr(tournament, attr) or 0
            if min_size > 1:
                return True
    
    return False


def _check_team_registration_status(tournament, team) -> str:
    """
    Check if team is already registered for tournament.
    Returns: "registered", "not_registered", or "error"
    """
    if not team:
        return "not_registered"
    
    try:
        if Registration.objects.filter(tournament=tournament, team=team).exists():
            return "registered"
        return "not_registered"
    except Exception:
        return "error"


def _get_organizer_fields(tournament) -> Dict[str, Any]:
    """
    Extract organizer-defined custom fields from tournament settings.
    Returns configuration for dynamic form generation.
    """
    settings = getattr(tournament, "settings", None)
    if not settings:
        return {}
    
    fields_config = {
        "require_in_game_id": getattr(settings, "require_in_game_id", False),
        "require_team_logo": getattr(settings, "require_team_logo", False),
        "require_screenshot": getattr(settings, "require_screenshot", False),
        "require_agreement": getattr(settings, "require_agreement", True),
        "custom_questions": getattr(settings, "custom_questions", ""),
    }
    
    return fields_config


def _get_tournament_rules(tournament) -> Dict[str, Any]:
    """
    Extract tournament rules, additional text, and PDF files.
    """
    # Get rules text from various possible sources
    rules_text = maybe_text(
        getattr(tournament, "rules_text", None),
        getattr(tournament, "rules_html", None),
        getattr(getattr(tournament, "settings", None), "rules_text", None),
        getattr(getattr(tournament, "settings", None), "rules_html", None)
    )
    
    # Get additional rules
    extra_rules = maybe_text(
        getattr(tournament, "additional_rules", None),
        getattr(getattr(tournament, "settings", None), "additional_rules", None)
    )
    
    # Get PDF rules
    rules_pdf_url, rules_pdf_filename = rules_pdf_of(tournament)
    
    return {
        "rules_text": rules_text,
        "extra_rules": extra_rules,
        "rules_pdf_url": rules_pdf_url,
        "rules_pdf_filename": rules_pdf_filename,
        "has_rules": bool(rules_text or extra_rules or rules_pdf_url)
    }


def _get_payment_config(tournament) -> Dict[str, Any]:
    """
    Get payment configuration from tournament settings.
    """
    settings = getattr(tournament, "settings", None)
    if not settings:
        return {}
    
    def _safe_str(val):
        return str(val) if val is not None else None
    
    return {
        "bkash": _safe_str(getattr(settings, "bkash_receive_number", None)),
        "nagad": _safe_str(getattr(settings, "nagad_receive_number", None)),
        "rocket": _safe_str(getattr(settings, "rocket_receive_number", None)),
        "bank": _safe_str(getattr(settings, "bank_instructions", None)),
    }


def _create_team_for_user(user, team_name: str, team_logo=None, game: str = "") -> Any:
    """
    Create a new team with the user as captain.
    Returns the created team.
    """
    if not Team or not TeamMembership:
        raise ValidationError("Team creation not available")
    
    profile = _get_user_profile(user)
    if not profile:
        raise ValidationError("User profile required")
    
    # Check if user already has a team for this game
    existing_membership = TeamMembership.objects.filter(
        profile=profile,
        status="ACTIVE",
        team__game=game
    ).first()
    
    if existing_membership:
        raise ValidationError(f"You already belong to a team for {game}")
    
    # Generate unique tag from team name
    import re
    from django.utils.text import slugify
    
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
    team_data = {
        "name": team_name,
        "tag": tag,
        "captain": profile,
        "game": game,
        "slug": slugify(team_name),
    }
    
    if team_logo:
        team_data["logo"] = team_logo
    
    team = Team.objects.create(**team_data)
    
    # Create captain membership
    TeamMembership.objects.create(
        team=team,
        profile=profile,
        role="CAPTAIN",
        status="ACTIVE"
    )
    
    return team


def _process_registration(request, tournament, user_data: dict, team=None) -> Any:
    """
    Process the actual registration based on tournament type and user data.
    """
    profile = _get_user_profile(request.user)
    if not profile:
        raise ValidationError("User profile required")
    
    # Check if already registered
    existing_reg = None
    if team:
        existing_reg = Registration.objects.filter(tournament=tournament, team=team).first()
    else:
        existing_reg = Registration.objects.filter(tournament=tournament, user=profile).first()
    
    if existing_reg:
        raise ValidationError("Already registered for this tournament")
    
    # Create registration - note Registration.user field expects UserProfile, not User
    reg_data = {
        "tournament": tournament,
        "status": "PENDING"  # Match the model's status choices
    }
    
    if team:
        reg_data["team"] = team
    else:
        reg_data["user"] = profile  # Use UserProfile, not User
    
    # Add payment fields that exist on Registration model
    if user_data.get("payment_method"):
        reg_data["payment_method"] = user_data["payment_method"]
    if user_data.get("payment_reference"):
        reg_data["payment_reference"] = user_data["payment_reference"]
    if user_data.get("payer_account_number"):
        reg_data["payment_sender"] = user_data["payer_account_number"]
    
    registration = Registration.objects.create(**reg_data)
    
    # Handle PaymentVerification if separate model exists
    entry_fee = read_fee_amount(tournament)
    if entry_fee and entry_fee > 0 and PaymentVerification:
        # Generate a unique reference number for tracking
        import uuid
        reference_number = f"REG-{tournament.slug.upper()}-{uuid.uuid4().hex[:8].upper()}"
        
        # Use correct field names from PaymentVerification model
        pv_data = {
            "registration": registration,
            "method": user_data.get("payment_method", "bkash"),
            "payer_account_number": user_data.get("payer_account_number", ""),
            "transaction_id": user_data.get("payment_reference", ""),
            "amount_bdt": entry_fee,
            "status": PaymentVerification.Status.PENDING,
            "note": f"Registration for {tournament.name}"
        }
        
        # Add reference_number only if the field exists (for compatibility)
        if hasattr(PaymentVerification, '_meta') and any(f.name == 'reference_number' for f in PaymentVerification._meta.fields):
            pv_data["reference_number"] = reference_number
        
        PaymentVerification.objects.create(**pv_data)
    
    return registration


@login_required(login_url="/accounts/login/")
def valorant_register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Specialized Valorant tournament registration view with team management.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Basic tournament info
    title = read_title(tournament)
    entry_fee = read_fee_amount(tournament)
    is_team_tournament = True  # Valorant is always team-based
    
    # Get organizer configuration
    payment_config = _get_payment_config(tournament)
    tournament_rules = _get_tournament_rules(tournament)
    
    # Check if user has an existing Valorant team (use UserProfile-based membership)
    user_team = None
    is_captain = False
    team_members = []
    profile = _get_user_profile(request.user)
    if Team and TeamMembership and profile:
        try:
            membership = TeamMembership.objects.select_related("team").filter(
                profile=profile,
                status="ACTIVE",
                team__game="valorant",
            ).first()
            if membership:
                user_team = membership.team
                is_captain = getattr(membership, "role", "").upper() == "CAPTAIN"
                # Gather members with full details
                for mem in TeamMembership.objects.select_related("profile__user").filter(team=user_team, status="ACTIVE").order_by("-role", "joined_at"):
                    u = getattr(mem.profile, "user", None)
                    p = getattr(mem, "profile", None)
                    full_name = (getattr(u, "get_full_name", lambda: "")() or getattr(u, "username", "")).strip() if u else ""
                    email = getattr(u, "email", "") if u else ""
                    team_members.append({
                        "name": full_name,
                        "email": email,
                        "riot_id": getattr(p, "riot_id", "") if p else "",
                        "discord_id": getattr(p, "discord_id", "") if p else "",
                        "phone": getattr(p, "phone", "") if p else "",
                        "country": getattr(p, "country", "") if p else "",
                        "is_captain": getattr(mem, "role", "").upper() == "CAPTAIN",
                    })
        except Exception:
            pass
    
    # Prefill from profile/user
    prefill = {
        "full_name": (getattr(request.user, "get_full_name", lambda: "")() or getattr(request.user, "username", "")).strip(),
        "email": getattr(request.user, "email", "") or "",
        "discord_id": getattr(profile, "discord_id", "") if profile else "",
        "riot_id": getattr(profile, "riot_id", "") if profile else "",
    }

    # Check for existing registration or pending request
    already_registered = False
    pending_request = None
    if user_team:
        from apps.tournaments.models import Registration, RegistrationRequest
        already_registered = Registration.objects.filter(tournament=tournament, team=user_team).exists()
        if not already_registered and not is_captain:
            pending_request = RegistrationRequest.objects.filter(
                tournament=tournament,
                team=user_team,
                requester=profile,
                status=RegistrationRequest.Status.PENDING
            ).first()

    context = {
        "tournament": tournament,
        "title": title,
        "entry_fee": entry_fee,
        "payment_config": payment_config,
        "tournament_rules": tournament_rules,
        "user_team": user_team,
        "team_members": team_members,
        "prefill": prefill,
        "lock_email": True,
        "is_captain": is_captain,
        "already_registered": already_registered,
        "pending_request": pending_request,
    }
    
    # Handle form submission
    if request.method == "POST":
        # Honeypot protection
        if request.POST.get("website", "").strip():
            return redirect(reverse("tournaments:valorant_register", kwargs={"slug": slug}))
        
        # Handle non-captain request for approval
        if request.POST.get("action") == "request_approval" and user_team and not is_captain:
            try:
                if create_registration_request:
                    request_message = request.POST.get("request_message", "").strip()
                    create_registration_request(
                        requester=profile,
                        tournament=tournament,
                        team=user_team,
                        message=request_message or "Please approve registration for this tournament."
                    )
                    messages.success(
                        request,
                        "Your request has been sent to your team captain. You will be notified when they respond."
                    )
                else:
                    messages.error(request, "Request feature is not available.")
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Failed to send request: {str(e)}")
            return redirect(reverse("tournaments:valorant_register", kwargs={"slug": slug}))
        
        try:
            with transaction.atomic():
                # Extract team data
                team_data = {
                    "team_name": request.POST.get("team_name", "").strip(),
                    "team_tag": request.POST.get("team_tag", "").strip(),
                    "team_logo": request.FILES.get("team_logo"),
                }
                
                # Extract captain data
                captain_data = {
                    "full_name": request.POST.get("captain_full_name", "").strip(),
                    "email": request.POST.get("captain_email", "").strip(),
                    "riot_id": request.POST.get("captain_riot_id", "").strip(),
                    "discord": request.POST.get("captain_discord", "").strip(),
                    "phone": request.POST.get("captain_phone", "").strip(),
                    "country": request.POST.get("captain_country", "").strip(),
                }
                
                # Extract player data
                players_data = []
                for i in range(1, 8):  # Support up to 7 players
                    name = request.POST.get(f"player_{i}_name", "").strip()
                    if name:  # Only process if name is provided
                        players_data.append({
                            "name": name,
                            "riot_id": request.POST.get(f"player_{i}_riot_id", "").strip(),
                            "discord": request.POST.get(f"player_{i}_discord", "").strip(),
                            "email": request.POST.get(f"player_{i}_email", "").strip(),
                            "phone": request.POST.get(f"player_{i}_phone", "").strip(),
                            "country": request.POST.get(f"player_{i}_country", "").strip(),
                            "is_captain": i == 1,  # First player is captain
                        })
                
                # Payment data
                payment_data = {}
                if entry_fee and entry_fee > 0:
                    payment_data = {
                        "payment_method": request.POST.get("payment_method", "").strip(),
                        "payment_reference": request.POST.get("payment_reference", "").strip(),
                        "payer_account_number": request.POST.get("payer_account_number", "").strip(),
                    }
                
                # Validate data
                if not team_data["team_name"]:
                    raise ValidationError("Team name is required")
                
                if len(players_data) < 2:
                    raise ValidationError("At least 2 players are required (captain + 1 player)")
                
                if len(players_data) > 7:
                    raise ValidationError("Maximum 7 players allowed (5 main + 2 substitutes)")
                
                # Validate required fields for each player
                for i, player in enumerate(players_data, 1):
                    if not player["name"]:
                        raise ValidationError(f"Player {i} name is required")
                    if not player["riot_id"]:
                        raise ValidationError(f"Player {i} Riot ID is required")
                    if not player["discord"]:
                        raise ValidationError(f"Player {i} Discord ID is required")
                    if not player["email"]:
                        raise ValidationError(f"Player {i} email is required")
                    if not player["country"]:
                        raise ValidationError(f"Player {i} country is required")
                
                # Validate captain data
                if not captain_data["full_name"]:
                    raise ValidationError("Captain full name is required")
                if not captain_data["email"]:
                    raise ValidationError("Captain email is required")
                if not captain_data["riot_id"]:
                    raise ValidationError("Captain Riot ID is required")
                if not captain_data["discord"]:
                    raise ValidationError("Captain Discord ID is required")
                if not captain_data["country"]:
                    raise ValidationError("Captain country is required")
                
                # Validate agreements
                if tournament_rules["has_rules"]:
                    if not request.POST.get("agree_rules") == "on":
                        raise ValidationError("You must agree to the tournament rules")
                
                if not request.POST.get("agree_anticheat") == "on":
                    raise ValidationError("You must agree to anti-cheat measures")
                
                if not request.POST.get("agree_visibility") == "on":
                    raise ValidationError("You must agree to visibility settings")
                
                if not request.POST.get("agree_communication") == "on":
                    raise ValidationError("You must agree to receive communications")
                
                if not request.POST.get("confirm_accuracy") == "on":
                    raise ValidationError("You must confirm information accuracy")
                
                if entry_fee and entry_fee > 0:
                    if not request.POST.get("agree_payment") == "on":
                        raise ValidationError("You must agree to pay the entry fee")
                    
                    if not payment_data["payment_method"]:
                        raise ValidationError("Payment method is required")
                    if not payment_data["payment_reference"]:
                        raise ValidationError("Transaction ID is required")
                    if not payment_data["payer_account_number"]:
                        raise ValidationError("Account number is required")
                
                # Captain-only registration when a team exists
                if user_team and not is_captain:
                    raise ValidationError("Only the team captain can register the team")

                # Handle team creation/saving using UserProfile-based helpers
                save_team = request.POST.get("save_team") == "on"
                team = user_team
                if not team:
                    if not save_team:
                        # For Valorant, we require a real team (enforced by signals); create one
                        team = _create_team_for_user(request.user, team_data["team_name"], team_data.get("team_logo"), game="valorant")
                        # Optional: set tag/logo
                        if team and team_data.get("team_tag"):
                            team.tag = team_data["team_tag"]
                            team.save(update_fields=["tag"])            
                    else:
                        team = _create_team_for_user(request.user, team_data["team_name"], team_data.get("team_logo"), game="valorant")
                
                # Create registration via service (ensures email + payment verification)
                if create_registration_with_email:
                    registration = create_registration_with_email(
                        tournament=tournament,
                        team=team,
                        payment_method=payment_data.get("payment_method"),
                        payment_reference=payment_data.get("payment_reference"),
                    )
                else:
                    registration = Registration.objects.create(tournament=tournament, team=team, status="PENDING")
                
                # Store additional Valorant-specific data in registration notes or custom fields
                valorant_data = {
                    "team_tag": team_data["team_tag"],
                    "captain_discord": captain_data["discord"],
                    "players": players_data,
                }
                
                # Store as JSON in notes field if available
                if hasattr(registration, 'notes'):
                    import json
                    registration.notes = json.dumps(valorant_data)
                    registration.save()
                
                # Handle PaymentVerification
                if entry_fee and entry_fee > 0 and PaymentVerification:
                    import uuid
                    reference_number = f"VLR-{tournament.slug.upper()}-{uuid.uuid4().hex[:8].upper()}"
                    
                    pv_data = {
                        "registration": registration,
                        "method": payment_data["payment_method"],
                        "payer_account_number": payment_data["payer_account_number"],
                        "transaction_id": payment_data["payment_reference"],
                        "amount_bdt": entry_fee,
                        "status": PaymentVerification.Status.PENDING,
                        "note": f"Valorant team {team_data['team_name']} registration"
                    }
                    
                    if hasattr(PaymentVerification, '_meta') and any(f.name == 'reference_number' for f in PaymentVerification._meta.fields):
                        pv_data["reference_number"] = reference_number
                    
                    PaymentVerification.objects.create(**pv_data)
                
                messages.success(
                    request,
                    f"🎮 Successfully registered team '{team_data['team_name']}' for {tournament.name}! "
                    f"Registration confirmation will be sent to {captain_data['email']} within 24 hours."
                )
                
                return redirect(reverse("tournaments:detail", kwargs={"slug": slug}))
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    return render(request, "tournaments/valorant_register.html", context)


@login_required(login_url="/accounts/login/")
def efootball_register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Specialized eFootball tournament registration view with 2-player team management.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Basic tournament info
    title = read_title(tournament)
    entry_fee = read_fee_amount(tournament)
    is_team_tournament = True  # eFootball is always team-based (2-player)
    
    # Get organizer configuration
    payment_config = _get_payment_config(tournament)
    tournament_rules = _get_tournament_rules(tournament)
    
    # Check if user has an existing eFootball team for this game (UserProfile-based)
    user_team = None
    is_captain = False
    team_members = []
    profile = _get_user_profile(request.user)
    if Team and TeamMembership and profile:
        try:
            membership = TeamMembership.objects.select_related("team").filter(
                profile=profile,
                status="ACTIVE",
                team__game="efootball",
            ).first()
            if membership:
                user_team = membership.team
                is_captain = getattr(membership, "role", "").upper() == "CAPTAIN"
                for mem in TeamMembership.objects.select_related("profile__user").filter(team=user_team, status="ACTIVE").order_by("-role", "joined_at"):
                    u = getattr(mem.profile, "user", None)
                    p = getattr(mem, "profile", None)
                    full_name = (getattr(u, "get_full_name", lambda: "")() or getattr(u, "username", "")).strip() if u else ""
                    email = getattr(u, "email", "") if u else ""
                    team_members.append({
                        "name": full_name,
                        "email": email,
                        "efootball_id": getattr(p, "efootball_id", "") if p else "",
                        "discord_id": getattr(p, "discord_id", "") if p else "",
                        "phone": getattr(p, "phone", "") if p else "",
                        "country": getattr(p, "country", "") if p else "",
                        "is_captain": getattr(mem, "role", "").upper() == "CAPTAIN",
                    })
        except Exception:
            pass
    
    # Prefill from profile/user
    prefill = {
        "full_name": (getattr(request.user, "get_full_name", lambda: "")() or getattr(request.user, "username", "")).strip(),
        "email": getattr(request.user, "email", "") or "",
        "discord_id": getattr(profile, "discord_id", "") if profile else "",
        "efootball_id": getattr(profile, "efootball_id", "") if profile else "",
    }

    # Check for existing registration or pending request
    already_registered = False
    pending_request = None
    if user_team:
        from apps.tournaments.models import Registration, RegistrationRequest
        already_registered = Registration.objects.filter(tournament=tournament, team=user_team).exists()
        if not already_registered and not is_captain:
            pending_request = RegistrationRequest.objects.filter(
                tournament=tournament,
                team=user_team,
                requester=profile,
                status=RegistrationRequest.Status.PENDING
            ).first()
    
    context = {
        "tournament": tournament,
        "title": title,
        "entry_fee": entry_fee,
        "payment_config": payment_config,
        "tournament_rules": tournament_rules,
        "user_team": user_team,
        "team_members": team_members,
        "prefill": prefill,
        "lock_email": True,
        "is_captain": is_captain,
        "already_registered": already_registered,
        "pending_request": pending_request,
    }
    
    # Handle form submission
    if request.method == "POST":
        # Honeypot protection
        if request.POST.get("website", "").strip():
            return redirect(reverse("tournaments:efootball_register", kwargs={"slug": slug}))
        
        # Handle non-captain request for approval
        if request.POST.get("action") == "request_approval" and user_team and not is_captain:
            try:
                if create_registration_request:
                    request_message = request.POST.get("request_message", "").strip()
                    create_registration_request(
                        requester=profile,
                        tournament=tournament,
                        team=user_team,
                        message=request_message or "Please approve registration for this tournament."
                    )
                    messages.success(
                        request,
                        "Your request has been sent to your team captain. You will be notified when they respond."
                    )
                else:
                    messages.error(request, "Request feature is not available.")
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Failed to send request: {str(e)}")
            return redirect(reverse("tournaments:efootball_register", kwargs={"slug": slug}))
        
        try:
            with transaction.atomic():
                # Extract team data
                team_data = {
                    "team_name": request.POST.get("team_name", "").strip(),
                    "team_tag": request.POST.get("team_tag", "").strip(),
                    "team_logo": request.FILES.get("team_logo"),
                }
                
                # Extract captain data
                captain_data = {
                    "full_name": request.POST.get("captain_full_name", "").strip(),
                    "email": request.POST.get("captain_email", "").strip(),
                    "efootball_id": request.POST.get("captain_efootball_id", "").strip(),
                    "discord": request.POST.get("captain_discord", "").strip(),
                    "phone": request.POST.get("captain_phone", "").strip(),
                    "country": request.POST.get("captain_country", "").strip(),
                }
                
                # Extract player data (exactly 2 players for eFootball)
                players_data = []
                for i in range(1, 3):  # Only 2 players for eFootball
                    name = request.POST.get(f"player_{i}_name", "").strip()
                    if name:
                        players_data.append({
                            "name": name,
                            "efootball_id": request.POST.get(f"player_{i}_efootball_id", "").strip(),
                            "discord": request.POST.get(f"player_{i}_discord", "").strip(),
                            "email": request.POST.get(f"player_{i}_email", "").strip(),
                            "phone": request.POST.get(f"player_{i}_phone", "").strip(),
                            "country": request.POST.get(f"player_{i}_country", "").strip(),
                            "is_captain": i == 1,  # First player is captain
                        })
                
                # Payment data
                payment_data = {}
                if entry_fee and entry_fee > 0:
                    payment_data = {
                        "payment_method": request.POST.get("payment_method", "").strip(),
                        "payment_reference": request.POST.get("payment_reference", "").strip(),
                        "payer_account_number": request.POST.get("payer_account_number", "").strip(),
                    }
                
                # Validate data
                if not team_data["team_name"]:
                    raise ValidationError("Team name is required")
                
                if len(players_data) != 2:
                    raise ValidationError("Exactly 2 players are required for eFootball duo tournament")
                
                # Validate required fields for both players
                for i, player in enumerate(players_data, 1):
                    if not player["name"]:
                        raise ValidationError(f"Player {i} name is required")
                    if not player["efootball_id"]:
                        raise ValidationError(f"Player {i} eFootball ID is required")
                    if not player["discord"]:
                        raise ValidationError(f"Player {i} Discord ID is required")
                    if not player["email"]:
                        raise ValidationError(f"Player {i} email is required")
                    if not player["country"]:
                        raise ValidationError(f"Player {i} country is required")
                
                # Validate captain data
                if not captain_data["full_name"]:
                    raise ValidationError("Captain full name is required")
                if not captain_data["email"]:
                    raise ValidationError("Captain email is required")
                if not captain_data["efootball_id"]:
                    raise ValidationError("Captain eFootball ID is required")
                if not captain_data["discord"]:
                    raise ValidationError("Captain Discord ID is required")
                if not captain_data["phone"]:
                    raise ValidationError("Captain phone number is required")
                if not captain_data["country"]:
                    raise ValidationError("Captain country is required")
                
                # Validate agreements
                if tournament_rules["has_rules"]:
                    if not request.POST.get("agree_rules") == "on":
                        raise ValidationError("You must agree to the tournament rules")
                
                if not request.POST.get("agree_visibility") == "on":
                    raise ValidationError("You must agree to visibility settings")
                
                if not request.POST.get("agree_communication") == "on":
                    raise ValidationError("You must agree to receive communications")
                
                if not request.POST.get("confirm_accuracy") == "on":
                    raise ValidationError("You must confirm information accuracy")
                
                if entry_fee and entry_fee > 0:
                    if not request.POST.get("agree_payment") == "on":
                        raise ValidationError("You must agree to pay the entry fee")
                    
                    if not payment_data["payment_method"]:
                        raise ValidationError("Payment method is required")
                    if not payment_data["payment_reference"]:
                        raise ValidationError("Transaction ID is required")
                    if not payment_data["payer_account_number"]:
                        raise ValidationError("Account number is required")
                
                # Captain-only registration when a team exists
                if user_team and not is_captain:
                    raise ValidationError("Only the team captain can register the team")

                # Handle team creation/saving using UserProfile-based helpers
                save_team = request.POST.get("save_team") == "on"
                team = user_team
                if not team:
                    if not save_team:
                        # For eFootball team tournaments we still need an entity; create one
                        team = _create_team_for_user(request.user, team_data["team_name"], team_data.get("team_logo"), game="efootball")
                        if team and team_data.get("team_tag"):
                            team.tag = team_data["team_tag"]
                            team.save(update_fields=["tag"])            
                    else:
                        team = _create_team_for_user(request.user, team_data["team_name"], team_data.get("team_logo"), game="efootball")
                
                # Create registration via service (ensures email + payment verification)
                if create_registration_with_email:
                    registration = create_registration_with_email(
                        tournament=tournament,
                        team=team,
                        payment_method=payment_data.get("payment_method"),
                        payment_reference=payment_data.get("payment_reference"),
                    )
                else:
                    registration = Registration.objects.create(tournament=tournament, team=team, status="PENDING")
                
                # Store additional eFootball-specific data
                efootball_data = {
                    "team_tag": team_data["team_tag"],
                    "captain_discord": captain_data["discord"],
                    "players": players_data,
                    "tournament_type": "efootball_2v2",
                }
                
                # Store as JSON in notes field if available
                if hasattr(registration, 'notes'):
                    import json
                    registration.notes = json.dumps(efootball_data)
                    registration.save()
                
                # Handle PaymentVerification
                if entry_fee and entry_fee > 0 and PaymentVerification:
                    import uuid
                    reference_number = f"EFC-{tournament.slug.upper()}-{uuid.uuid4().hex[:8].upper()}"
                    
                    pv_data = {
                        "registration": registration,
                        "method": payment_data["payment_method"],
                        "payer_account_number": payment_data["payer_account_number"],
                        "transaction_id": payment_data["payment_reference"],
                        "amount_bdt": entry_fee,
                        "status": PaymentVerification.Status.PENDING,
                        "note": f"eFootball duo {team_data['team_name']} registration"
                    }
                    
                    if hasattr(PaymentVerification, '_meta') and any(f.name == 'reference_number' for f in PaymentVerification._meta.fields):
                        pv_data["reference_number"] = reference_number
                    
                    PaymentVerification.objects.create(**pv_data)
                
                messages.success(
                    request,
                    f"⚽ Successfully registered duo team '{team_data['team_name']}' for {tournament.name}! "
                    f"Registration confirmation will be sent to {captain_data['email']} within 24 hours."
                )
                
                return redirect(reverse("tournaments:detail", kwargs={"slug": slug}))
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    return render(request, "tournaments/efootball_register.html", context)


@login_required(login_url="/accounts/login/")
def unified_register(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Unified tournament registration view implementing the revised flow.
    
    Flow:
    1. Authentication check (handled by @login_required)
    2. Tournament type determination
    3. Team membership checks
    4. Dynamic form based on organizer requirements
    5. Team creation if needed
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Determine tournament type first
    is_team_tournament = _is_team_tournament(tournament)
    
    # Only redirect to specialized views for TEAM tournaments of specific games
    if is_team_tournament:
        game_name = str(getattr(tournament, 'game', '')).lower()
        game_type = str(getattr(tournament, 'game_type', '')).lower()
        
        if 'valorant' in game_name or 'valorant' in game_type:
            return redirect('tournaments:valorant_register', slug=slug)
        
        if any(keyword in game_name or keyword in game_type for keyword in ['efootball', 'e-football', 'football', 'fifa', 'pes']):
            return redirect('tournaments:efootball_register', slug=slug)
    
    # Basic tournament info  
    title = read_title(tournament)
    entry_fee = read_fee_amount(tournament)
    # is_team_tournament already determined above
    
    # Get user's team status
    user_team, membership, is_captain = _get_user_team(request.user)
    
    # Get organizer configuration
    organizer_fields = _get_organizer_fields(tournament)
    payment_config = _get_payment_config(tournament)
    tournament_rules = _get_tournament_rules(tournament)
    
    # Determine registration status and flow
    context = {
        "tournament": tournament,
        "title": title,
        "entry_fee": entry_fee,
        "is_team_tournament": is_team_tournament,
        "user_team": user_team,
        "is_captain": is_captain,
        "organizer_fields": organizer_fields,
        "payment_config": payment_config,
        "tournament_rules": tournament_rules,
        "coin_policy": coin_policy_of(tournament),
    }
    
    # Handle team tournaments
    if is_team_tournament:
        if user_team:
            # User has a team - check registration status
            team_status = _check_team_registration_status(tournament, user_team)
            
            if team_status == "registered":
                # Already registered - show status page
                context["status"] = "already_registered"
                context["redirect_url"] = reverse("tournaments:detail", kwargs={"slug": slug})
                return render(request, "tournaments/registration_status.html", context)
            
            elif team_status == "not_registered":
                # Team not registered - check if user can register
                if not is_captain:
                    messages.error(request, "Only the team captain can register the team for tournaments.")
                    return redirect(reverse("tournaments:detail", kwargs={"slug": slug}))
                
                # Captain can register - show team registration form
                context["registration_type"] = "team_existing"
                
        else:
            # User has no team - show team creation form
            context["registration_type"] = "team_create"
    else:
        # Solo tournament - show individual registration form
        context["registration_type"] = "solo"
        
        # Check if already registered as individual
        try:
            prof = _get_user_profile(request.user)
            if prof and Registration.objects.filter(tournament=tournament, user=prof).exists():
                context["status"] = "already_registered"
                context["redirect_url"] = reverse("tournaments:detail", kwargs={"slug": slug})
                return render(request, "tournaments/registration_status.html", context)
        except Exception:
            pass
    
    # Handle form submission
    if request.method == "POST":
        # Honeypot protection
        if request.POST.get("website", "").strip():
            return redirect(reverse("tournaments:unified_register", kwargs={"slug": slug}))
        
        try:
            with transaction.atomic():
                user_data = {
                    "display_name": request.POST.get("display_name", "").strip(),
                    "phone": request.POST.get("phone", "").strip(),
                    "email": request.POST.get("email", "").strip(),
                    "in_game_id": request.POST.get("in_game_id", "").strip(),
                    "payment_method": request.POST.get("payment_method", "").strip(),
                    "payment_reference": request.POST.get("payment_reference", "").strip(),
                    "payer_account_number": request.POST.get("payer_account_number", "").strip(),
                }
                
                # Validate required fields
                if not user_data["display_name"]:
                    raise ValidationError("Display name is required")
                if not user_data["phone"]:
                    raise ValidationError("Phone number is required")
                
                # Validate rules agreement if tournament has rules
                if tournament_rules["has_rules"]:
                    agree_rules = request.POST.get("agree_rules") == "on"
                    if not agree_rules:
                        raise ValidationError("You must agree to the tournament rules and conditions to register")
                
                # Handle payment validation
                if entry_fee and entry_fee > 0:
                    if not user_data["payment_method"] or not user_data["payment_reference"]:
                        raise ValidationError("Payment method and transaction reference are required")
                    if len(user_data["payment_reference"]) < 6:
                        raise ValidationError("Transaction reference must be at least 6 characters")
                
                # Handle team creation if needed
                team_for_registration = user_team
                if context["registration_type"] == "team_create":
                    team_name = request.POST.get("team_name", "").strip()
                    team_logo = request.FILES.get("team_logo")
                    save_as_team = request.POST.get("save_as_team") == "1"
                    
                    if not team_name:
                        raise ValidationError("Team name is required")
                    
                    if save_as_team:
                        # Create permanent team
                        game = getattr(tournament, "game", "")
                        team_for_registration = _create_team_for_user(
                            request.user, team_name, team_logo, game
                        )
                    else:
                        # Registration only - no permanent team created
                        team_for_registration = None
                        user_data["team_name"] = team_name
                
                # Process registration
                registration = _process_registration(
                    request, tournament, user_data, team_for_registration
                )
                
                if entry_fee and entry_fee > 0:
                    messages.success(
                        request, 
                        "Registration submitted successfully! Our organizers will verify your payment manually and send you a confirmation email within 24 hours."
                    )
                else:
                    messages.success(
                        request, 
                        "Registration submitted successfully! You will receive a confirmation email shortly."
                    )
                
                # Try to redirect to receipt page, fallback to tournament detail
                try:
                    return redirect("tournaments:registration_receipt", slug=tournament.slug)
                except Exception:
                    return redirect(reverse("tournaments:detail", kwargs={"slug": tournament.slug}))
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    # Pre-fill form with user data
    if request.user.is_authenticated:
        profile = _get_user_profile(request.user)
        context["initial_data"] = {
            "display_name": (
                getattr(request.user, "get_full_name", lambda: "")() or 
                request.user.username or ""
            ).strip(),
            "email": getattr(request.user, "email", "") or "",
            "phone": "",  # UserProfile doesn't have phone field
        }
    
    return render(request, "tournaments/unified_register.html", context)