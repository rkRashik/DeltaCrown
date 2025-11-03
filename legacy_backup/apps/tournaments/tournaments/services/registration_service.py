# apps/tournaments/services/registration_service.py
"""
Modern Registration Service
Handles all registration logic, validations, and business rules
"""
from __future__ import annotations
from datetime import timedelta
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")
RegistrationRequest = apps.get_model("tournaments", "RegistrationRequest")
UserProfile = apps.get_model("user_profile", "UserProfile")


def _get_team_models():
    """Get team-related models with fallback"""
    try:
        Team = apps.get_model("teams", "Team")
        TeamMembership = apps.get_model("teams", "TeamMembership")
        return Team, TeamMembership
    except Exception:
        return None, None


class RegistrationContext:
    """
    Context object containing all information needed for registration UI
    """
    def __init__(
        self,
        tournament,
        user,
        can_register: bool = False,
        button_state: str = "disabled",
        button_text: str = "Registration Unavailable",
        reason: str = "",
        is_team_event: bool = False,
        user_team = None,
        is_captain: bool = False,
        team_registered: bool = False,
        already_registered: bool = False,
        slots_available: bool = True,
        requires_payment: bool = False,
        registration_closes_in: Optional[timedelta] = None,
        user_profile = None,
        pending_request = None,
    ):
        self.tournament = tournament
        self.user = user
        self.can_register = can_register
        self.button_state = button_state
        self.button_text = button_text
        self.reason = reason
        self.is_team_event = is_team_event
        self.user_team = user_team
        self.is_captain = is_captain
        self.team_registered = team_registered
        self.already_registered = already_registered
        self.slots_available = slots_available
        self.requires_payment = requires_payment
        self.registration_closes_in = registration_closes_in
        self.user_profile = user_profile
        self.pending_request = pending_request

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "can_register": self.can_register,
            "button_state": self.button_state,
            "button_text": self.button_text,
            "message": self.reason,
            "reason": self.reason,
            "is_team_event": self.is_team_event,
            "is_captain": self.is_captain,
            "team_registered": self.team_registered,
            "already_registered": self.already_registered,
            "slots_available": self.slots_available,
            "requires_payment": self.requires_payment,
            "registration_closes_in": str(self.registration_closes_in) if self.registration_closes_in else None,
            "has_team": bool(self.user_team),
            "team_name": getattr(self.user_team, "name", None) if self.user_team else None,
            "has_pending_request": bool(self.pending_request),
        }


