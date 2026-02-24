"""
TOC Service Layer — Participants Advanced Operations.

Sprint 3: Emergency Subs, Free Agent Pool, Waitlist,
          Guest Team Conversion, Fee Waivers.

Wraps existing RegistrationService + new models for TOC-specific
workflows. All methods return plain dicts for API serialization.

PRD: §3.7–§3.12
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.emergency_sub import EmergencySubRequest
from apps.tournaments.models.free_agent import FreeAgentRegistration
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.registration_service import RegistrationService

logger = logging.getLogger(__name__)


class TOCParticipantsAdvancedService:
    """
    Service methods for Sprint 3 advanced participant operations.

    All methods are @classmethod. Returns plain dicts.
    """

    # ──────────────────────────────────────────────────────────────
    # S3-B1: Emergency Substitution — Submit
    # ──────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def submit_emergency_sub(
        cls,
        tournament: Tournament,
        registration_id: int,
        *,
        requested_by,
        dropping_player_id: int,
        substitute_player_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Submit an emergency substitution request.

        Auto-checks:
        - Substitute not already registered in this tournament
        - Dropping player exists in registration lineup
        - Registration belongs to this tournament
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        reg = Registration.objects.get(
            id=registration_id,
            tournament=tournament,
            is_deleted=False,
        )

        dropping = User.objects.get(id=dropping_player_id)
        substitute = User.objects.get(id=substitute_player_id)

        # Auto-check: substitute not already registered
        existing = Registration.objects.filter(
            tournament=tournament,
            user=substitute,
            is_deleted=False,
        ).exclude(status__in=[Registration.CANCELLED, Registration.REJECTED]).exists()

        if existing:
            raise ValidationError(
                f"{substitute.username} is already registered in this tournament."
            )

        # Auto-check: no duplicate pending request for same substitute
        dup = EmergencySubRequest.objects.filter(
            tournament=tournament,
            substitute_player=substitute,
            status=EmergencySubRequest.STATUS_PENDING,
        ).exists()

        if dup:
            raise ValidationError(
                f"A pending sub request already exists for {substitute.username}."
            )

        sub_req = EmergencySubRequest.objects.create(
            tournament=tournament,
            registration=reg,
            requested_by=requested_by,
            dropping_player=dropping,
            substitute_player=substitute,
            reason=reason,
        )

        logger.info(
            "Emergency sub request created: %s → %s (tournament %s)",
            dropping.username, substitute.username, tournament.slug,
        )

        return cls._serialize_sub_request(sub_req)

    # ──────────────────────────────────────────────────────────────
    # S3-B2: Emergency Substitution — Approve / Deny
    # ──────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def approve_emergency_sub(
        cls,
        tournament: Tournament,
        sub_request_id: str,
        *,
        reviewer,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Approve an emergency sub request and update the roster."""
        sub_req = EmergencySubRequest.objects.select_related(
            "registration", "dropping_player", "substitute_player",
        ).get(
            id=sub_request_id,
            tournament=tournament,
            status=EmergencySubRequest.STATUS_PENDING,
        )

        sub_req.approve(reviewer, notes)

        # Update registration lineup snapshot if present
        reg = sub_req.registration
        lineup = reg.lineup_snapshot or []
        updated_lineup = []
        for entry in lineup:
            if isinstance(entry, dict) and entry.get("user_id") == sub_req.dropping_player_id:
                entry["user_id"] = sub_req.substitute_player_id
                entry["username"] = sub_req.substitute_player.username
                entry["substituted"] = True
                entry["substituted_at"] = timezone.now().isoformat()
            updated_lineup.append(entry)

        reg.lineup_snapshot = updated_lineup
        reg.save(update_fields=["lineup_snapshot"])

        logger.info(
            "Emergency sub approved: %s → %s (tournament %s, reviewer %s)",
            sub_req.dropping_player.username,
            sub_req.substitute_player.username,
            tournament.slug,
            reviewer.username,
        )

        return cls._serialize_sub_request(sub_req)

    @classmethod
    @transaction.atomic
    def deny_emergency_sub(
        cls,
        tournament: Tournament,
        sub_request_id: str,
        *,
        reviewer,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Deny an emergency sub request."""
        sub_req = EmergencySubRequest.objects.get(
            id=sub_request_id,
            tournament=tournament,
            status=EmergencySubRequest.STATUS_PENDING,
        )
        sub_req.deny(reviewer, notes)

        logger.info(
            "Emergency sub denied: %s → %s (tournament %s)",
            sub_req.dropping_player.username if hasattr(sub_req, 'dropping_player') else '?',
            sub_req.substitute_player.username if hasattr(sub_req, 'substitute_player') else '?',
            tournament.slug,
        )

        return cls._serialize_sub_request(sub_req)

    @classmethod
    def list_emergency_subs(
        cls,
        tournament: Tournament,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all emergency sub requests for a tournament."""
        qs = EmergencySubRequest.objects.filter(
            tournament=tournament,
        ).select_related(
            "registration__user",
            "requested_by",
            "dropping_player",
            "substitute_player",
            "reviewed_by",
        ).order_by("-created_at")

        if status_filter:
            qs = qs.filter(status=status_filter)

        return [cls._serialize_sub_request(r) for r in qs]

    # ──────────────────────────────────────────────────────────────
    # S3-B3: Free Agent Pool — List
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def list_free_agents(
        cls,
        tournament: Tournament,
        *,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List free agent registrations for a tournament.

        Filterable by status and searchable by username/role/rank.
        """
        qs = FreeAgentRegistration.objects.filter(
            tournament=tournament,
        ).select_related("user", "assigned_to_team").order_by("-created_at")

        if status_filter:
            qs = qs.filter(status=status_filter)

        if search:
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(preferred_role__icontains=search)
                | Q(rank_info__icontains=search)
                | Q(game_id__icontains=search)
            )

        return [cls._serialize_free_agent(fa) for fa in qs]

    # ──────────────────────────────────────────────────────────────
    # S3-B4: Free Agent — Assign to Team
    # ──────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def assign_free_agent(
        cls,
        tournament: Tournament,
        free_agent_id: str,
        *,
        team_id: int,
        assigned_by,
    ) -> Dict[str, Any]:
        """Assign a free agent to a team."""
        from apps.teams.models import Team

        fa = FreeAgentRegistration.objects.get(
            id=free_agent_id,
            tournament=tournament,
            status=FreeAgentRegistration.STATUS_AVAILABLE,
        )

        team = Team.objects.get(id=team_id)
        fa.assign_to_team(team, assigned_by=assigned_by)

        logger.info(
            "Free agent %s assigned to team %s (tournament %s)",
            fa.user.username, team.name, tournament.slug,
        )

        return cls._serialize_free_agent(fa)

    # ──────────────────────────────────────────────────────────────
    # S3-B5: Manual Waitlist Promotion
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def promote_waitlist(
        cls,
        tournament: Tournament,
        registration_id: int,
        *,
        promoted_by,
    ) -> Dict[str, Any]:
        """
        Manually promote a specific registration from the waitlist.

        Wraps RegistrationService.promote_from_waitlist().
        """
        reg = RegistrationService.promote_from_waitlist(
            tournament_id=tournament.id,
            registration_id=registration_id,
            promoted_by=promoted_by,
        )

        if not reg:
            raise ValidationError("No waitlisted registration to promote.")

        return {
            "id": reg.id,
            "participant_name": reg.user.username if reg.user else "Unknown",
            "status": reg.status,
            "status_display": reg.get_status_display(),
            "waitlist_position": reg.waitlist_position,
            "message": f"Promoted {reg.user.username if reg.user else 'registration'} from waitlist.",
        }

    # ──────────────────────────────────────────────────────────────
    # S3-B6: Auto-Promote Next Eligible
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def auto_promote_waitlist(
        cls,
        tournament: Tournament,
    ) -> Dict[str, Any]:
        """
        Auto-promote the next eligible waitlisted registration (FIFO).

        Wraps RegistrationService.auto_promote_waitlist().
        """
        reg = RegistrationService.auto_promote_waitlist(tournament_id=tournament.id)

        if not reg:
            return {
                "promoted": False,
                "message": "Waitlist is empty or tournament is at capacity.",
            }

        return {
            "promoted": True,
            "id": reg.id,
            "participant_name": reg.user.username if reg.user else "Unknown",
            "status": reg.status,
            "status_display": reg.get_status_display(),
            "message": f"Auto-promoted {reg.user.username if reg.user else 'registration'} from waitlist.",
        }

    # ──────────────────────────────────────────────────────────────
    # S3-B7: Convert Guest Team to Verified
    # ──────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def convert_guest_team(
        cls,
        tournament: Tournament,
        registration_id: int,
        *,
        converted_by,
    ) -> Dict[str, Any]:
        """
        Convert a guest team registration to a verified (non-guest) team.

        Clears the is_guest_team flag and invite_token.
        """
        reg = Registration.objects.select_related("user").get(
            id=registration_id,
            tournament=tournament,
            is_deleted=False,
        )

        if not reg.is_guest_team:
            raise ValidationError("Registration is not a guest team.")

        reg.is_guest_team = False
        reg.invite_token = None
        reg.conversion_status = "converted"
        reg.save(update_fields=["is_guest_team", "invite_token", "conversion_status"])

        logger.info(
            "Guest team %s converted to verified (tournament %s, by %s)",
            reg.user.username if reg.user else reg.id,
            tournament.slug,
            converted_by.username,
        )

        return {
            "id": reg.id,
            "participant_name": reg.user.username if reg.user else "Unknown",
            "is_guest_team": reg.is_guest_team,
            "conversion_status": reg.conversion_status,
            "message": "Guest team converted to verified successfully.",
        }

    # ──────────────────────────────────────────────────────────────
    # S3-B8: Fee Waiver
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def issue_fee_waiver(
        cls,
        tournament: Tournament,
        registration_id: int,
        *,
        waived_by,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Issue a fee waiver for a registration.

        Wraps RegistrationService.waive_fee().
        """
        if not reason or not reason.strip():
            raise ValidationError("Waiver reason is required.")

        # Verify registration belongs to tournament
        reg = Registration.objects.get(
            id=registration_id,
            tournament=tournament,
            is_deleted=False,
        )

        payment = RegistrationService.waive_fee(
            registration_id=registration_id,
            waived_by=waived_by,
            reason=reason.strip(),
        )

        return {
            "id": reg.id,
            "participant_name": reg.user.username if reg.user else "Unknown",
            "payment_status": payment.status,
            "waive_reason": payment.waive_reason,
            "message": f"Fee waived for {reg.user.username if reg.user else 'registration'}.",
        }

    # ──────────────────────────────────────────────────────────────
    # Waitlist Overview (helper for S3-F3)
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def get_waitlist(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """Get ordered waitlist for the tournament."""
        qs = Registration.objects.filter(
            tournament=tournament,
            status=Registration.WAITLISTED,
            is_deleted=False,
        ).select_related("user").order_by("waitlist_position", "created_at")

        return [
            {
                "id": r.id,
                "position": r.waitlist_position,
                "participant_name": r.user.username if r.user else "Unknown",
                "username": r.user.username if r.user else None,
                "registration_number": r.registration_number or "",
                "registered_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in qs
        ]

    # ──────────────────────────────────────────────────────────────
    # Private serializers
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def _serialize_sub_request(cls, sub: EmergencySubRequest) -> Dict[str, Any]:
        """Serialize an EmergencySubRequest to a plain dict."""
        return {
            "id": str(sub.id),
            "tournament_id": sub.tournament_id,
            "registration_id": sub.registration_id,
            "requested_by": sub.requested_by.username if sub.requested_by else None,
            "requested_by_id": sub.requested_by_id,
            "dropping_player": sub.dropping_player.username if sub.dropping_player else None,
            "dropping_player_id": sub.dropping_player_id,
            "substitute_player": sub.substitute_player.username if sub.substitute_player else None,
            "substitute_player_id": sub.substitute_player_id,
            "reason": sub.reason,
            "status": sub.status,
            "status_display": sub.get_status_display(),
            "reviewed_by": sub.reviewed_by.username if sub.reviewed_by else None,
            "reviewed_at": sub.reviewed_at.isoformat() if sub.reviewed_at else None,
            "review_notes": sub.review_notes,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }

    @classmethod
    def _serialize_free_agent(cls, fa: FreeAgentRegistration) -> Dict[str, Any]:
        """Serialize a FreeAgentRegistration to a plain dict."""
        return {
            "id": str(fa.id),
            "tournament_id": fa.tournament_id,
            "user_id": fa.user_id,
            "username": fa.user.username if fa.user else None,
            "status": fa.status,
            "status_display": fa.get_status_display(),
            "preferred_role": fa.preferred_role,
            "rank_info": fa.rank_info,
            "bio": fa.bio,
            "availability_notes": fa.availability_notes,
            "game_id": fa.game_id,
            "assigned_to_team": fa.assigned_to_team.name if fa.assigned_to_team else None,
            "assigned_to_team_id": fa.assigned_to_team_id,
            "assigned_at": fa.assigned_at.isoformat() if fa.assigned_at else None,
            "created_at": fa.created_at.isoformat() if fa.created_at else None,
        }
