"""
UP PHASE 8: Recruit Eligibility Service

Helper service to determine if a viewer can recruit a target user.
Checks if viewer is Team Owner or Manager of any active team.
"""
from django.contrib.auth import get_user_model
from typing import Optional
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class RecruitEligibilityService:
    """
    Service to check recruit eligibility for profile viewers.
    
    Business Rules:
    - Only Team OWNER or MANAGER can recruit
    - Must have at least one active team membership
    - Can recruit any user (no self-recruitment check needed)
    """
    
    @staticmethod
    def can_recruit(viewer_user: User, target_user: Optional[User] = None) -> bool:
        """
        Check if viewer can recruit (show recruit button).
        
        Args:
            viewer_user: User viewing the profile
            target_user: User being viewed (optional, for future restrictions)
            
        Returns:
            bool: True if viewer is Team Owner/Manager
        """
        if not viewer_user or not viewer_user.is_authenticated:
            return False
        
        try:
            # Import here to avoid circular imports
            from apps.organizations.models import TeamMembership
            
            # Check if viewer is OWNER or MANAGER of any active team
            is_recruiter = TeamMembership.objects.filter(
                user=viewer_user,
                role__in=[TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER],
                status=TeamMembership.Status.ACTIVE
            ).exists()
            
            logger.debug(
                f"Recruit eligibility check: viewer_id={viewer_user.id}, "
                f"can_recruit={is_recruiter}"
            )
            
            return is_recruiter
            
        except Exception as e:
            logger.error(f"Error checking recruit eligibility: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_recruiter_teams(viewer_user: User) -> list:
        """
        Get teams where viewer can recruit (OWNER or MANAGER).
        
        Args:
            viewer_user: User viewing the profile
            
        Returns:
            list: List of teams with recruitment permission
        """
        if not viewer_user or not viewer_user.is_authenticated:
            return []
        
        try:
            from apps.organizations.models import TeamMembership
            
            recruiter_teams = TeamMembership.objects.filter(
                user=viewer_user,
                role__in=[TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER],
                status=TeamMembership.Status.ACTIVE
            ).select_related('team').values_list('team__name', 'team__slug')
            
            return list(recruiter_teams)
            
        except Exception as e:
            logger.error(f"Error getting recruiter teams: {e}", exc_info=True)
            return []
