# apps/teams/services/team_service.py
"""
Team Management Service Layer (Module 3.3)

Implements team lifecycle operations following ADR-001 (Service Layer Architecture).
Integrates Module 2.4 audit logging for all privileged actions.

Planning Reference: Documents/ExecutionPlan/Modules/MODULE_3.3_IMPLEMENTATION_PLAN.md

Traceability:
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer
- Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#adr-001
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.teams.models._legacy import Team, TeamMembership, TeamInvite, TEAM_MAX_ROSTER
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)

# Constants from planning doc
INVITE_EXPIRATION_HOURS = 72
TEAM_ROLE_CAPTAIN = "OWNER"  # Captain is stored as OWNER role
TEAM_ROLE_PLAYER = "PLAYER"
TEAM_INVITE_STATUS_PENDING = "PENDING"
TEAM_INVITE_STATUS_ACCEPTED = "ACCEPTED"
TEAM_INVITE_STATUS_DECLINED = "DECLINED"
TEAM_INVITE_STATUS_EXPIRED = "EXPIRED"


class TeamService:
    """
    Service layer for team management operations.
    
    All methods enforce business rules, validate permissions, and trigger
    appropriate audit logs and WebSocket events.
    """
    
    @staticmethod
    @transaction.atomic
    def create_team(
        name: str,
        captain_profile: UserProfile,
        game: str,
        tag: Optional[str] = None,
        description: str = "",
        **kwargs
    ) -> Team:
        """
        Create team with captain as first member.
        
        Business Rules:
        - Name must be unique
        - Slug auto-generated from name
        - Captain automatically added as first member with role='captain'
        - Team starts with is_active=True
        
        Args:
            name: Team name (must be unique)
            captain_profile: UserProfile who becomes captain
            game: Game identifier (from GAME_CHOICES)
            tag: Optional team tag/abbreviation (auto-generated if not provided)
            description: Optional team description
            **kwargs: Additional Team model fields (logo, region, etc.)
        
        Returns:
            Team: Created team instance
        
        Raises:
            ValidationError: If name already exists or validation fails
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation
        """
        # Validate name uniqueness
        if Team.objects.filter(name=name).exists():
            raise ValidationError(f"Team with name '{name}' already exists")
        
        # Generate slug from name
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Team.objects.filter(slug=slug, game=game).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Auto-generate tag if not provided
        if not tag:
            # Use first 3-5 characters of name as tag
            tag = "".join([c for c in name if c.isalnum()])[:5].upper()
            # Ensure tag uniqueness
            counter = 1
            original_tag = tag
            while Team.objects.filter(tag=tag).exists():
                tag = f"{original_tag}{counter}"
                counter += 1
        
        # Create team (Note: Team.save() automatically creates captain membership via ensure_captain_membership())
        team = Team.objects.create(
            name=name,
            tag=tag,
            slug=slug,
            game=game,
            captain=captain_profile,
            description=description,
            is_active=True,
            **kwargs
        )
        
        # Captain membership is auto-created by Team.save() -> ensure_captain_membership()
        # with role=OWNER, status=ACTIVE
        
        # Audit log
        logger.info(
            f"[AUDIT] Team created: team_id={team.id}, name={team.name}, "
            f"captain={captain_profile.user.username}, game={game}"
        )
        
        # WebSocket broadcast will be triggered by API layer
        # (following Module 3.2 pattern where views handle broadcasts)
        
        return team
    
    @staticmethod
    @transaction.atomic
    def invite_player(
        team: Team,
        invited_profile: UserProfile,
        invited_by_profile: UserProfile,
        role: str = TEAM_ROLE_PLAYER
    ) -> TeamInvite:
        """
        Send team invitation.
        
        Business Rules:
        - Only captain can invite
        - Team must not be full (active members + pending invites < TEAM_MAX_ROSTER)
        - Cannot invite user with existing pending invite
        - Cannot invite current team member
        - Invite expires after 72 hours
        
        Args:
            team: Team to invite player to
            invited_profile: UserProfile being invited
            invited_by_profile: UserProfile sending invitation (must be captain)
            role: Role for invitee (default: 'player')
            message: Optional invitation message
        
        Returns:
            TeamInvite: Created invitation
        
        Raises:
            PermissionDenied: If invited_by is not captain
            ValidationError: If team full, duplicate invite, or already member
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
        """
        # Validate captain permission
        if team.captain_id != invited_by_profile.id:
            raise PermissionDenied("Only team captain can invite players")
        
        # Check if user is already a member
        if TeamMembership.objects.filter(team=team, profile=invited_profile, status="ACTIVE").exists():
            raise ValidationError(f"{invited_profile.user.username} is already a team member")
        
        # Check for existing pending invite
        if TeamInvite.objects.filter(
            team=team,
            invited_user=invited_profile,
            status=TEAM_INVITE_STATUS_PENDING
        ).exists():
            raise ValidationError(f"{invited_profile.user.username} already has a pending invite from this team")
        
        # Check roster capacity
        active_members = TeamMembership.objects.filter(team=team, status="ACTIVE").count()
        pending_invites = TeamInvite.objects.filter(team=team, status=TEAM_INVITE_STATUS_PENDING).count()
        
        if (active_members + pending_invites) >= TEAM_MAX_ROSTER:
            raise ValidationError(
                f"Team roster full. Max {TEAM_MAX_ROSTER} members "
                f"(current: {active_members} active + {pending_invites} pending)"
            )
        
        # Create invite
        expires_at = timezone.now() + timedelta(hours=INVITE_EXPIRATION_HOURS)
        invite = TeamInvite.objects.create(
            team=team,
            invited_user=invited_profile,
            inviter=invited_by_profile,
            role=role,
            status=TEAM_INVITE_STATUS_PENDING,
            expires_at=expires_at
        )
        
        # Audit log
        logger.info(
            f"[AUDIT] Team invite sent: invite_id={invite.id}, team={team.name}, "
            f"invited_user={invited_profile.user.username}, inviter={invited_by_profile.user.username}, "
            f"expires_at={expires_at.isoformat()}"
        )
        
        # Notification trigger (Module 2.5 integration point)
        # TODO: Integrate notification system when Module 2.5 is available
        
        return invite
    
    @staticmethod
    @transaction.atomic
    def accept_invite(invite: TeamInvite, accepting_profile: UserProfile) -> TeamMembership:
        """
        Accept invitation and join team.
        
        Business Rules:
        - Only invited user can accept
        - Invite must not be expired
        - Team must not be full
        - Creates active membership
        - Updates invite status to 'accepted'
        
        Args:
            invite: TeamInvite to accept
            accepting_profile: UserProfile accepting (must match invited_user)
        
        Returns:
            TeamMembership: Created membership
        
        Raises:
            PermissionDenied: If accepting_profile is not the invited user
            ValidationError: If invite expired or team full
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
        """
        # Validate permission
        if invite.invited_user_id != accepting_profile.user_id:
            raise PermissionDenied("You can only accept invites sent to you")
        
        # Check invite status
        if invite.status != TEAM_INVITE_STATUS_PENDING:
            raise ValidationError(f"Invite is no longer pending (status: {invite.status})")
        
        # Check expiration
        if timezone.now() > invite.expires_at:
            invite.status = TEAM_INVITE_STATUS_EXPIRED
            invite.save(update_fields=["status"])
            raise ValidationError("Invite has expired")
        
        # Check roster capacity (final check before adding)
        active_members = TeamMembership.objects.filter(team=invite.team, status="ACTIVE").count()
        if active_members >= TEAM_MAX_ROSTER:
            raise ValidationError(f"Team roster is full (max {TEAM_MAX_ROSTER} members)")
        
        # Create membership
        membership = TeamMembership.objects.create(
            team=invite.team,
            profile=accepting_profile,
            role=invite.role,
            status="ACTIVE",
            joined_at=timezone.now()
        )
        
        # Update invite
        invite.status = TEAM_INVITE_STATUS_ACCEPTED
        invite.save(update_fields=["status"])
        
        # Audit log
        logger.info(
            f"[AUDIT] Team invite accepted: invite_id={invite.id}, team={invite.team.name}, "
            f"user={accepting_profile.user.username}, role={invite.role}"
        )
        
        # WebSocket broadcast handled by API layer
        
        return membership
    
    @staticmethod
    @transaction.atomic
    def decline_invite(invite: TeamInvite, declining_profile: UserProfile):
        """
        Decline invitation.
        
        Business Rules:
        - Only invited user can decline
        - Updates invite status to 'declined'
        - No WebSocket broadcast (silent decline per planning doc)
        
        Args:
            invite: TeamInvite to decline
            declining_profile: UserProfile declining (must match invited_user)
        
        Raises:
            PermissionDenied: If declining_profile is not the invited user
            ValidationError: If invite is not pending
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
        """
        # Validate permission
        if invite.invited_user_id != declining_profile.user_id:
            raise PermissionDenied("You can only decline invites sent to you")
        
        # Check invite status
        if invite.status != TEAM_INVITE_STATUS_PENDING:
            raise ValidationError(f"Invite is no longer pending (status: {invite.status})")
        
        # Update invite
        invite.status = TEAM_INVITE_STATUS_DECLINED
        invite.save(update_fields=["status"])
        
        # Audit log
        logger.info(
            f"[AUDIT] Team invite declined: invite_id={invite.id}, team={invite.team.name}, "
            f"user={declining_profile.user.username}"
        )
        
        # No WebSocket broadcast for declines (per planning doc)
    
    @staticmethod
    @transaction.atomic
    def remove_member(
        team: Team,
        member_profile: UserProfile,
        removed_by_profile: UserProfile
    ):
        """
        Remove team member.
        
        Business Rules:
        - Only captain can remove members
        - Cannot remove captain (must transfer first)
        - Deactivates membership (soft delete)
        
        Args:
            team: Team to remove member from
            member_profile: UserProfile being removed
            removed_by_profile: UserProfile performing removal (must be captain)
        
        Raises:
            PermissionDenied: If removed_by is not captain
            ValidationError: If trying to remove captain or member not found
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
        """
        # Validate captain permission
        if team.captain_id != removed_by_profile.id:
            raise PermissionDenied("Only team captain can remove members")
        
        # Check if trying to remove captain
        if member_profile.id == team.captain_id:
            raise ValidationError("Cannot remove team captain. Transfer captain role first.")
        
        # Find active membership
        try:
            membership = TeamMembership.objects.get(
                team=team,
                profile=member_profile,
                status="ACTIVE"
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError(f"{member_profile.user.username} is not an active member of this team")
        
        # Deactivate membership
        membership.status = "REMOVED"
        membership.save(update_fields=["status"])
        
        # Audit log
        logger.info(
            f"[AUDIT] Team member removed: team={team.name}, removed_user={member_profile.user.username}, "
            f"removed_by={removed_by_profile.user.username}"
        )
        
        # WebSocket broadcast and notification handled by API layer
    
    @staticmethod
    @transaction.atomic
    def leave_team(team: Team, leaving_profile: UserProfile):
        """
        Member leaves team voluntarily.
        
        Business Rules:
        - Captain cannot leave (must transfer or disband)
        - Deactivates membership
        
        Args:
            team: Team to leave
            leaving_profile: UserProfile leaving the team
        
        Raises:
            ValidationError: If captain tries to leave or not a member
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
        """
        # Check if captain
        if team.captain_id == leaving_profile.id:
            raise ValidationError("Captain cannot leave team. Transfer captain role or disband team.")
        
        # Find active membership
        try:
            membership = TeamMembership.objects.get(
                team=team,
                profile=leaving_profile,
                status="ACTIVE"
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError("You are not an active member of this team")
        
        # Deactivate membership
        membership.status = "REMOVED"
        membership.save(update_fields=["status"])
        
        # Audit log
        logger.info(
            f"[AUDIT] Team member left: team={team.name}, user={leaving_profile.user.username}"
        )
        
        # WebSocket broadcast handled by API layer
    
    @staticmethod
    @transaction.atomic
    def transfer_captain(
        team: Team,
        new_captain_profile: UserProfile,
        current_captain_profile: UserProfile
    ):
        """
        Transfer captain role to another member.
        
        Business Rules:
        - Only current captain can transfer
        - New captain must be active team member
        - Updates team.captain and both memberships
        - Old captain becomes regular player
        
        Args:
            team: Team to transfer captain for
            new_captain_profile: UserProfile to become new captain
            current_captain_profile: Current captain (must match team.captain)
        
        Raises:
            PermissionDenied: If current_captain is not the team captain
            ValidationError: If new_captain is not an active member
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer
        """
        # Validate current captain
        if team.captain_id != current_captain_profile.id:
            raise PermissionDenied("Only current captain can transfer captain role")
        
        # Validate new captain is active member
        try:
            new_captain_membership = TeamMembership.objects.get(
                team=team,
                profile=new_captain_profile,
                status="ACTIVE"
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError(f"{new_captain_profile.user.username} is not an active team member")
        
        # Get current captain membership
        try:
            current_captain_membership = TeamMembership.objects.get(
                team=team,
                profile=current_captain_profile,
                role=TEAM_ROLE_CAPTAIN,
                status="ACTIVE"
            )
        except TeamMembership.DoesNotExist:
            # Edge case: captain doesn't have membership record
            # Create it for consistency
            current_captain_membership = TeamMembership.objects.create(
                team=team,
                profile=current_captain_profile,
                role=TEAM_ROLE_CAPTAIN,
                status="ACTIVE",
                joined_at=team.created_at
            )
        
        # Update memberships (demote old captain FIRST to avoid unique constraint violation)
        current_captain_membership.role = TEAM_ROLE_PLAYER
        current_captain_membership.save(update_fields=["role"])
        
        new_captain_membership.role = TEAM_ROLE_CAPTAIN
        new_captain_membership.save(update_fields=["role"])
        
        # Update team captain
        team.captain = new_captain_profile
        team.save(update_fields=["captain"])
        
        # Audit log
        logger.info(
            f"[AUDIT] Captain transferred: team={team.name}, "
            f"old_captain={current_captain_profile.user.username}, "
            f"new_captain={new_captain_profile.user.username}"
        )
        
        # WebSocket broadcast handled by API layer
    
    @staticmethod
    @transaction.atomic
    def disband_team(team: Team, disbanding_profile: UserProfile):
        """
        Disband team (soft delete).
        
        Business Rules:
        - Only captain can disband
        - Cannot disband with active tournament registrations
        - Marks team as inactive
        - Deactivates all memberships
        
        Args:
            team: Team to disband
            disbanding_profile: UserProfile disbanding (must be captain)
        
        Raises:
            PermissionDenied: If disbanding_profile is not captain
            ValidationError: If team has active tournament registrations
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution
        """
        # Validate captain permission
        if team.captain_id != disbanding_profile.id:
            raise PermissionDenied("Only team captain can disband the team")
        
        # Check for active tournament registrations
        # Note: TeamTournamentRegistration is in apps.teams.models.tournament_integration
        from apps.teams.models.tournament_integration import TeamTournamentRegistration
        
        active_registrations = TeamTournamentRegistration.objects.filter(
            team=team,
            status__in=["pending", "confirmed", "checked_in"]
        ).count()
        
        if active_registrations > 0:
            raise ValidationError(
                f"Cannot disband team with {active_registrations} active tournament registration(s). "
                "Wait for tournaments to complete or withdraw registrations."
            )
        
        # Deactivate team
        team.is_active = False
        team.save(update_fields=["is_active"])
        
        # Deactivate all memberships
        TeamMembership.objects.filter(team=team, status="ACTIVE").update(status="REMOVED")
        
        # Audit log
        logger.info(
            f"[AUDIT] Team disbanded: team={team.name}, disbanded_by={disbanding_profile.user.username}, "
            f"member_count={TeamMembership.objects.filter(team=team).count()}"
        )
        
        # WebSocket broadcast and notifications handled by API layer
    
    @staticmethod
    def update_team(
        team: Team,
        updating_profile: UserProfile,
        **update_fields
    ) -> Team:
        """
        Update team fields.
        
        Business Rules:
        - Only captain can update team
        - Allowed fields: description, logo, banner_image, region, social links
        - Cannot update: name, tag, game (requires special procedures)
        
        Args:
            team: Team to update
            updating_profile: UserProfile performing update (must be captain)
            **update_fields: Fields to update
        
        Returns:
            Team: Updated team instance
        
        Raises:
            PermissionDenied: If updating_profile is not captain
            ValidationError: If trying to update restricted fields
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
        """
        # Validate captain permission
        if team.captain_id != updating_profile.id:
            raise PermissionDenied("Only team captain can update team details")
        
        # Whitelist of allowed update fields
        allowed_fields = {
            "description", "logo", "banner_image", "roster_image", "region",
            "twitter", "instagram", "discord", "youtube", "twitch", "linktree"
        }
        
        # Check for restricted fields
        restricted_fields = set(update_fields.keys()) - allowed_fields
        if restricted_fields:
            raise ValidationError(
                f"Cannot update restricted fields: {', '.join(restricted_fields)}. "
                "Allowed fields: " + ", ".join(allowed_fields)
            )
        
        # Apply updates
        for field, value in update_fields.items():
            setattr(team, field, value)
        
        team.save(update_fields=list(update_fields.keys()))
        
        # Audit log
        logger.info(
            f"[AUDIT] Team updated: team={team.name}, updated_by={updating_profile.user.username}, "
            f"fields={list(update_fields.keys())}"
        )
        
        return team
