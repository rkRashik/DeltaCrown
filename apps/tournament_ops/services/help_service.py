"""
Help and Onboarding Service

Phase 7, Epic 7.6: Guidance & Help Overlays
Business logic for help content, overlays, and organizer onboarding.
"""

from typing import Optional
from apps.tournament_ops.adapters import HelpContentAdapter
from apps.tournament_ops.dtos import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
    HelpBundleDTO,
)


class HelpAndOnboardingService:
    """
    Service for managing help content, overlays, and onboarding wizard.
    Orchestrates help system for organizer console.
    
    NO ORM IMPORTS - uses HelpContentAdapter only.
    """
    
    def __init__(self, help_content_adapter: HelpContentAdapter):
        """
        Initialize service with required adapter.
        
        Args:
            help_content_adapter: Adapter for help content data access
        """
        self.help_content_adapter = help_content_adapter
    
    def get_help_bundle(
        self,
        page_id: str,
        user_id: int,
        audience: str = 'organizer',
        tournament_id: Optional[int] = None
    ) -> HelpBundleDTO:
        """
        Get complete help bundle for a page.
        
        Combines:
        - Help content for the page
        - Overlays configured for the page
        - User's onboarding state (completed/pending steps)
        
        Args:
            page_id: Page identifier (e.g., 'results_inbox', 'scheduling')
            user_id: Current user ID
            audience: Target audience ('organizer', 'referee', 'player', 'global')
            tournament_id: Optional tournament ID for tournament-specific onboarding
            
        Returns:
            HelpBundleDTO with all help resources for the page
        """
        # Fetch help content for this page
        help_content = self.help_content_adapter.get_help_content_for_page(
            page_id=page_id,
            audience=audience
        )
        
        # Fetch overlays for this page
        overlays = self.help_content_adapter.get_overlays_for_page(
            page_id=page_id
        )
        
        # Fetch user's onboarding state
        onboarding_steps = self.help_content_adapter.get_onboarding_state(
            user_id=user_id,
            tournament_id=tournament_id
        )
        
        # Build bundle
        bundle = HelpBundleDTO(
            page_id=page_id,
            help_content=help_content,
            overlays=overlays,
            onboarding_steps=onboarding_steps,
        )
        
        # Calculate pending count
        bundle.calculate_pending_count()
        
        return bundle
    
    def complete_onboarding_step(
        self,
        user_id: int,
        step_key: str,
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """
        Mark an onboarding step as completed.
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier (e.g., 'results_inbox_intro')
            tournament_id: Optional tournament ID for tournament-specific steps
            
        Returns:
            OnboardingStepDTO representing the completed step
        """
        return self.help_content_adapter.mark_step_completed(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id
        )
    
    def dismiss_help_item(
        self,
        user_id: int,
        step_key: str,
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """
        Dismiss/skip an onboarding step or help item.
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier
            tournament_id: Optional tournament ID
            
        Returns:
            OnboardingStepDTO representing the dismissed step
        """
        return self.help_content_adapter.dismiss_step(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id
        )
    
    def get_onboarding_progress(
        self,
        user_id: int,
        tournament_id: Optional[int] = None
    ) -> dict:
        """
        Get summary of user's onboarding progress.
        
        Args:
            user_id: User ID
            tournament_id: Optional tournament ID
            
        Returns:
            Dictionary with progress summary:
            - total_steps: Total onboarding steps
            - completed: Number of completed steps
            - dismissed: Number of dismissed steps
            - pending: Number of pending steps
            - completion_percentage: Percentage complete (0-100)
        """
        steps = self.help_content_adapter.get_onboarding_state(
            user_id=user_id,
            tournament_id=tournament_id
        )
        
        total = len(steps)
        completed = sum(1 for step in steps if step.is_complete)
        dismissed = sum(1 for step in steps if step.dismissed)
        pending = sum(1 for step in steps if step.is_pending)
        
        completion_percentage = int((completed / total * 100)) if total > 0 else 0
        
        return {
            'total_steps': total,
            'completed': completed,
            'dismissed': dismissed,
            'pending': pending,
            'completion_percentage': completion_percentage,
        }
