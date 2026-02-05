"""
Team Invite Service - Phase D

Handles invite listing, acceptance, and decline operations for:
1. TeamMembership invites (status=INVITED)
2. TeamInvite records (email-based invites)
"""

from typing import Dict, List, Any, Optional
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from dataclasses import dataclass

from apps.organizations.models import Team, TeamMembership, TeamInvite, TeamMembershipEvent
from apps.organizations.choices import MembershipStatus, MembershipEventType

User = get_user_model()


# ============================================================================
# DTOs
# ============================================================================

@dataclass
class MembershipInviteDTO:
    """Represents a TeamMembership invite."""
    id: int
    team_id: int
    team_name: str
    team_slug: str
    game_name: str
    role: str
    inviter_name: Optional[str]
    created_at: str
    status: str


@dataclass
class EmailInviteDTO:
    """Represents a TeamInvite (email-based)."""
    token: str
    team_id: int
    team_name: str
    team_slug: str
    game_name: str
    role: str
    invited_email: str
    inviter_name: Optional[str]
    created_at: str
    expires_at: Optional[str]
    status: str


@dataclass
class InvitesListDTO:
    """Combined list of all invites for a user."""
    membership_invites: List[MembershipInviteDTO]
    email_invites: List[EmailInviteDTO]
    total_count: int


# ============================================================================
# Service Errors
# ============================================================================

class InviteServiceError(Exception):
    """Base exception for invite service errors."""
    def __init__(self, error_code: str, message: str, safe_message: str):
        self.error_code = error_code
        self.message = message
        self.safe_message = safe_message
        super().__init__(message)


class InviteNotFoundError(InviteServiceError):
    """Invite does not exist."""
    def __init__(self, message: str = "Invite not found"):
        super().__init__(
            error_code="INVITE_NOT_FOUND",
            message=message,
            safe_message="This invitation could not be found."
        )


class InviteExpiredError(InviteServiceError):
    """Invite has expired."""
    def __init__(self):
        super().__init__(
            error_code="INVITE_EXPIRED",
            message="Invite has expired",
            safe_message="This invitation has expired and can no longer be accepted."
        )


class InviteForbiddenError(InviteServiceError):
    """User not authorized to accept/decline this invite."""
    def __init__(self):
        super().__init__(
            error_code="INVITE_FORBIDDEN",
            message="User not authorized for this invite",
            safe_message="You are not authorized to respond to this invitation."
        )


class InviteAlreadyAcceptedError(InviteServiceError):
    """Invite already accepted (idempotent safe)."""
    def __init__(self):
        super().__init__(
            error_code="INVITE_ALREADY_ACCEPTED",
            message="Invite already accepted",
            safe_message="This invitation has already been accepted."
        )


# ============================================================================
# Team Invite Service
# ============================================================================

