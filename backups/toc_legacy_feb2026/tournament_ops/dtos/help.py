"""
Data Transfer Objects (DTOs) for Help & Onboarding System

Phase 7, Epic 7.6: Guidance & Help Overlays
Provides DTOs for help content, overlays, and onboarding state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class HelpContentDTO:
    """
    DTO for help content/documentation.
    Represents a single help article or tooltip content.
    """
    content_id: int
    key: str
    scope: str
    title: str
    body: str
    html_body: Optional[str] = None
    audience: str = 'global'
    is_active: bool = True
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, help_content) -> 'HelpContentDTO':
        """
        Convert HelpContent model instance to DTO.
        
        Args:
            help_content: HelpContent model instance
            
        Returns:
            HelpContentDTO instance
        """
        return cls(
            content_id=help_content.id,
            key=help_content.key,
            scope=help_content.scope,
            title=help_content.title,
            body=help_content.body,
            html_body=help_content.html_body,
            audience=help_content.audience,
            is_active=help_content.is_active,
            display_order=help_content.display_order,
            created_at=help_content.created_at,
            updated_at=help_content.updated_at,
        )
    
    def validate(self):
        """Validate DTO fields."""
        if not self.key:
            raise ValueError("key is required")
        if not self.scope:
            raise ValueError("scope is required")
        if not self.title:
            raise ValueError("title is required")
        if not self.body:
            raise ValueError("body is required")
        if self.content_id and self.content_id <= 0:
            raise ValueError("content_id must be positive if provided")
        if self.audience not in ['organizer', 'referee', 'player', 'global']:
            raise ValueError("audience must be one of: organizer, referee, player, global")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'content_id': self.content_id,
            'key': self.key,
            'scope': self.scope,
            'title': self.title,
            'body': self.body,
            'html_body': self.html_body,
            'audience': self.audience,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class HelpOverlayDTO:
    """
    DTO for help overlay/tooltip placement.
    Defines where and how a help item should appear on a page.
    """
    overlay_id: int
    help_content_key: str
    help_content_title: str
    help_content_body: str
    page_id: str
    placement: str = 'top-right'
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, help_overlay) -> 'HelpOverlayDTO':
        """
        Convert HelpOverlay model instance to DTO.
        
        Args:
            help_overlay: HelpOverlay model instance
            
        Returns:
            HelpOverlayDTO instance
        """
        return cls(
            overlay_id=help_overlay.id,
            help_content_key=help_overlay.help_content.key,
            help_content_title=help_overlay.help_content.title,
            help_content_body=help_overlay.help_content.body,
            page_id=help_overlay.page_id,
            placement=help_overlay.placement,
            config=help_overlay.config or {},
            is_active=help_overlay.is_active,
            display_order=help_overlay.display_order,
            created_at=help_overlay.created_at,
            updated_at=help_overlay.updated_at,
        )
    
    def validate(self):
        """Validate DTO fields."""
        if not self.help_content_key:
            raise ValueError("help_content_key is required")
        if not self.page_id:
            raise ValueError("page_id is required")
        if self.overlay_id and self.overlay_id <= 0:
            raise ValueError("overlay_id must be positive if provided")
        valid_placements = ['top', 'top-right', 'right', 'bottom-right', 'bottom', 
                           'bottom-left', 'left', 'top-left', 'center']
        if self.placement not in valid_placements:
            raise ValueError(f"placement must be one of: {', '.join(valid_placements)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'overlay_id': self.overlay_id,
            'help_content_key': self.help_content_key,
            'help_content_title': self.help_content_title,
            'help_content_body': self.help_content_body,
            'page_id': self.page_id,
            'placement': self.placement,
            'config': self.config,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class OnboardingStepDTO:
    """
    DTO for organizer onboarding step state.
    Tracks completion/dismissal of individual onboarding steps.
    """
    state_id: Optional[int]
    user_id: int
    tournament_id: Optional[int]
    step_key: str
    completed_at: Optional[datetime] = None
    dismissed: bool = False
    dismissed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, onboarding_state) -> 'OnboardingStepDTO':
        """
        Convert OrganizerOnboardingState model instance to DTO.
        
        Args:
            onboarding_state: OrganizerOnboardingState model instance
            
        Returns:
            OnboardingStepDTO instance
        """
        return cls(
            state_id=onboarding_state.id,
            user_id=onboarding_state.user_id,
            tournament_id=onboarding_state.tournament_id,
            step_key=onboarding_state.step_key,
            completed_at=onboarding_state.completed_at,
            dismissed=onboarding_state.dismissed,
            dismissed_at=onboarding_state.dismissed_at,
            created_at=onboarding_state.created_at,
            updated_at=onboarding_state.updated_at,
        )
    
    def validate(self):
        """Validate DTO fields."""
        if not self.step_key:
            raise ValueError("step_key is required")
        if self.user_id and self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if self.tournament_id and self.tournament_id <= 0:
            raise ValueError("tournament_id must be positive if provided")
        if self.state_id and self.state_id <= 0:
            raise ValueError("state_id must be positive if provided")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'state_id': self.state_id,
            'user_id': self.user_id,
            'tournament_id': self.tournament_id,
            'step_key': self.step_key,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'dismissed': self.dismissed,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def is_complete(self) -> bool:
        """Check if step is completed."""
        return self.completed_at is not None
    
    @property
    def is_pending(self) -> bool:
        """Check if step is still pending (not completed and not dismissed)."""
        return not self.is_complete and not self.dismissed


@dataclass
class HelpBundleDTO:
    """
    DTO for complete help bundle for a page.
    Combines help content, overlays, and onboarding state for a single page/context.
    """
    page_id: str
    help_content: List[HelpContentDTO] = field(default_factory=list)
    overlays: List[HelpOverlayDTO] = field(default_factory=list)
    onboarding_steps: List[OnboardingStepDTO] = field(default_factory=list)
    pending_onboarding_count: int = 0
    
    def validate(self):
        """Validate DTO fields."""
        if not self.page_id:
            raise ValueError("page_id is required")
        
        # Validate nested DTOs
        for content in self.help_content:
            content.validate()
        for overlay in self.overlays:
            overlay.validate()
        for step in self.onboarding_steps:
            step.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary."""
        return {
            'page_id': self.page_id,
            'help_content': [c.to_dict() for c in self.help_content],
            'overlays': [o.to_dict() for o in self.overlays],
            'onboarding_steps': [s.to_dict() for s in self.onboarding_steps],
            'pending_onboarding_count': self.pending_onboarding_count,
        }
    
    def calculate_pending_count(self):
        """Calculate number of pending onboarding steps and update count."""
        self.pending_onboarding_count = sum(1 for step in self.onboarding_steps if step.is_pending)
