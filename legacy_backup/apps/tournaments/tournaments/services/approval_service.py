# apps/tournaments/services/approval_service.py
"""
Captain Approval Service
Handles registration approval requests from non-captain team members
"""
from __future__ import annotations
from datetime import timedelta
from typing import Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

# Models
Tournament = apps.get_model("tournaments", "Tournament")
RegistrationRequest = apps.get_model("tournaments", "RegistrationRequest")
UserProfile = apps.get_model("user_profile", "UserProfile")


def _get_team_models():
    """Get team models"""
    try:
        Team = apps.get_model("teams", "Team")
        TeamMembership = apps.get_model("teams", "TeamMembership")
        return Team, TeamMembership
    except Exception:
        return None, None


class ApprovalService:
    """
    Service for handling registration approval workflows
    """

    @staticmethod
    def _get_captain(team):
        """Get the captain of a team"""
        Team, TeamMembership = _get_team_models()
        if not TeamMembership:
            return None

        try:
            # Try team.captain field first
            if hasattr(team, "captain") and team.captain:
                return team.captain

            # Fallback: find CAPTAIN membership
            membership = TeamMembership.objects.filter(
                team=team,
                role="CAPTAIN",
                status="ACTIVE"
            ).select_related("profile").first()

            return membership.profile if membership else None
        except Exception:
            return None

    @staticmethod
    def _verify_membership(profile, team) -> bool:
        """Verify that profile is an active member of team"""
        Team, TeamMembership = _get_team_models()
        if not TeamMembership:
            return False

        try:
            return TeamMembership.objects.filter(
                team=team,
                profile=profile,
                status="ACTIVE"
            ).exists()
        except Exception:
            return False

    @classmethod
    @transaction.atomic
    def create_request(
        cls,
        requester,  # UserProfile
        tournament,
        team,
        message: str = ""
    ):
        """
        Create a new approval request
        """
        # Verify requester is a member
        if not cls._verify_membership(requester, team):
            raise ValidationError({
                "requester": "You must be an active member of this team"
            })

        # Get captain
        captain = cls._get_captain(team)
        if not captain:
            raise ValidationError({
                "team": "Team has no captain"
            })

        # Can't request from yourself
        if requester.id == captain.id:
            raise ValidationError({
                "requester": "You are the captain. Register the team directly."
            })

        # Check for existing pending request
        existing = RegistrationRequest.objects.filter(
            tournament=tournament,
            team=team,
            requester=requester,
            status="PENDING"
        ).first()

        if existing:
            raise ValidationError({
                "non_field_errors": "You already have a pending request for this tournament"
            })

        # Set expiration
        expires_at = tournament.reg_close_at if tournament.reg_close_at else (
            timezone.now() + timedelta(days=7)
        )

        # Create request
        request = RegistrationRequest.objects.create(
            requester=requester,
            tournament=tournament,
            team=team,
            captain=captain,
            message=message[:500] if message else "",
            status="PENDING",
            expires_at=expires_at
        )

        # Send notification to captain
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                recipient=captain,
                event="APPROVAL_REQUEST_CREATED",
                title="Registration Request",
                message=f"{requester.display_name} requested that you register {team.name} for {tournament.name}.",
                action_url=f"/teams/{team.id}/registration-requests/",
                priority="HIGH"
            )
        except Exception:
            pass  # Don't fail on notification error

        return request

    @classmethod
    @transaction.atomic
    def approve_request(
        cls,
        request,  # RegistrationRequest
        captain,  # UserProfile
        response_message: str = "",
        auto_register: bool = True
    ):
        """
        Approve a registration request
        """
        # Verify captain
        if request.captain_id != captain.id:
            raise ValidationError({
                "captain": "Only the team captain can approve this request"
            })

        # Check if already processed
        if request.status != "PENDING":
            raise ValidationError({
                "non_field_errors": f"Request has already been {request.status.lower()}"
            })

        # Check if expired
        if request.is_expired:
            request.mark_expired()
            raise ValidationError({
                "non_field_errors": "Request has expired"
            })

        # Mark as approved
        request.approve(response_message)

        # Send notification to requester
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                recipient=request.requester,
                event="APPROVAL_REQUEST_APPROVED",
                title="Request Approved",
                message=f"{captain.display_name} approved your registration request for {request.tournament.name}. The team will be registered shortly.",
                action_url=f"/tournaments/{request.tournament.slug}/",
                priority="HIGH"
            )
        except Exception:
            pass

        # Optionally auto-register the team
        if auto_register:
            try:
                from .registration_service import RegistrationService
                # Captain registers the team
                registration = RegistrationService.create_registration(
                    tournament=request.tournament,
                    user=captain.user if hasattr(captain, "user") else None,
                    data={
                        "display_name": captain.display_name,
                        "email": getattr(captain.user, "email", "") if hasattr(captain, "user") else "",
                        "phone": "",
                    },
                    team=request.team
                )
                return registration
            except Exception as e:
                # Log error but don't fail approval
                print(f"Auto-registration failed: {e}")
                pass

        return None

    @classmethod
    @transaction.atomic
    def reject_request(
        cls,
        request,  # RegistrationRequest
        captain,  # UserProfile
        response_message: str = ""
    ):
        """
        Reject a registration request
        """
        # Verify captain
        if request.captain_id != captain.id:
            raise ValidationError({
                "captain": "Only the team captain can reject this request"
            })

        # Check if already processed
        if request.status != "PENDING":
            raise ValidationError({
                "non_field_errors": f"Request has already been {request.status.lower()}"
            })

        # Mark as rejected
        request.reject(response_message)

        # Send notification to requester
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send(
                recipient=request.requester,
                event="APPROVAL_REQUEST_REJECTED",
                title="Request Declined",
                message=f"{captain.display_name} declined your registration request for {request.tournament.name}. Reason: {response_message or 'Not specified'}",
                action_url=f"/tournaments/{request.tournament.slug}/",
                priority="NORMAL"
            )
        except Exception:
            pass

    @staticmethod
    def expire_old_requests():
        """
        Mark expired requests as EXPIRED (cron job)
        """
        try:
            now = timezone.now()
            expired = RegistrationRequest.objects.filter(
                status="PENDING",
                expires_at__lt=now
            )

            count = 0
            for request in expired:
                if request.mark_expired():
                    count += 1

                    # Notify requester
                    try:
                        from apps.notifications.services import NotificationService
                        NotificationService.send(
                            recipient=request.requester,
                            event="APPROVAL_REQUEST_EXPIRED",
                            title="Request Expired",
                            message=f"Your registration request for {request.tournament.name} has expired.",
                            action_url=f"/tournaments/{request.tournament.slug}/",
                            priority="LOW"
                        )
                    except Exception:
                        pass

            return count
        except Exception:
            return 0

    @staticmethod
    def get_pending_for_captain(captain) -> list:
        """
        Get all pending requests for a captain
        """
        try:
            return list(RegistrationRequest.objects.filter(
                captain=captain,
                status="PENDING"
            ).select_related("requester", "tournament", "team").order_by("-created_at"))
        except Exception:
            return []

    @staticmethod
    def get_user_requests(requester) -> list:
        """
        Get all requests made by a user
        """
        try:
            return list(RegistrationRequest.objects.filter(
                requester=requester
            ).select_related("captain", "tournament", "team").order_by("-created_at"))
        except Exception:
            return []
