# apps/tournaments/services/registration_service_phase2.py
"""
Phase 2: Enhanced Registration Service
Integrates all 6 Phase 1 models into registration logic

Key Changes:
- Uses TournamentSchedule for date validation and timing
- Uses TournamentCapacity for slot management
- Uses TournamentFinance for fee calculations
- Uses TournamentRules for requirements and restrictions
- Uses TournamentArchive to check archive status
- Uses TournamentMedia for display assets
- Backward compatible with legacy Tournament model
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

# Phase 1 Models
from apps.tournaments.models_phase1 import (
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive,
)

# Legacy Models
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


class RegistrationContextPhase2:
    """
    Enhanced registration context using Phase 1 models
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
        user_team=None,
        is_captain: bool = False,
        team_registered: bool = False,
        already_registered: bool = False,
        slots_available: bool = True,
        requires_payment: bool = False,
        registration_closes_in: Optional[timedelta] = None,
        user_profile=None,
        pending_request=None,
        # Phase 1 additions
        schedule_info: Optional[Dict] = None,
        capacity_info: Optional[Dict] = None,
        finance_info: Optional[Dict] = None,
        rules_info: Optional[Dict] = None,
        media_info: Optional[Dict] = None,
        archive_info: Optional[Dict] = None,
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
        
        # Phase 1 model data
        self.schedule_info = schedule_info or {}
        self.capacity_info = capacity_info or {}
        self.finance_info = finance_info or {}
        self.rules_info = rules_info or {}
        self.media_info = media_info or {}
        self.archive_info = archive_info or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            # Core registration state
            "can_register": self.can_register,
            "button_state": self.button_state,
            "button_text": self.button_text,
            "message": self.reason,
            "reason": self.reason,
            
            # User/team state
            "is_team_event": self.is_team_event,
            "is_captain": self.is_captain,
            "team_registered": self.team_registered,
            "already_registered": self.already_registered,
            "has_team": bool(self.user_team),
            "team_name": getattr(self.user_team, "name", None) if self.user_team else None,
            "has_pending_request": bool(self.pending_request),
            
            # Capacity & timing
            "slots_available": self.slots_available,
            "registration_closes_in": str(self.registration_closes_in) if self.registration_closes_in else None,
            
            # Payment
            "requires_payment": self.requires_payment,
            
            # Phase 1 data
            "schedule": self.schedule_info,
            "capacity": self.capacity_info,
            "finance": self.finance_info,
            "rules": self.rules_info,
            "media": self.media_info,
            "archive": self.archive_info,
        }


