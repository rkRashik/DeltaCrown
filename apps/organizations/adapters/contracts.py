"""
Adapter Contracts - Typed interfaces for dependent app integrations.

These contracts define the exact interface that dependent apps
(tournaments, notifications, etc.) expect from the team system.

Design Principles:
- Protocol-based (duck typing) for maximum flexibility
- Minimal dependencies (only stdlib typing)
- Performance-aware (document query expectations)
"""

from typing import Dict, Any, Optional, Protocol


class TeamURLProvider(Protocol):
    """
    Provides URL generation for team resources.
    
    Used by: notifications (team invite links, roster change notifications),
             user_profile (team cards), leaderboards (team rankings).
    
    Performance Contract: ≤1 query for vNext path, 0 queries for legacy path.
    """
    
    def get_team_url(self, team_id: int) -> str:
        """
        Generate absolute URL for team detail page.
        
        Args:
            team_id: Primary key of team (works for both legacy and vNext teams)
            
        Returns:
            Absolute URL string (e.g., "/organizations/protocol-v/" or "/teams/protocol-v/")
            
        Raises:
            NotFoundError: If team_id does not exist in either system
        
        Performance:
            - vNext path: 1 SELECT (Team by ID)
            - Legacy path: 0 queries (direct URL construction from cached slug)
        """
        ...


class TeamIdentityProvider(Protocol):
    """
    Provides display-ready team branding and metadata.
    
    Used by: tournaments (bracket generation), notifications (team mentions),
             user_profile (team cards), leaderboards (ranking displays).
    
    Performance Contract: ≤3 queries for vNext path, ≤2 queries for legacy path.
    """
    
    def get_team_identity(self, team_id: int) -> Dict[str, Any]:
        """
        Retrieve team branding and metadata for display purposes.
        
        Args:
            team_id: Primary key of team (works for both legacy and vNext teams)
            
        Returns:
            Dictionary with keys:
                - team_id: int
                - name: str
                - slug: str
                - logo_url: str
                - badge_url: Optional[str]  # Organization badge if applicable
                - game_name: str
                - game_id: int
                - region: str
                - is_verified: bool  # Organization verification status
                - is_org_team: bool  # True if vNext team
                - organization_name: Optional[str]
                - organization_slug: Optional[str]
                
        Raises:
            NotFoundError: If team_id does not exist in either system
        
        Performance:
            - vNext path: 1-2 SELECTs (Team + Organization with select_related)
            - Legacy path: 1 SELECT (Team with select_related('game'))
        """
        ...


class TeamRosterValidator(Protocol):
    """
    Validates team roster eligibility for tournament registration.
    
    Used by: tournaments (registration flow), tournament_ops (dashboard).
    
    Performance Contract: ≤5 queries for validation logic.
    """
    
    def validate_roster(
        self,
        team_id: int,
        tournament_id: Optional[int] = None,
        game_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate team roster meets tournament registration requirements.
        
        Args:
            team_id: Primary key of team (works for both legacy and vNext teams)
            tournament_id: Optional tournament ID for tournament-specific rules
            game_id: Optional game ID for game-specific validation
            
        Returns:
            Dictionary with keys:
                - is_valid: bool
                - errors: List[str]  # Blocking validation errors
                - warnings: List[str]  # Non-blocking warnings
                - roster_data: Dict[str, Any]  # Debug info for troubleshooting
                  - active_count: int
                  - required_slots: Dict[str, int]
                  - missing_slots: List[str]
                  - tournament_locks: List[Dict]  # Conflicting tournament registrations
                  
        Raises:
            NotFoundError: If team_id does not exist in either system
            
        Performance:
            - vNext path: ≤5 SELECTs (Team + Memberships + Tournament locks + Game Passports)
            - Legacy path: ≤4 SELECTs (same as current behavior)
        
        Validation Rules:
            - Minimum roster size (game-specific, typically 5-6 players)
            - Role distribution (e.g., 5 STARTER slots required)
            - Active membership status (ACTIVE members only)
            - Tournament locks (no overlapping tournament registrations)
            - Game Passport validity (if game requires verification)
        """
        ...