class RegistrationService:
    """
    Service layer for tournament registration
    """

    @staticmethod
    def _is_team_event(tournament) -> bool:
        """Determine if tournament is team-based"""
        # Check tournament_type field first (Phase 2 field)
        tournament_type = getattr(tournament, "tournament_type", "")
        if tournament_type and str(tournament_type).upper() in ['TEAM', 'MIXED']:
            return True
        
        # Check settings.min_team_size / max_team_size
        settings = getattr(tournament, "settings", None)
        if settings:
            min_team_size = getattr(settings, "min_team_size", None)
            max_team_size = getattr(settings, "max_team_size", None)
            if (min_team_size and min_team_size > 1) or (max_team_size and max_team_size > 1):
                return True

        return False

    @staticmethod
    def _get_user_team(user) -> Tuple[Optional[Any], Optional[Any], bool]:
        """
        Get user's team, membership, and captain status
        Returns: (team, membership, is_captain)
        """
        Team, TeamMembership = _get_team_models()
        if not Team or not TeamMembership:
            return None, None, False

        try:
            # Get user profile
            profile = UserProfile.objects.filter(user=user).first()
            if not profile:
                return None, None, False

            # Get active membership
            membership = TeamMembership.objects.filter(
                profile=profile,
                status="ACTIVE"
            ).select_related("team").first()

            if not membership:
                return None, None, False

            team = membership.team
            is_captain = (
                membership.role == "CAPTAIN" or
                (hasattr(team, "captain") and team.captain_id == profile.id)
            )

            return team, membership, is_captain

        except Exception:
            return None, None, False

    @staticmethod
    def _check_slots_available(tournament) -> bool:
        """Check if tournament has available slots"""
        slot_size = getattr(tournament, "slot_size", None)
        if not slot_size or slot_size <= 0:
            return True  # No limit set

        try:
            # Count confirmed registrations
            current_count = Registration.objects.filter(
                tournament=tournament,
                status="CONFIRMED"
            ).count()
            return current_count < slot_size
        except Exception:
            return True  # Fail-safe: allow registration

    @staticmethod
    def _check_already_registered(tournament, user, team=None) -> bool:
        """Check if user or team is already registered"""
        try:
            profile = UserProfile.objects.filter(user=user).first()
            if not profile:
                return False

            # Check user registration (solo)
            if Registration.objects.filter(tournament=tournament, user=profile).exists():
                return True

            # Check team registration
            if team and Registration.objects.filter(tournament=tournament, team=team).exists():
                return True

            return False
        except Exception:
            return False

    @staticmethod
    def _check_pending_request(tournament, user, team) -> Optional[Any]:
        """Check if user has pending approval request"""
        if not team:
            return None

        try:
            profile = UserProfile.objects.filter(user=user).first()
            if not profile:
                return None

            return RegistrationRequest.objects.filter(
                tournament=tournament,
                team=team,
                requester=profile,
                status="PENDING"
            ).first()
        except Exception:
            return None

    @classmethod
    def get_registration_context(cls, tournament, user) -> RegistrationContext:
        """
        Get complete registration context for UI rendering.
        Now uses centralized state machine for consistency.
        """
        now = timezone.now()

        # Check if user is authenticated
        if not user or not user.is_authenticated:
            # Anonymous user - show basic state
            return RegistrationContext(
                tournament=tournament,
                user=None,
                can_register=False,
                button_state="not_authenticated",
                button_text="Login to Register",
                reason="You must be logged in to register",
                is_team_event=tournament.state.is_team_based,
                user_team=None,
                is_captain=False,
                team_registered=False,
                already_registered=False,
                slots_available=not tournament.state.is_full,
                requires_payment=bool(getattr(tournament, "entry_fee_bdt", None) or getattr(tournament, "entry_fee", None)),
                registration_closes_in=tournament.state.time_until_registration_closes(),
                user_profile=None,
                pending_request=None,
            )

        # Get user profile
        try:
            user_profile = UserProfile.objects.filter(user=user).first()
        except Exception:
            user_profile = None

        # Use state machine for core checks
        state_machine = tournament.state
        is_team_event = state_machine.is_team_based
        slots_available = not state_machine.is_full
        reg_state = state_machine.registration_state

        # Get user's team if team event
        user_team, membership, is_captain = None, None, False
        if is_team_event:
            user_team, membership, is_captain = cls._get_user_team(user)

        # Check if already registered
        already_registered = cls._check_already_registered(tournament, user, user_team)
        team_registered = already_registered and user_team is not None

        # Check pending approval request
        pending_request = None
        if is_team_event and user_team and not is_captain:
            pending_request = cls._check_pending_request(tournament, user, user_team)

        # Check payment requirement
        entry_fee = getattr(tournament, "entry_fee_bdt", None) or getattr(tournament, "entry_fee", None)
        requires_payment = bool(entry_fee and entry_fee > 0)

        # Determine button state and text using state machine
        button_state = "disabled"
        button_text = "Registration Unavailable"
        can_register = False
        reason = ""

        # Already registered
        if already_registered:
            button_state = "registered"
            button_text = "Registered ✓"
            reason = "You are already registered for this tournament"

        # Use state machine for registration state
        elif reg_state.value == 'completed':
            button_state = "completed"
            button_text = "Tournament Ended"
            reason = "This tournament has ended"

        elif reg_state.value == 'started':
            button_state = "started"
            button_text = "Tournament Started"
            reason = "Tournament has already begun"

        elif reg_state.value == 'closed':
            button_state = "closed"
            button_text = "Registration Closed"
            reason = "Registration deadline has passed"

        elif reg_state.value == 'not_open':
            reg_open, _ = state_machine.registration_window
            button_state = "not_open"
            button_text = f"Opens {reg_open.strftime('%b %d, %H:%M')}" if reg_open else "Not Open Yet"
            reason = "Registration has not opened yet"

        elif reg_state.value == 'full':
            button_state = "full"
            button_text = "Tournament Full"
            reason = "All slots have been filled"

        # Team event, non-captain
        elif is_team_event and user_team and not is_captain:
            if pending_request:
                button_state = "request_pending"
                button_text = "Request Pending"
                reason = f"Waiting for {user_team.captain.display_name if hasattr(user_team, 'captain') else 'captain'} to approve"
            else:
                button_state = "request_approval"
                button_text = "Request Captain Approval"
                reason = "Only the team captain can register"
                can_register = True  # Can create request

        # Team event, no team
        elif is_team_event and not user_team:
            button_state = "no_team"
            button_text = "Create/Join Team First"
            reason = "You need to be part of a team to register"

        # Team event, team already registered
        elif is_team_event and team_registered:
            button_state = "registered"
            button_text = "Team Registered ✓"
            reason = "Your team is already registered"

        # All clear - can register!
        elif reg_state.value == 'open':
            button_state = "register"
            button_text = "Register Now"
            can_register = True
            reason = "Ready to register"

        return RegistrationContext(
            tournament=tournament,
            user=user,
            can_register=can_register,
            button_state=button_state,
            button_text=button_text,
            reason=reason,
            is_team_event=is_team_event,
            user_team=user_team,
            is_captain=is_captain,
            team_registered=team_registered,
            already_registered=already_registered,
            slots_available=slots_available,
            requires_payment=requires_payment,
            registration_closes_in=state_machine.time_until_registration_closes(),
            user_profile=user_profile,
            pending_request=pending_request,
        )

    @staticmethod
    def auto_fill_profile_data(user) -> Dict[str, Any]:
        """
        Extract user profile data for form auto-fill
        """
        data = {
            "email": getattr(user, "email", ""),
            "username": getattr(user, "username", ""),
        }

        try:
            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                data.update({
                    "display_name": getattr(profile, "display_name", ""),
                    "phone": getattr(profile, "phone", "") or getattr(profile, "mobile", ""),
                    "discord_id": getattr(profile, "discord_id", ""),
                    "riot_id": getattr(profile, "riot_id", ""),
                    "efootball_id": getattr(profile, "efootball_id", ""),
                    "region": getattr(profile, "region", ""),
                })
        except Exception:
            pass

        return data

    @staticmethod
    def auto_fill_team_data(team) -> Dict[str, Any]:
        """
        Extract team data for form auto-fill
        """
        if not team:
            return {}

        Team, TeamMembership = _get_team_models()
        if not TeamMembership:
            return {}

        data = {
            "team_id": getattr(team, "id", None),
            "team_name": getattr(team, "name", ""),
            "team_tag": getattr(team, "tag", ""),
            "team_logo_url": getattr(team.logo, "url", None) if hasattr(team, "logo") and team.logo else None,
            "members": [],
        }

        try:
            # Get all active members
            memberships = TeamMembership.objects.filter(
                team=team,
                status="ACTIVE"
            ).select_related("profile").order_by("-role", "joined_at")

            for membership in memberships:
                profile = membership.profile
                data["members"].append({
                    "profile_id": profile.id,
                    "display_name": getattr(profile, "display_name", ""),
                    "role": membership.role,
                    "is_captain": membership.role == "CAPTAIN",
                    "verified": True,  # Active membership = verified
                })
        except Exception:
            pass

        return data

    @staticmethod
    def validate_registration_data(tournament, user, data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate registration data
        Returns: (is_valid, errors_dict)
        """
        errors = {}

        # Required fields
        if not data.get("display_name"):
            errors["display_name"] = "Display name is required"

        if not data.get("phone") and not data.get("payer_account_number"):
            errors["phone"] = "Contact number is required"

        # Phone format validation (Bangladesh mobile)
        phone = data.get("phone") or data.get("payer_account_number")
        if phone:
            import re
            if not re.match(r"^(?:\+?880|0)1[0-9]{9}$", str(phone).replace(" ", "")):
                errors["phone"] = "Enter a valid Bangladeshi mobile number (e.g., 01712345678)"

        # Email validation
        email = data.get("email")
        if email:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address"

        # Payment validation if required
        entry_fee = getattr(tournament, "entry_fee_bdt", None) or getattr(tournament, "entry_fee", None)
        if entry_fee and entry_fee > 0:
            if not data.get("payment_method"):
                errors["payment_method"] = "Payment method is required"
            if not data.get("payment_reference"):
                errors["payment_reference"] = "Transaction ID is required"
            elif len(str(data.get("payment_reference"))) < 6:
                errors["payment_reference"] = "Transaction ID must be at least 6 characters"

        # Rules agreement
        if data.get("require_rules_agree") and not data.get("agree_rules"):
            errors["agree_rules"] = "You must agree to the tournament rules"

        # Game-specific validations
        settings = getattr(tournament, "settings", None)
        if settings:
            if getattr(settings, "require_ingame_id", False) and not data.get("in_game_id"):
                errors["in_game_id"] = "In-game ID is required for this tournament"

        return len(errors) == 0, errors

    @classmethod
    @transaction.atomic
    def create_registration(
        cls,
        tournament,
        user,
        data: Dict[str, Any],
        team=None
    ) -> Registration:
        """
        Create a new registration
        """
        # Validate first
        is_valid, errors = cls.validate_registration_data(tournament, user, data)
        if not is_valid:
            raise ValidationError(errors)

        # Get user profile
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            raise ValidationError({"user": "User profile not found"})

        # Check for duplicates
        if cls._check_already_registered(tournament, user, team):
            raise ValidationError({"non_field_errors": "Already registered for this tournament"})

        # Check slots
        if not cls._check_slots_available(tournament):
            raise ValidationError({"non_field_errors": "Tournament is full"})

        # Create registration
        registration = Registration.objects.create(
            tournament=tournament,
            user=profile,
            team=team,
            status="PENDING",
            payment_method=data.get("payment_method", ""),
            payment_sender=data.get("payer_account_number", ""),
            payment_reference=data.get("payment_reference", ""),
            payment_status="pending" if data.get("payment_method") else "verified",
        )

        # Send notification
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                recipient=profile,
                event="REGISTRATION_SUBMITTED",
                title="Registration Submitted",
                message=f"Your registration for {tournament.name} has been submitted and is pending verification.",
                action_url=f"/dashboard/registrations/{registration.id}/",
                priority="NORMAL"
            )
        except Exception:
            pass  # Don't fail registration if notification fails

        return registration