class TeamInviteService:
    """Service for managing team invitations."""
    
    @staticmethod
    def list_user_invites(user_id: int) -> InvitesListDTO:
        """
        List all pending invites for a user.
        
        Returns both:
        1. TeamMembership records with status=INVITED
        2. TeamInvite records matching user's email with status=PENDING
        
        Args:
            user_id: User ID to fetch invites for
            
        Returns:
            InvitesListDTO with membership_invites and email_invites
            
        Query Budget: ≤5 queries (optimized with prefetch_related)
        """
        from apps.games.models import Game
        
        user = User.objects.select_related().get(id=user_id)
        
        # 1. Membership invites (status=INVITED)
        membership_invites_qs = TeamMembership.objects.filter(
            user=user,
            status=MembershipStatus.INVITED
        ).select_related(
            'team',
            'team__organization'
        )
        
        # 2. Email invites (status=PENDING, matching user email)
        email_invites_qs = TeamInvite.objects.filter(
            invited_email__iexact=user.email,
            status='PENDING'
        ).select_related(
            'team',
            'inviter'
        )
        
        # Prefetch all games in ONE query
        all_team_ids = []
        all_team_ids.extend(m.team_id for m in membership_invites_qs)
        all_team_ids.extend(e.team_id for e in email_invites_qs)
        
        # Build game lookup dict (single query)
        game_lookup = {}
        if all_team_ids:
            from apps.organizations.models import Team
            teams_with_games = Team.objects.filter(
                id__in=all_team_ids
            ).select_related('game_id')
            
            for team in teams_with_games:
                if team.game_id:
                    game_lookup[team.id] = team.game_id.name
                else:
                    game_lookup[team.id] = "Unknown Game"
        
        # Convert membership invites
        membership_invites = []
        for invite in membership_invites_qs:
            game_name = game_lookup.get(invite.team_id, "Unknown Game")
            
            # Get inviter name (team creator or org name)
            inviter_name = None
            if invite.team.created_by:
                inviter_name = invite.team.created_by.username
            elif invite.team.organization:
                inviter_name = f"{invite.team.organization.name} (Org)"
            
            membership_invites.append(MembershipInviteDTO(
                id=invite.id,
                team_id=invite.team.id,
                team_name=invite.team.name,
                team_slug=invite.team.slug,
                game_name=game_name,
                role=invite.role,
                inviter_name=inviter_name,
                created_at=invite.joined_at.isoformat() if invite.joined_at else timezone.now().isoformat(),
                status=invite.status
            ))
        
        # Convert email invites (filter expired)
        email_invites = []
        for invite in email_invites_qs:
            # Mark expired if needed
            if invite.is_expired():
                invite.mark_expired_if_needed()
                continue  # Skip expired invites
            
            game_name = game_lookup.get(invite.team_id, "Unknown Game")
            inviter_name = invite.inviter.username if invite.inviter else None
            
            email_invites.append(EmailInviteDTO(
                token=str(invite.token),
                team_id=invite.team.id,
                team_name=invite.team.name,
                team_slug=invite.team.slug,
                game_name=game_name,
                role=invite.role,
                invited_email=invite.invited_email,
                inviter_name=inviter_name,
                created_at=invite.created_at.isoformat(),
                expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
                status=invite.status
            ))
        
        return InvitesListDTO(
            membership_invites=membership_invites,
            email_invites=email_invites,
            total_count=len(membership_invites) + len(email_invites)
        )
    
    @staticmethod
    @transaction.atomic
    def accept_membership_invite(membership_id: int, actor_user_id: int) -> Dict[str, Any]:
        """
        Accept a TeamMembership invite.
        
        Changes status from INVITED → ACTIVE.
        
        Args:
            membership_id: TeamMembership ID
            actor_user_id: User accepting the invite
            
        Returns:
            Dict with team_id, team_slug, team_url
            
        Raises:
            InviteNotFoundError: Membership doesn't exist
            InviteForbiddenError: User not authorized
            InviteAlreadyAcceptedError: Already accepted (idempotent)
            
        Query Budget: ≤6 queries
        """
        # Lock row to prevent race conditions
        try:
            membership = TeamMembership.objects.select_for_update().select_related('team').get(
                id=membership_id
            )
        except TeamMembership.DoesNotExist:
            raise InviteNotFoundError("Membership invite not found")
        
        # Security check: only invited user can accept
        if membership.user_id != actor_user_id:
            raise InviteForbiddenError()
        
        # Idempotent: if already ACTIVE, return success
        if membership.status == MembershipStatus.ACTIVE:
            raise InviteAlreadyAcceptedError()
        
        # Must be INVITED status
        if membership.status != MembershipStatus.INVITED:
            raise InviteNotFoundError("Invite is not in pending state")
        
        # Accept: change status to ACTIVE
        membership.status = MembershipStatus.ACTIVE
        membership.save(update_fields=['status'])
        
        # Create JOINED event for audit trail
        TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=membership.user,
            actor=membership.user,  # User accepted their own invite
            event_type=MembershipEventType.JOINED,
            new_role=membership.role,
            new_status=MembershipStatus.ACTIVE,
            metadata={'invite_accepted': True, 'invite_type': 'membership'},
        )
        
        # Return team details
        team = membership.team
        team_url = team.get_absolute_url()
        
        return {
            'team_id': team.id,
            'team_slug': team.slug,
            'team_name': team.name,
            'team_url': team_url,
            'role': membership.role,
        }
    
    @staticmethod
    @transaction.atomic
    def decline_membership_invite(membership_id: int, actor_user_id: int) -> Dict[str, Any]:
        """
        Decline a TeamMembership invite.
        
        Changes status from INVITED → DECLINED (soft delete).
        
        Args:
            membership_id: TeamMembership ID
            actor_user_id: User declining the invite
            
        Returns:
            Dict with success=True
            
        Raises:
            InviteNotFoundError: Membership doesn't exist
            InviteForbiddenError: User not authorized
            
        Query Budget: ≤6 queries
        """
        # Lock row
        try:
            membership = TeamMembership.objects.select_for_update().get(id=membership_id)
        except TeamMembership.DoesNotExist:
            raise InviteNotFoundError("Membership invite not found")
        
        # Security check
        if membership.user_id != actor_user_id:
            raise InviteForbiddenError()
        
        # Must be INVITED status
        if membership.status != MembershipStatus.INVITED:
            raise InviteNotFoundError("Invite is not in pending state")
        
        # Decline: soft delete by changing status
        membership.status = 'DECLINED'
        membership.save(update_fields=['status'])
        
        return {'success': True}
    
    @staticmethod
    @transaction.atomic
    def accept_email_invite(token: str, actor_user_id: int) -> Dict[str, Any]:
        """
        Accept an email-based TeamInvite.
        
        Creates TeamMembership with ACTIVE status and marks invite ACCEPTED.
        
        Args:
            token: UUID token from TeamInvite
            actor_user_id: User accepting the invite
            
        Returns:
            Dict with team_id, team_slug, team_url
            
        Raises:
            InviteNotFoundError: Token invalid
            InviteExpiredError: Invite expired
            InviteForbiddenError: Email doesn't match
            InviteAlreadyAcceptedError: Already accepted
            
        Query Budget: ≤6 queries
        """
        user = User.objects.get(id=actor_user_id)
        
        # Lock row
        try:
            invite = TeamInvite.objects.select_for_update().select_related('team').get(
                token=token
            )
        except TeamInvite.DoesNotExist:
            raise InviteNotFoundError("Email invite not found")
        
        # Check expiry
        if invite.is_expired():
            invite.mark_expired_if_needed()
            raise InviteExpiredError()
        
        # Security check: email must match
        if invite.invited_email.lower() != user.email.lower():
            raise InviteForbiddenError()
        
        # Check status
        if invite.status == 'ACCEPTED':
            raise InviteAlreadyAcceptedError()
        
        if invite.status != 'PENDING':
            raise InviteNotFoundError("Invite is not in pending state")
        
        # Check if user already has membership (edge case: invited via both methods)
        existing_membership = TeamMembership.objects.filter(
            team=invite.team,
            user=user
        ).first()
        
        if existing_membership:
            if existing_membership.status == MembershipStatus.ACTIVE:
                # Already a member - just mark invite accepted
                invite.status = 'ACCEPTED'
                invite.responded_at = timezone.now()
                invite.save(update_fields=['status', 'responded_at'])
                raise InviteAlreadyAcceptedError()
            else:
                # Reactivate existing membership
                existing_membership.status = MembershipStatus.ACTIVE
                existing_membership.role = invite.role
                existing_membership.save(update_fields=['status', 'role'])
                
                # Create JOINED event for reactivation
                TeamMembershipEvent.objects.create(
                    membership=existing_membership,
                    team=invite.team,
                    user=user,
                    actor=user,
                    event_type=MembershipEventType.JOINED,
                    new_role=invite.role,
                    new_status=MembershipStatus.ACTIVE,
                    metadata={'invite_accepted': True, 'invite_type': 'email', 'reactivated': True},
                )
        else:
            # Create new membership
            membership = TeamMembership.objects.create(
                team=invite.team,
                user=user,
                role=invite.role,
                status=MembershipStatus.ACTIVE
            )
            
            # Create JOINED event for new membership
            TeamMembershipEvent.objects.create(
                membership=membership,
                team=invite.team,
                user=user,
                actor=user,
                event_type=MembershipEventType.JOINED,
                new_role=invite.role,
                new_status=MembershipStatus.ACTIVE,
                metadata={'invite_accepted': True, 'invite_type': 'email'},
            )
        
        # Mark invite accepted
        invite.status = 'ACCEPTED'
        invite.responded_at = timezone.now()
        invite.invited_user = user  # Link user
        invite.save(update_fields=['status', 'responded_at', 'invited_user'])
        
        # Return team details
        team = invite.team
        team_url = team.get_absolute_url()
        
        return {
            'team_id': team.id,
            'team_slug': team.slug,
            'team_name': team.name,
            'team_url': team_url,
            'role': invite.role,
        }
    
    @staticmethod
    @transaction.atomic
    def decline_email_invite(token: str, actor_user_id: int) -> Dict[str, Any]:
        """
        Decline an email-based TeamInvite.
        
        Marks invite as DECLINED.
        
        Args:
            token: UUID token from TeamInvite
            actor_user_id: User declining the invite
            
        Returns:
            Dict with success=True
            
        Raises:
            InviteNotFoundError: Token invalid
            InviteForbiddenError: Email doesn't match
            
        Query Budget: ≤6 queries
        """
        user = User.objects.get(id=actor_user_id)
        
        # Lock row
        try:
            invite = TeamInvite.objects.select_for_update().get(token=token)
        except TeamInvite.DoesNotExist:
            raise InviteNotFoundError("Email invite not found")
        
        # Security check
        if invite.invited_email.lower() != user.email.lower():
            raise InviteForbiddenError()
        
        # Must be PENDING
        if invite.status != 'PENDING':
            raise InviteNotFoundError("Invite is not in pending state")
        
        # Decline
        invite.status = 'DECLINED'
        invite.responded_at = timezone.now()
        invite.save(update_fields=['status', 'responded_at'])
        
        return {'success': True}
