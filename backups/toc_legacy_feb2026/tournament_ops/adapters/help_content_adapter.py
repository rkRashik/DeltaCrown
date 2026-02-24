"""
Help Content Adapter

Phase 7, Epic 7.6: Guidance & Help Overlays
Data access layer for help content, overlays, and onboarding state.
Uses method-level ORM imports only.
"""

from typing import List, Optional, Protocol
from datetime import datetime
from apps.tournament_ops.dtos import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
)


class HelpContentAdapterProtocol(Protocol):
    """Protocol defining help content adapter interface."""
    
    def get_help_content_for_page(
        self, 
        page_id: str, 
        audience: str = 'global'
    ) -> List[HelpContentDTO]:
        """Get active help content for a specific page/scope and audience."""
        ...
    
    def get_overlays_for_page(self, page_id: str) -> List[HelpOverlayDTO]:
        """Get active overlays for a specific page."""
        ...
    
    def get_onboarding_state(
        self, 
        user_id: int, 
        tournament_id: Optional[int] = None
    ) -> List[OnboardingStepDTO]:
        """Get all onboarding steps for a user (optionally scoped to tournament)."""
        ...
    
    def mark_step_completed(
        self, 
        user_id: int, 
        step_key: str, 
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """Mark an onboarding step as completed."""
        ...
    
    def dismiss_step(
        self, 
        user_id: int, 
        step_key: str, 
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """Dismiss/skip an onboarding step."""
        ...


class HelpContentAdapter:
    """
    Concrete adapter for help content and onboarding data access.
    Uses method-level ORM imports to maintain architecture boundaries.
    """
    
    def get_help_content_for_page(
        self, 
        page_id: str, 
        audience: str = 'global'
    ) -> List[HelpContentDTO]:
        """
        Get active help content for a specific page/scope and audience.
        
        Args:
            page_id: Page/scope identifier (e.g., 'results_inbox', 'scheduling')
            audience: Target audience ('organizer', 'referee', 'player', 'global')
            
        Returns:
            List of HelpContentDTO instances
        """
        # Method-level ORM import
        from apps.siteui.models import HelpContent
        
        # Query for matching help content
        # Match by scope OR by audience (global content applies everywhere)
        help_items = HelpContent.objects.filter(
            is_active=True
        ).filter(
            models.Q(scope=page_id) | models.Q(audience='global')
        ).filter(
            models.Q(audience=audience) | models.Q(audience='global')
        ).order_by('display_order', 'title')
        
        # Import Q here
        from django.db import models
        
        # Re-query with Q (fix)
        help_items = HelpContent.objects.filter(
            is_active=True
        ).filter(
            models.Q(scope=page_id)
        ).filter(
            models.Q(audience=audience) | models.Q(audience='global')
        ).order_by('display_order', 'title')
        
        # Convert to DTOs
        return [HelpContentDTO.from_model(item) for item in help_items]
    
    def get_overlays_for_page(self, page_id: str) -> List[HelpOverlayDTO]:
        """
        Get active overlays for a specific page.
        
        Args:
            page_id: Page identifier (e.g., 'results_inbox', 'scheduling')
            
        Returns:
            List of HelpOverlayDTO instances
        """
        # Method-level ORM import
        from apps.siteui.models import HelpOverlay
        
        # Query for overlays on this page
        overlays = HelpOverlay.objects.filter(
            page_id=page_id,
            is_active=True
        ).select_related('help_content').order_by('display_order')
        
        # Convert to DTOs
        return [HelpOverlayDTO.from_model(overlay) for overlay in overlays]
    
    def get_onboarding_state(
        self, 
        user_id: int, 
        tournament_id: Optional[int] = None
    ) -> List[OnboardingStepDTO]:
        """
        Get all onboarding steps for a user (optionally scoped to tournament).
        
        Args:
            user_id: User ID
            tournament_id: Optional tournament ID for tournament-specific onboarding
            
        Returns:
            List of OnboardingStepDTO instances
        """
        # Method-level ORM import
        from apps.siteui.models import OrganizerOnboardingState
        
        # Query onboarding states
        query_filters = {'user_id': user_id}
        
        if tournament_id is not None:
            query_filters['tournament_id'] = tournament_id
        else:
            # Global onboarding (not tournament-specific)
            query_filters['tournament_id__isnull'] = True
        
        states = OrganizerOnboardingState.objects.filter(
            **query_filters
        ).order_by('created_at')
        
        # Convert to DTOs
        return [OnboardingStepDTO.from_model(state) for state in states]
    
    def mark_step_completed(
        self, 
        user_id: int, 
        step_key: str, 
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """
        Mark an onboarding step as completed.
        Creates the state record if it doesn't exist.
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier
            tournament_id: Optional tournament ID
            
        Returns:
            OnboardingStepDTO instance
        """
        # Method-level ORM import
        from apps.siteui.models import OrganizerOnboardingState
        from django.utils import timezone
        
        # Get or create the state record
        state, created = OrganizerOnboardingState.objects.get_or_create(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id,
            defaults={
                'completed_at': timezone.now(),
                'dismissed': False,
            }
        )
        
        # If it already existed, update completion time
        if not created and state.completed_at is None:
            state.completed_at = timezone.now()
            state.dismissed = False  # Clear dismissed flag if completing
            state.save(update_fields=['completed_at', 'dismissed', 'updated_at'])
        
        # Convert to DTO
        return OnboardingStepDTO.from_model(state)
    
    def dismiss_step(
        self, 
        user_id: int, 
        step_key: str, 
        tournament_id: Optional[int] = None
    ) -> OnboardingStepDTO:
        """
        Dismiss/skip an onboarding step.
        Creates the state record if it doesn't exist.
        
        Args:
            user_id: User ID
            step_key: Onboarding step identifier
            tournament_id: Optional tournament ID
            
        Returns:
            OnboardingStepDTO instance
        """
        # Method-level ORM import
        from apps.siteui.models import OrganizerOnboardingState
        from django.utils import timezone
        
        # Get or create the state record
        state, created = OrganizerOnboardingState.objects.get_or_create(
            user_id=user_id,
            step_key=step_key,
            tournament_id=tournament_id,
            defaults={
                'dismissed': True,
                'dismissed_at': timezone.now(),
            }
        )
        
        # If it already existed, update dismissal
        if not created and not state.dismissed:
            state.dismissed = True
            state.dismissed_at = timezone.now()
            state.save(update_fields=['dismissed', 'dismissed_at', 'updated_at'])
        
        # Convert to DTO
        return OnboardingStepDTO.from_model(state)
