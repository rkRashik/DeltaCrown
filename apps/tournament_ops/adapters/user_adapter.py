"""
User/Profile service adapter for cross-domain user data access.

Provides TournamentOps with access to user profile data and eligibility checks
without direct imports from apps.user_profile.models or apps.accounts.models.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1, Epic 1.1
"""

from typing import Protocol, runtime_checkable

from .base import BaseAdapter
from apps.tournament_ops.dtos import UserProfileDTO


@runtime_checkable
class UserAdapterProtocol(Protocol):
    """
    Protocol defining the interface for user/profile data access.
    
    All methods return DTOs (not ORM models) to maintain clean domain boundaries.
    """
    
    def get_user_profile(self, user_id: int) -> UserProfileDTO:
        """
        Fetch user profile data by user ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfileDTO containing profile data and game identities
            
        Raises:
            UserNotFoundError: If user does not exist
        """
        ...
    
    def is_user_eligible(self, user_id: int, tournament_id: int) -> bool:
        """
        Check if user is eligible to register for a tournament.
        
        Eligibility checks may include:
        - User is not banned
        - User meets age requirements
        - User has verified required game identities
        - User is not already registered for this tournament
        
        Args:
            user_id: User identifier
            tournament_id: Tournament identifier
            
        Returns:
            bool: True if eligible, False otherwise
        """
        ...
    
    def is_user_banned(self, user_id: int) -> bool:
        """
        Check if user is currently banned from platform.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if banned, False otherwise
        """
        ...


class UserAdapter(BaseAdapter):
    """
    Concrete user adapter implementation.
    
    This adapter is the ONLY way for TournamentOps to access user/profile data.
    It must never return ORM models directly - only DTOs.
    
    Implementation Note:
    - Phase 1, Epic 1.1: Create adapter skeleton (this file)
    - Phase 1, Epic 1.3: Wire up DTOs ✓ (done)
    - Phase 1, Epic 1.4: Implement actual data fetching from user_profile domain
    - Phase 1, Epic 1.1: Add unit tests with mocked user service
    
    Reference: CLEANUP_AND_TESTING_PART_6.md - §4.4 (Service-Based APIs)
    """
    
    def get_user_profile(self, user_id: int) -> UserProfileDTO:
        """
        Fetch user profile data by user ID.
        
        Uses UserProfile model to fetch profile data and converts to UserProfileDTO.
        
        TODO: Replace with ProfileService when available.
        
        Raises:
            UserNotFoundError: If user does not exist
        """
        from apps.user_profile.models import UserProfile
        from apps.tournament_ops.exceptions import UserNotFoundError
        
        try:
            profile = UserProfile.objects.select_related('user').get(user_id=user_id)
            return UserProfileDTO.from_model(profile)
        except UserProfile.DoesNotExist:
            raise UserNotFoundError(f"User {user_id} not found")
    
    def is_user_eligible(self, user_id: int, tournament_id: int) -> bool:
        """
        Check if user is eligible to register for a tournament.
        
        Basic eligibility checks:
        - User profile exists
        - User is not banned (TODO: implement ban check when moderation available)
        - Email is verified (basic account validation)
        
        Note: Game-specific identity checks are done at team level.
        Note: Tournament-specific checks (already registered) are done by Tournament domain.
        
        TODO: Add age/region checks when tournament config DTOs are available.
        TODO: Integrate with moderation service for ban status.
        
        Returns:
            bool: True if eligible for basic registration, False otherwise
        """
        from apps.tournament_ops.exceptions import UserNotFoundError
        
        try:
            profile = self.get_user_profile(user_id)
            
            # Basic checks
            if not profile.email_verified:
                return False
            
            # TODO: Check ban status when ModerationService is available
            # For now, assume user is not banned if profile exists
            
            # TODO: Add age requirement check based on tournament config
            # TODO: Add region restriction check based on tournament config
            
            return True
        except UserNotFoundError:
            return False
    
    def is_user_banned(self, user_id: int) -> bool:
        """
        Check if user is currently banned from platform.
        
        TODO: Implement via ModerationService when available.
        For now, returns False (assume not banned).
        """
        # TODO: Call ModerationService.is_user_banned(user_id)
        # For Phase 1, we assume users are not banned
        return False
    
    def check_health(self) -> bool:
        """
        Check if user/profile service is accessible.
        
        Simple health check - attempt to query user_profile.
        """
        try:
            from apps.user_profile.models import UserProfile
            UserProfile.objects.exists()
            return True
        except Exception:
            return False
