"""
Team service adapter for cross-domain team data access.

Provides TournamentOps with access to team data and membership validation
without direct imports from apps.teams.models.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.1
"""

from typing import Protocol, runtime_checkable, List

from .base import BaseAdapter
from apps.tournament_ops.dtos import TeamDTO, ValidationResult
@runtime_checkable
class TeamAdapterProtocol(Protocol):
    """
    Protocol defining the interface for team data access.
    
    All methods return DTOs (not ORM models) to maintain clean domain boundaries.
    """
    
    def get_team(self, team_id: int) -> TeamDTO:
        """
        Fetch team data by ID.
        
        Args:
            team_id: Team identifier
            
        Returns:
            TeamDTO containing team data
            
        Raises:
            TeamNotFoundError: If team does not exist
        """
        ...
    
    def list_team_members(self, team_id: int) -> List[int]:
        """
        List all member user IDs for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            List of user IDs who are members of this team
        """
        ...
    
    def validate_membership(self, team_id: int, user_id: int) -> bool:
        """
        Check if user is a member of the team.
        
        Args:
            team_id: Team identifier
            user_id: User identifier
            
        Returns:
            bool: True if user is a team member, False otherwise
        """
        ...
    
    def validate_team_eligibility(
        self,
        team_id: int,
        tournament_id: int,
        game_id: int,
        required_team_size: int,
    ) -> ValidationResult:
        """
        Validate if team is eligible for a tournament.
        
        Args:
            team_id: Team identifier
            tournament_id: Tournament identifier
            game_id: Game identifier
            required_team_size: Required number of team members
            
        Returns:
            ValidationResult with is_valid flag and any error messages
        """
        ...


class TeamAdapter(BaseAdapter):
    """
    Concrete team adapter implementation.
    
    This adapter is the ONLY way for TournamentOps to access team data.
    It must never return ORM models directly - only DTOs.
    
    Implementation Note:
    - Phase 1, Epic 1.1: Create adapter skeleton (this file)
    - Phase 1, Epic 1.3: Wire up DTOs ✓ (done)
    - Phase 1, Epic 1.4: Implement actual data fetching from teams domain
    - Phase 1, Epic 1.1: Add unit tests with mocked team service
    
    Reference: CLEANUP_AND_TESTING_PART_6.md - §4.4 (Service-Based APIs)
    """
    
    def get_team(self, team_id: int) -> TeamDTO:
        """
        Fetch team data by ID.
        
        Uses TeamService from teams domain to fetch team data,
        then converts to TeamDTO using from_model().
        
        Raises:
            TeamNotFoundError: If team does not exist
        """
        from apps.teams.services.team_service import TeamService
        from apps.tournament_ops.exceptions import TeamNotFoundError
        
        try:
            team = TeamService.get_team_by_id(team_id)
            if not team:
                raise TeamNotFoundError(f"Team {team_id} not found")
            return TeamDTO.from_model(team)
        except Exception as e:
            if "not found" in str(e).lower() or isinstance(e, TeamNotFoundError):
                raise TeamNotFoundError(f"Team {team_id} not found")
            raise
    
    def list_team_members(self, team_id: int) -> List[int]:
        """
        List all member user IDs for a team.
        
        Returns list of user IDs who are active members.
        """
        team = self.get_team(team_id)  # Re-use get_team for validation
        return team.member_ids
    
    def validate_membership(self, team_id: int, user_id: int) -> bool:
        """
        Check if user is a member of the team.
        
        Returns True if user is an active member, False otherwise.
        """
        member_ids = self.list_team_members(team_id)
        return user_id in member_ids
    
    def validate_team_eligibility(
        self,
        team_id: int,
        tournament_id: int,
        game_id: int,
        required_team_size: int,
    ) -> ValidationResult:
        """
        Validate if team is eligible for a tournament.
        
        Checks:
        - Team exists and is verified
        - Team size meets requirement
        - Team game matches tournament game
        
        Note: Does NOT check "already registered" - that is handled by
        Tournament domain services in Phase 4 (RegistrationService).
        
        TODO (Phase 4): Add check for existing registration via TournamentService
        """
        from apps.tournament_ops.dtos.common import ValidationResult
        from apps.games.services.game_service import GameService
        
        errors = []
        
        # Get team data
        try:
            team = self.get_team(team_id)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Team not found: {str(e)}"]
            )
        
        # Check if team is verified
        if not team.is_verified:
            errors.append("Team must be verified to register for tournaments")
        
        # Check team size
        actual_size = len(team.member_ids)
        if actual_size < required_team_size:
            errors.append(
                f"Team has {actual_size} members but tournament requires {required_team_size}"
            )
        
        # Check game match
        game = GameService.get_game_by_id(game_id)
        if game and team.game != game.slug:
            errors.append(
                f"Team is registered for '{team.game}' but tournament is for '{game.slug}'"
            )
        
        # TODO (Phase 4): Check if team already registered for this tournament
        # This will be done via TournamentService.get_registration(team_id, tournament_id)
        # For now, we skip this check as it belongs to Tournament domain
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def check_health(self) -> bool:
        """
        Check if team service is accessible.
        
        Simple health check - attempt to query teams service.
        """
        try:
            from apps.teams.models._legacy import Team
            # Simple DB connectivity check
            Team.objects.exists()
            return True
        except Exception:
            return False
    
    def check_tournament_permission(self, user_id: int, team_id: int) -> bool:
        """
        Check if user has permission to register team for tournaments.
        
        Typically only team captain (owner) can register the team.
        
        TODO: Call TeamPermissionService when available in teams domain.
        For now, check if user is captain (in captain_id field).
        """
        team = self.get_team(team_id)
        return team.captain_id == user_id
