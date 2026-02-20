"""
Guest-to-Real Team Conversion Service (P4-T04)

Handles the lifecycle of converting guest team registrations into real
team registrations when invited members claim their slots.

Flow:
1. Organizer generates invite link for a guest registration
2. Invited members visit link, create accounts, verify Game IDs
3. When all members join → auto-convert to real team registration
4. Organizer can manually approve partial conversions
"""
import secrets
import logging
from typing import Dict, Optional, List

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import Registration

logger = logging.getLogger(__name__)


class GuestConversionService:
    """Service for guest-to-real team conversion."""

    # ------------------------------------------------------------------ #
    # Invite Link Generation
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def generate_invite_link(registration_id: int, organizer) -> Dict:
        """
        Generate a unique invite token for a guest team registration.

        Args:
            registration_id: Guest team Registration ID
            organizer: User performing the action (must be tournament organizer)

        Returns:
            dict with invite_token and invite_url

        Raises:
            ValidationError: If registration is not a guest team or already has a token
        """
        registration = Registration.objects.select_for_update().get(id=registration_id)

        if not registration.is_guest_team:
            raise ValidationError("Only guest team registrations can generate invite links.")

        if registration.status in (Registration.CANCELLED, Registration.REJECTED):
            raise ValidationError("Cannot generate invite link for cancelled/rejected registration.")

        # Generate token if not already present
        if not registration.invite_token:
            registration.invite_token = secrets.token_urlsafe(32)
            registration.conversion_status = Registration.CONVERSION_PENDING
            registration.save(update_fields=['invite_token', 'conversion_status'])

        return {
            'invite_token': registration.invite_token,
            'registration_id': registration.id,
            'tournament_slug': registration.tournament.slug,
        }

    # ------------------------------------------------------------------ #
    # Member Claim
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def claim_slot(invite_token: str, user, game_id: str) -> Dict:
        """
        Allow a user to claim a guest roster slot by verifying their Game ID.

        Args:
            invite_token: Invite token from the link
            user: Authenticated user claiming the slot
            game_id: User's in-game identifier to match against guest roster

        Returns:
            dict with status info (matched, total, remaining, auto_converted)

        Raises:
            ValidationError: If token invalid, already claimed, or game_id mismatch
        """
        try:
            registration = Registration.objects.select_for_update().get(
                invite_token=invite_token,
                is_guest_team=True,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError("Invalid or expired invite link.")

        if registration.status in (Registration.CANCELLED, Registration.REJECTED):
            raise ValidationError("This registration is no longer active.")

        roster = registration.lineup_snapshot or []
        if not roster:
            raise ValidationError("No roster data available for this guest team.")

        # Check if user already claimed a slot
        for member in roster:
            if member.get('claimed_by') == user.id:
                raise ValidationError("You have already claimed a slot in this team.")

        # Find matching roster slot by game_id (case-insensitive)
        matched_index = None
        for i, member in enumerate(roster):
            guest_ign = (member.get('game_id') or member.get('ign') or '').strip().lower()
            if guest_ign == game_id.strip().lower() and not member.get('claimed_by'):
                matched_index = i
                break

        if matched_index is None:
            # Check if game_id exists but already claimed
            for member in roster:
                guest_ign = (member.get('game_id') or member.get('ign') or '').strip().lower()
                if guest_ign == game_id.strip().lower():
                    raise ValidationError("This Game ID slot has already been claimed.")
            raise ValidationError(
                f"Game ID '{game_id}' does not match any unclaimed slot in the guest roster."
            )

        # Claim the slot
        roster[matched_index]['claimed_by'] = user.id
        roster[matched_index]['claimed_username'] = user.username
        roster[matched_index]['claimed_at'] = timezone.now().isoformat()
        registration.lineup_snapshot = roster

        # Calculate progress
        total = len(roster)
        claimed = sum(1 for m in roster if m.get('claimed_by'))
        remaining = total - claimed

        # Update conversion status
        if remaining == 0:
            registration.conversion_status = Registration.CONVERSION_COMPLETE
        else:
            registration.conversion_status = Registration.CONVERSION_PARTIAL

        registration.save(update_fields=['lineup_snapshot', 'conversion_status'])

        # Auto-convert if all members joined
        auto_converted = False
        if remaining == 0:
            auto_converted = GuestConversionService._auto_convert(registration)

        logger.info(
            "Slot claimed: reg=%s user=%s game_id=%s (%d/%d)",
            registration.id, user.username, game_id, claimed, total,
        )

        return {
            'success': True,
            'matched': True,
            'total_slots': total,
            'claimed_slots': claimed,
            'remaining_slots': remaining,
            'auto_converted': auto_converted,
            'conversion_status': registration.conversion_status,
            'tournament_name': registration.tournament.name,
        }

    # ------------------------------------------------------------------ #
    # Auto-Conversion
    # ------------------------------------------------------------------ #

    @staticmethod
    def _auto_convert(registration: Registration) -> bool:
        """
        Automatically convert a fully-claimed guest registration to a real one.

        Preserves seed position and bracket slot.
        """
        try:
            registration.is_guest_team = False
            registration.conversion_status = Registration.CONVERSION_COMPLETE
            registration.save(update_fields=['is_guest_team', 'conversion_status'])

            logger.info(
                "Auto-converted guest registration %s to real team (tournament=%s)",
                registration.id, registration.tournament.name,
            )
            return True
        except Exception as exc:
            logger.error("Auto-conversion failed for reg %s: %s", registration.id, exc)
            return False

    # ------------------------------------------------------------------ #
    # Manual Approval (Partial Conversion)
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def approve_partial_conversion(registration_id: int, organizer) -> Dict:
        """
        Organizer manually approves a partial guest conversion.

        Allows the registration to proceed even if not all slots are claimed.
        Preserves original seed position and bracket slot.

        Args:
            registration_id: Registration ID
            organizer: User performing the approval

        Returns:
            dict with conversion result

        Raises:
            ValidationError: If registration is not a guest team or not partially converted
        """
        registration = Registration.objects.select_for_update().get(id=registration_id)

        if not registration.is_guest_team:
            raise ValidationError("Registration is not a guest team.")

        if registration.conversion_status not in (
            Registration.CONVERSION_PARTIAL,
            Registration.CONVERSION_COMPLETE,
        ):
            raise ValidationError("No members have claimed slots yet.")

        roster = registration.lineup_snapshot or []
        claimed = sum(1 for m in roster if m.get('claimed_by'))
        total = len(roster)

        registration.is_guest_team = False
        registration.conversion_status = Registration.CONVERSION_APPROVED
        registration.save(update_fields=['is_guest_team', 'conversion_status'])

        logger.info(
            "Organizer %s approved partial conversion for reg %s (%d/%d claimed)",
            organizer.username, registration.id, claimed, total,
        )

        return {
            'success': True,
            'registration_id': registration.id,
            'claimed_slots': claimed,
            'total_slots': total,
            'seed': registration.seed,
            'slot_number': registration.slot_number,
        }

    # ------------------------------------------------------------------ #
    # Status Query
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_conversion_status(invite_token: str) -> Dict:
        """
        Get the current conversion status for a guest registration.

        Args:
            invite_token: Invite token

        Returns:
            dict with roster status and progress
        """
        try:
            registration = Registration.objects.select_related('tournament').get(
                invite_token=invite_token,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError("Invalid invite link.")

        roster = registration.lineup_snapshot or []
        total = len(roster)
        claimed = sum(1 for m in roster if m.get('claimed_by'))

        members = []
        for member in roster:
            members.append({
                'game_id': member.get('game_id') or member.get('ign', ''),
                'role': member.get('role', ''),
                'claimed': bool(member.get('claimed_by')),
                'claimed_by': member.get('claimed_username', ''),
            })

        return {
            'tournament_name': registration.tournament.name,
            'tournament_slug': registration.tournament.slug,
            'registration_id': registration.id,
            'conversion_status': registration.conversion_status,
            'total_slots': total,
            'claimed_slots': claimed,
            'remaining_slots': total - claimed,
            'members': members,
            'is_guest_team': registration.is_guest_team,
        }
