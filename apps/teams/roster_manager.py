# apps/teams/roster_manager.py
"""
Roster management utilities for game-specific teams.

Provides high-level API for managing team rosters with proper validation,
capacity checks, and role assignments.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from typing import Optional, Dict, Any, List

from .game_config import get_game_config, GAME_CONFIGS
from .validators import (
    validate_roster_capacity,
    validate_minimum_roster,
    validate_role_for_team,
    validate_starters_count,
    validate_substitutes_count,
    validate_unique_ign_in_team,
    validate_captain_is_member,
    validate_player_not_in_game_team,
    validate_tournament_roster_lock,
)
from .models.game_specific import (
    GAME_TEAM_MODELS,
    GAME_MEMBERSHIP_MODELS,
    get_team_model_for_game,
    get_membership_model_for_game,
)


class RosterManager:
    """
    High-level manager for team roster operations.
    
    Handles all roster modifications with proper validation and atomic transactions.
    """
    
    def __init__(self, team):
        """
        Initialize roster manager for a team.
        
        Args:
            team: Team instance to manage
        """
        self.team = team
        self.game_config = get_game_config(team.game)
        self.membership_model = get_membership_model_for_game(team.game)
    
    def add_player(
        self,
        profile,
        role: str,
        is_starter: bool = True,
        ign: Optional[str] = None,
        secondary_role: Optional[str] = None,
        **extra_data
    ) -> Any:
        """
        Add a player to the team roster.
        
        Args:
            profile: UserProfile of player to add
            role: Player's primary role
            is_starter: Whether player is a starter (vs substitute)
            ign: In-game name (optional)
            secondary_role: Secondary role (optional)
            **extra_data: Game-specific additional data
            
        Returns:
            Created membership instance
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            # Lock team for roster modifications
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            # Validate capacity
            validate_roster_capacity(team, adding_count=1, include_pending=True)
            
            # Validate player not already in another team
            validate_player_not_in_game_team(profile, team.game)
            
            # Validate role
            validate_role_for_team(team, role)
            
            if secondary_role:
                validate_role_for_team(team, secondary_role)
            
            # Validate starters/subs count
            if is_starter:
                validate_starters_count(team, True)
            else:
                validate_substitutes_count(team, False)
            
            # Validate IGN uniqueness
            if ign:
                validate_unique_ign_in_team(team, ign)
            
            # Create membership
            membership = self.membership_model.objects.create(
                team=team,
                profile=profile,
                role=role,
                secondary_role=secondary_role or "",
                is_starter=is_starter,
                in_game_name=ign or "",
                status='ACTIVE',
                **extra_data
            )
            
            return membership
    
    def remove_player(self, profile, reason: str = "Removed") -> None:
        """
        Remove a player from the team.
        
        Args:
            profile: UserProfile of player to remove
            reason: Reason for removal
            
        Raises:
            ValidationError: If player is captain or team would be below minimum
        """
        with transaction.atomic():
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            # Check if player is captain
            if team.captain == profile:
                raise ValidationError(
                    "Cannot remove team captain. Transfer captaincy first."
                )
            
            # Get membership
            try:
                membership = team.get_memberships().get(profile=profile, status='ACTIVE')
            except self.membership_model.DoesNotExist:
                raise ValidationError("Player is not an active member of this team.")
            
            # Check if removal would leave team below minimum
            remaining_count = team.get_memberships().filter(
                status='ACTIVE'
            ).exclude(pk=membership.pk).count()
            
            min_size = self.game_config.min_starters
            if remaining_count < min_size:
                raise ValidationError(
                    f"Cannot remove player. Team would have {remaining_count} members "
                    f"(minimum required: {min_size})."
                )
            
            # Mark as removed
            membership.status = 'REMOVED'
            membership.save()
    
    def promote_to_starter(self, profile) -> None:
        """
        Promote a substitute to starter.
        
        Args:
            profile: UserProfile of player to promote
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            try:
                membership = team.get_memberships().get(
                    profile=profile,
                    status='ACTIVE',
                    is_starter=False
                )
            except self.membership_model.DoesNotExist:
                raise ValidationError("Player is not an active substitute.")
            
            # Validate starters count
            validate_starters_count(team, True, membership.pk)
            
            # Promote
            membership.is_starter = True
            membership.save()
    
    def demote_to_substitute(self, profile) -> None:
        """
        Demote a starter to substitute.
        
        Args:
            profile: UserProfile of player to demote
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            try:
                membership = team.get_memberships().get(
                    profile=profile,
                    status='ACTIVE',
                    is_starter=True
                )
            except self.membership_model.DoesNotExist:
                raise ValidationError("Player is not an active starter.")
            
            # Check if player is captain
            if membership.is_captain:
                raise ValidationError("Cannot demote team captain to substitute.")
            
            # Check if demotion would leave team without enough starters
            remaining_starters = team.get_memberships().filter(
                status='ACTIVE',
                is_starter=True
            ).exclude(pk=membership.pk).count()
            
            if remaining_starters < self.game_config.min_starters:
                raise ValidationError(
                    f"Cannot demote. Team needs at least {self.game_config.min_starters} starters."
                )
            
            # Demote
            membership.is_starter = False
            membership.save()
    
    def transfer_captaincy(self, new_captain_profile) -> None:
        """
        Transfer team captaincy to another member.
        
        Args:
            new_captain_profile: UserProfile of new captain
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            # Validate new captain is active member
            try:
                new_captain_membership = team.get_memberships().get(
                    profile=new_captain_profile,
                    status='ACTIVE'
                )
            except self.membership_model.DoesNotExist:
                raise ValidationError("New captain must be an active team member.")
            
            # Get old captain membership
            old_captain = team.captain
            old_captain_membership = None
            
            if old_captain:
                try:
                    old_captain_membership = team.get_memberships().get(
                        profile=old_captain,
                        status='ACTIVE'
                    )
                except self.membership_model.DoesNotExist:
                    pass
            
            # Update memberships
            if old_captain_membership:
                old_captain_membership.is_captain = False
                old_captain_membership.role = "Player"  # Demote to regular player
                old_captain_membership.save()
            
            new_captain_membership.is_captain = True
            new_captain_membership.role = "Captain"
            new_captain_membership.save()
            
            # Update team captain
            team.captain = new_captain_profile
            team.save()
    
    def change_player_role(
        self,
        profile,
        new_role: str,
        new_secondary_role: Optional[str] = None
    ) -> None:
        """
        Change a player's role.
        
        Args:
            profile: UserProfile of player
            new_role: New primary role
            new_secondary_role: New secondary role (optional)
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            team = type(self.team).objects.select_for_update().get(pk=self.team.pk)
            
            try:
                membership = team.get_memberships().get(
                    profile=profile,
                    status='ACTIVE'
                )
            except self.membership_model.DoesNotExist:
                raise ValidationError("Player is not an active member.")
            
            # Validate new roles
            validate_role_for_team(team, new_role, membership.pk)
            
            if new_secondary_role:
                validate_role_for_team(team, new_secondary_role, membership.pk)
            
            # Update roles
            membership.role = new_role
            membership.secondary_role = new_secondary_role or ""
            membership.save()
    
    def get_roster_status(self) -> Dict[str, Any]:
        """
        Get current roster status and capacity information.
        
        Returns:
            Dictionary with roster status details
        """
        active_memberships = self.team.get_memberships().filter(status='ACTIVE')
        
        starters = active_memberships.filter(is_starter=True)
        substitutes = active_memberships.filter(is_starter=False)
        
        return {
            "total_members": active_memberships.count(),
            "starters": starters.count(),
            "substitutes": substitutes.count(),
            "max_total": self.game_config.max_starters + self.game_config.max_substitutes,
            "max_starters": self.game_config.max_starters,
            "max_substitutes": self.game_config.max_substitutes,
            "min_starters": self.game_config.min_starters,
            "can_add_starter": starters.count() < self.game_config.max_starters,
            "can_add_substitute": substitutes.count() < self.game_config.max_substitutes,
            "is_complete": active_memberships.count() >= self.game_config.min_starters,
            "is_full": active_memberships.count() >= (
                self.game_config.max_starters + self.game_config.max_substitutes
            ),
        }
    
    def get_available_roles(self, exclude_taken: bool = False) -> List[str]:
        """
        Get available roles for this team's game.
        
        Args:
            exclude_taken: If True, exclude roles already taken (for unique role games)
            
        Returns:
            List of available role names
        """
        all_roles = self.game_config.roles
        
        if not exclude_taken or not self.game_config.requires_unique_roles:
            return all_roles
        
        # For unique role games, exclude taken roles
        taken_roles = set(
            self.team.get_memberships().filter(
                status='ACTIVE',
                is_starter=True
            ).values_list('role', flat=True)
        )
        
        return [role for role in all_roles if role not in taken_roles]
    
    def validate_for_tournament(self) -> Dict[str, Any]:
        """
        Validate team roster is ready for tournament participation.
        
        Returns:
            Dictionary with validation results and issues
        """
        issues = []
        warnings = []
        
        status = self.get_roster_status()
        
        # Check minimum starters
        if status['starters'] < self.game_config.min_starters:
            issues.append(
                f"Team needs at least {self.game_config.min_starters} starters "
                f"(currently has {status['starters']})"
            )
        
        # Check captain
        if not self.team.captain:
            issues.append("Team must have a designated captain")
        
        # Check for unique roles (if required)
        if self.game_config.requires_unique_roles:
            roles = list(
                self.team.get_memberships().filter(
                    status='ACTIVE',
                    is_starter=True
                ).values_list('role', flat=True)
            )
            
            duplicates = [role for role in roles if roles.count(role) > 1]
            if duplicates:
                issues.append(
                    f"Duplicate roles found: {', '.join(set(duplicates))}. "
                    f"{self.game_config.name} requires unique roles."
                )
        
        # Check IGNs
        members_without_ign = self.team.get_memberships().filter(
            status='ACTIVE',
            in_game_name__isnull=True
        ).count() + self.team.get_memberships().filter(
            status='ACTIVE',
            in_game_name=""
        ).count()
        
        if members_without_ign > 0:
            warnings.append(
                f"{members_without_ign} player(s) don't have an in-game name set"
            )
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "roster_status": status,
        }


def get_roster_manager(team) -> RosterManager:
    """
    Get roster manager instance for a team.
    
    Args:
        team: Team instance
        
    Returns:
        RosterManager instance
    """
    return RosterManager(team)