class RegistrationServicePhase2:
    """
    Enhanced registration service using Phase 1 models
    """

    @staticmethod
    def _get_schedule_info(tournament) -> Dict[str, Any]:
        """Get schedule information from Phase 1 model or legacy"""
        try:
            schedule = TournamentSchedule.objects.filter(tournament=tournament).first()
            if schedule:
                return {
                    "has_phase1": True,
                    "registration_open_at": schedule.registration_open_at,
                    "registration_close_at": schedule.registration_close_at,
                    "start_at": schedule.start_at,
                    "end_at": schedule.end_at,
                    "is_registration_open": schedule.is_registration_open,
                    "is_started": schedule.is_started,
                    "is_completed": schedule.is_completed,
                    "days_until_start": schedule.days_until_start,
                    "time_until_registration_closes": schedule.time_until_registration_closes(),
                }
        except Exception:
            pass
        
        # Legacy fallback
        settings = getattr(tournament, "settings", None)
        reg_open = getattr(settings, "reg_open_at", None) if settings else None
        start_at = getattr(tournament, "start_at", None)
        
        return {
            "has_phase1": False,
            "registration_open_at": reg_open,
            "registration_close_at": start_at,
            "start_at": start_at,
            "end_at": None,
            "is_registration_open": bool(reg_open and reg_open <= timezone.now() and start_at and start_at > timezone.now()),
            "is_started": bool(start_at and start_at <= timezone.now()),
            "is_completed": False,
        }

    @staticmethod
    def _get_capacity_info(tournament) -> Dict[str, Any]:
        """Get capacity information from Phase 1 model or legacy"""
        try:
            capacity = TournamentCapacity.objects.filter(tournament=tournament).first()
            if capacity:
                return {
                    "has_phase1": True,
                    "max_teams": capacity.max_teams,
                    "current_teams": capacity.current_teams,
                    "min_teams": capacity.min_teams,
                    "available_slots": capacity.available_slots,
                    "fill_percentage": capacity.fill_percentage,
                    "is_full": capacity.is_full,
                    "can_accept_registrations": capacity.can_accept_registrations,
                    "waitlist_enabled": capacity.waitlist_enabled,
                    "waitlist_size": capacity.waitlist_size,
                }
        except Exception:
            pass
        
        # Legacy fallback
        slot_size = getattr(tournament, "slot_size", None)
        current_count = Registration.objects.filter(
            tournament=tournament,
            status="CONFIRMED"
        ).count() if slot_size else 0
        
        return {
            "has_phase1": False,
            "max_teams": slot_size or 0,
            "current_teams": current_count,
            "available_slots": max(0, (slot_size or 0) - current_count),
            "is_full": current_count >= (slot_size or 0) if slot_size else False,
            "can_accept_registrations": current_count < (slot_size or 0) if slot_size else True,
        }

    @staticmethod
    def _get_finance_info(tournament) -> Dict[str, Any]:
        """Get finance information from Phase 1 model or legacy"""
        try:
            finance = TournamentFinance.objects.filter(tournament=tournament).first()
            if finance:
                return {
                    "has_phase1": True,
                    "entry_fee": finance.entry_fee,
                    "currency": finance.currency,
                    "prize_pool": finance.prize_pool,
                    "is_free": finance.is_free,
                    "has_prizes": finance.has_prizes,
                    "entry_fee_display": finance.entry_fee_display,
                    "prize_pool_display": finance.prize_pool_display,
                }
        except Exception:
            pass
        
        # Legacy fallback
        entry_fee = getattr(tournament, "entry_fee_bdt", None) or getattr(tournament, "entry_fee", None) or Decimal("0")
        prize_pool = getattr(tournament, "prize_pool_bdt", None) or getattr(tournament, "prize_pool", None) or Decimal("0")
        
        return {
            "has_phase1": False,
            "entry_fee": entry_fee,
            "currency": "BDT",
            "prize_pool": prize_pool,
            "is_free": entry_fee == 0,
            "has_prizes": prize_pool > 0,
            "entry_fee_display": f"৳{entry_fee:,.0f}" if entry_fee else "Free",
            "prize_pool_display": f"৳{prize_pool:,.0f}" if prize_pool else "N/A",
        }

    @staticmethod
    def _get_rules_info(tournament) -> Dict[str, Any]:
        """Get rules information from Phase 1 model or legacy"""
        try:
            rules = TournamentRules.objects.filter(tournament=tournament).first()
            if rules:
                return {
                    "has_phase1": True,
                    "min_age": rules.min_age,
                    "max_age": rules.max_age,
                    "allowed_regions": rules.allowed_regions,
                    "banned_regions": rules.banned_regions,
                    "min_rank": rules.min_rank,
                    "max_rank": rules.max_rank,
                    "require_discord": rules.require_discord,
                    "require_game_id": rules.require_game_id,
                    "require_verification": rules.require_verification,
                    "has_age_restriction": rules.has_age_restriction,
                    "has_region_restriction": rules.has_region_restriction,
                    "has_rank_restriction": rules.has_rank_restriction,
                    "requirements_list": rules.requirements_list,
                }
        except Exception:
            pass
        
        # Legacy fallback
        settings = getattr(tournament, "settings", None)
        return {
            "has_phase1": False,
            "require_discord": getattr(settings, "require_discord_id", False) if settings else False,
            "require_game_id": getattr(settings, "require_ingame_id", False) if settings else False,
            "requirements_list": [],
        }

    @staticmethod
    def _get_media_info(tournament) -> Dict[str, Any]:
        """Get media information from Phase 1 model or legacy"""
        try:
            media = TournamentMedia.objects.filter(tournament=tournament).first()
            if media:
                return {
                    "has_phase1": True,
                    "logo_url": media.logo_url,
                    "banner_url": media.banner_url,
                    "thumbnail_url": media.thumbnail_url,
                    "has_logo": media.has_logo,
                    "has_banner": media.has_banner,
                }
        except Exception:
            pass
        
        # Legacy fallback
        return {
            "has_phase1": False,
            "banner_url": getattr(tournament.banner, "url", None) if hasattr(tournament, "banner") and tournament.banner else None,
            "thumbnail_url": getattr(tournament.thumbnail, "url", None) if hasattr(tournament, "thumbnail") and tournament.thumbnail else None,
        }

    @staticmethod
    def _get_archive_info(tournament) -> Dict[str, Any]:
        """Get archive information from Phase 1 model"""
        try:
            archive = TournamentArchive.objects.filter(tournament=tournament).first()
            if archive:
                return {
                    "has_phase1": True,
                    "is_archived": archive.is_archived,
                    "archive_reason": archive.archive_reason,
                    "archived_at": archive.archived_at,
                }
        except Exception:
            pass
        
        return {
            "has_phase1": False,
            "is_archived": False,
        }

    @staticmethod
    def _is_team_event(tournament) -> bool:
        """Determine if tournament is team-based"""
        settings = getattr(tournament, "settings", None)
        if settings:
            min_team_size = getattr(settings, "min_team_size", None)
            max_team_size = getattr(settings, "max_team_size", None)
            if (min_team_size and min_team_size > 1) or (max_team_size and max_team_size > 1):
                return True

        mode = getattr(tournament, "mode", "") or getattr(settings, "mode", "") if settings else ""
        if mode and any(x in str(mode).lower() for x in ["team", "squad", "5v5", "3v3", "2v2"]):
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
            profile = UserProfile.objects.filter(user=user).first()
            if not profile:
                return None, None, False

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
    def _check_already_registered(tournament, user, team=None) -> bool:
        """Check if user or team is already registered"""
        try:
            profile = UserProfile.objects.filter(user=user).first()
            if not profile:
                return False

            if Registration.objects.filter(tournament=tournament, user=profile).exists():
                return True

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
    def get_registration_context(cls, tournament, user) -> RegistrationContextPhase2:
        """
        Get complete registration context using Phase 1 models
        """
        now = timezone.now()

        # Get Phase 1 model info
        schedule_info = cls._get_schedule_info(tournament)
        capacity_info = cls._get_capacity_info(tournament)
        finance_info = cls._get_finance_info(tournament)
        rules_info = cls._get_rules_info(tournament)
        media_info = cls._get_media_info(tournament)
        archive_info = cls._get_archive_info(tournament)

        # Check if user is authenticated
        if not user or not user.is_authenticated:
            return RegistrationContextPhase2(
                tournament=tournament,
                user=None,
                can_register=False,
                button_state="not_authenticated",
                button_text="Login to Register",
                reason="You must be logged in to register",
                is_team_event=cls._is_team_event(tournament),
                user_team=None,
                is_captain=False,
                team_registered=False,
                already_registered=False,
                slots_available=capacity_info.get("can_accept_registrations", True),
                requires_payment=not finance_info.get("is_free", False),
                registration_closes_in=schedule_info.get("time_until_registration_closes"),
                user_profile=None,
                pending_request=None,
                schedule_info=schedule_info,
                capacity_info=capacity_info,
                finance_info=finance_info,
                rules_info=rules_info,
                media_info=media_info,
                archive_info=archive_info,
            )

        # Get user profile
        try:
            user_profile = UserProfile.objects.filter(user=user).first()
        except Exception:
            user_profile = None

        # Get team info
        is_team_event = cls._is_team_event(tournament)
        user_team, membership, is_captain = None, None, False
        if is_team_event:
            user_team, membership, is_captain = cls._get_user_team(user)

        # Check registration status
        already_registered = cls._check_already_registered(tournament, user, user_team)
        team_registered = already_registered and user_team is not None

        # Check pending request
        pending_request = None
        if is_team_event and user_team and not is_captain:
            pending_request = cls._check_pending_request(tournament, user, user_team)

        # Determine button state and text
        button_state = "disabled"
        button_text = "Registration Unavailable"
        can_register = False
        reason = ""

        # Check archive status first
        if archive_info.get("is_archived"):
            button_state = "archived"
            button_text = "Tournament Archived"
            reason = archive_info.get("archive_reason") or "This tournament has been archived"

        # Already registered
        elif already_registered:
            button_state = "registered"
            button_text = "Registered ✓"
            reason = "You are already registered for this tournament"

        # Tournament completed
        elif schedule_info.get("is_completed"):
            button_state = "completed"
            button_text = "Tournament Ended"
            reason = "This tournament has ended"

        # Tournament started
        elif schedule_info.get("is_started"):
            button_state = "started"
            button_text = "Tournament Started"
            reason = "Tournament has already begun"

        # Registration closed
        elif not schedule_info.get("is_registration_open"):
            reg_open = schedule_info.get("registration_open_at")
            if reg_open and reg_open > now:
                button_state = "not_open"
                button_text = f"Opens {reg_open.strftime('%b %d, %H:%M')}"
                reason = "Registration has not opened yet"
            else:
                button_state = "closed"
                button_text = "Registration Closed"
                reason = "Registration deadline has passed"

        # Tournament full
        elif capacity_info.get("is_full"):
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
                can_register = True

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
        elif schedule_info.get("is_registration_open") and capacity_info.get("can_accept_registrations"):
            button_state = "register"
            button_text = "Register Now"
            can_register = True
            reason = "Ready to register"

        return RegistrationContextPhase2(
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
            slots_available=capacity_info.get("can_accept_registrations", True),
            requires_payment=not finance_info.get("is_free", False),
            registration_closes_in=schedule_info.get("time_until_registration_closes"),
            user_profile=user_profile,
            pending_request=pending_request,
            schedule_info=schedule_info,
            capacity_info=capacity_info,
            finance_info=finance_info,
            rules_info=rules_info,
            media_info=media_info,
            archive_info=archive_info,
        )

    @staticmethod
    def auto_fill_profile_data(user) -> Dict[str, Any]:
        """Extract user profile data for form auto-fill"""
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
        """Extract team data for form auto-fill"""
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
                    "verified": True,
                })
        except Exception:
            pass

        return data

    @staticmethod
    def validate_registration_data_phase2(
        tournament, 
        user, 
        data: Dict[str, Any],
        schedule_info: Dict = None,
        capacity_info: Dict = None,
        finance_info: Dict = None,
        rules_info: Dict = None,
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Enhanced validation using Phase 1 models
        """
        errors = {}

        # Get Phase 1 info if not provided
        if schedule_info is None:
            schedule_info = RegistrationServicePhase2._get_schedule_info(tournament)
        if capacity_info is None:
            capacity_info = RegistrationServicePhase2._get_capacity_info(tournament)
        if finance_info is None:
            finance_info = RegistrationServicePhase2._get_finance_info(tournament)
        if rules_info is None:
            rules_info = RegistrationServicePhase2._get_rules_info(tournament)

        # Schedule validation
        if not schedule_info.get("is_registration_open"):
            errors["_timing"] = "Registration is not currently open"

        # Capacity validation
        if not capacity_info.get("can_accept_registrations"):
            errors["_capacity"] = "Tournament is full"

        # Required fields
        if not data.get("display_name"):
            errors["display_name"] = "Display name is required"

        if not data.get("phone") and not data.get("payer_account_number"):
            errors["phone"] = "Contact number is required"

        # Phone format validation
        phone = data.get("phone") or data.get("payer_account_number")
        if phone:
            import re
            if not re.match(r"^(?:\+?880|0)1[0-9]{9}$", str(phone).replace(" ", "")):
                errors["phone"] = "Enter a valid Bangladeshi mobile number"

        # Email validation
        email = data.get("email")
        if email:
            from django.core.validators import validate_email as django_validate_email
            try:
                django_validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address"

        # Payment validation
        if not finance_info.get("is_free"):
            if not data.get("payment_method"):
                errors["payment_method"] = "Payment method is required"
            if not data.get("payment_reference"):
                errors["payment_reference"] = "Transaction ID is required"
            elif len(str(data.get("payment_reference"))) < 6:
                errors["payment_reference"] = "Transaction ID must be at least 6 characters"

        # Rules validation
        if rules_info.get("require_discord") and not data.get("discord_id"):
            errors["discord_id"] = "Discord ID is required for this tournament"

        if rules_info.get("require_game_id") and not data.get("in_game_id"):
            errors["in_game_id"] = "In-game ID is required for this tournament"

        # Age restriction
        if rules_info.get("has_age_restriction"):
            min_age = rules_info.get("min_age")
            max_age = rules_info.get("max_age")
            user_age = data.get("age")
            if user_age:
                try:
                    user_age = int(user_age)
                    if min_age and user_age < min_age:
                        errors["age"] = f"Minimum age is {min_age}"
                    if max_age and user_age > max_age:
                        errors["age"] = f"Maximum age is {max_age}"
                except ValueError:
                    errors["age"] = "Invalid age"

        # Region restriction
        if rules_info.get("has_region_restriction"):
            user_region = data.get("region")
            allowed_regions = rules_info.get("allowed_regions", [])
            banned_regions = rules_info.get("banned_regions", [])
            
            if allowed_regions and user_region not in allowed_regions:
                errors["region"] = f"Only players from {', '.join(allowed_regions)} can register"
            
            if banned_regions and user_region in banned_regions:
                errors["region"] = f"Players from {user_region} cannot register"

        # Rules agreement
        if data.get("require_rules_agree") and not data.get("agree_rules"):
            errors["agree_rules"] = "You must agree to the tournament rules"

        return len(errors) == 0, errors

    @classmethod
    @transaction.atomic
    def create_registration_phase2(
        cls,
        tournament,
        user,
        data: Dict[str, Any],
        team=None
    ) -> Registration:
        """
        Create registration with Phase 1 model integration
        """
        # Get Phase 1 info
        schedule_info = cls._get_schedule_info(tournament)
        capacity_info = cls._get_capacity_info(tournament)
        finance_info = cls._get_finance_info(tournament)
        rules_info = cls._get_rules_info(tournament)

        # Validate
        is_valid, errors = cls.validate_registration_data_phase2(
            tournament, user, data,
            schedule_info=schedule_info,
            capacity_info=capacity_info,
            finance_info=finance_info,
            rules_info=rules_info,
        )
        if not is_valid:
            raise ValidationError(errors)

        # Get user profile
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            raise ValidationError({"user": "User profile not found"})

        # Check for duplicates
        if cls._check_already_registered(tournament, user, team):
            raise ValidationError({"non_field_errors": "Already registered for this tournament"})

        # Create registration
        registration = Registration.objects.create(
            tournament=tournament,
            user=profile,
            team=team,
            status="PENDING",
            payment_method=data.get("payment_method", ""),
            payment_sender=data.get("payer_account_number", ""),
            payment_reference=data.get("payment_reference", ""),
            payment_status="pending" if not finance_info.get("is_free") else "verified",
        )

        # Update Phase 1 capacity if available
        if capacity_info.get("has_phase1"):
            try:
                capacity = TournamentCapacity.objects.filter(tournament=tournament).first()
                if capacity:
                    capacity.increment_teams()
            except Exception:
                pass

        # Record payment in Phase 1 finance if available
        if finance_info.get("has_phase1") and not finance_info.get("is_free"):
            try:
                finance = TournamentFinance.objects.filter(tournament=tournament).first()
                if finance and data.get("payment_reference"):
                    finance.record_payment(
                        amount=finance_info.get("entry_fee"),
                        reference=data.get("payment_reference"),
                        notes=f"Registration payment from {profile.display_name}"
                    )
            except Exception:
                pass

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
            pass

        return registration
