"""
Unit tests for Help & Onboarding DTOs

Tests validation, serialization, and deserialization of help system DTOs.

Epic 7.6: Guidance & Help Overlays
"""

import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError
from apps.tournament_ops.dtos.help import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
    HelpBundleDTO
)


class TestHelpContentDTO:
    """Tests for HelpContentDTO validation and methods."""
    
    def test_valid_dto_creation(self):
        """Test creating valid HelpContentDTO."""
        dto = HelpContentDTO(
            id=1,
            content_type='tooltip',
            title='Create Tournament',
            content_body='Click to start creating your tournament.',
            page_identifier='organizer_dashboard',
            element_selector='#create-tournament-btn',
            display_priority=10,
            is_active=True,
            created_at=datetime(2025, 1, 1, 12, 0, 0)
        )
        
        assert dto.id == 1
        assert dto.content_type == 'tooltip'
        assert dto.title == 'Create Tournament'
        assert dto.page_identifier == 'organizer_dashboard'
        assert dto.is_active is True
    
    def test_immutability(self):
        """Test that DTOs are immutable."""
        dto = HelpContentDTO(
            id=1,
            content_type='article',
            title='Test',
            content_body='Body',
            page_identifier='test_page',
            element_selector=None,
            display_priority=5,
            is_active=True,
            created_at=datetime(2025, 1, 1)
        )
        
        with pytest.raises(FrozenInstanceError):
            dto.title = 'Modified'
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        dto = HelpContentDTO(
            id=2,
            content_type='article',
            title='Help Article',
            content_body='Article body content.',
            page_identifier='tournament_settings',
            element_selector=None,
            display_priority=20,
            is_active=True,
            created_at=datetime(2025, 1, 15, 14, 30, 0)
        )
        
        result = dto.to_dict()
        
        assert result['id'] == 2
        assert result['content_type'] == 'article'
        assert result['title'] == 'Help Article'
        assert result['content_body'] == 'Article body content.'
        assert result['page_identifier'] == 'tournament_settings'
        assert result['element_selector'] is None
        assert result['display_priority'] == 20
        assert result['is_active'] is True
        assert isinstance(result['created_at'], datetime)
    
    def test_tooltip_with_element_selector(self):
        """Test tooltip content type with element selector."""
        dto = HelpContentDTO(
            id=3,
            content_type='tooltip',
            title='Match Actions',
            content_body='Use these buttons to manage match state.',
            page_identifier='match_detail',
            element_selector='.match-actions-panel',
            display_priority=15,
            is_active=True,
            created_at=datetime(2025, 1, 20)
        )
        
        assert dto.content_type == 'tooltip'
        assert dto.element_selector == '.match-actions-panel'
        assert dto.title == 'Match Actions'


class TestHelpOverlayDTO:
    """Tests for HelpOverlayDTO."""
    
    def test_valid_overlay_creation(self):
        """Test creating valid HelpOverlayDTO."""
        dto = HelpOverlayDTO(
            id=1,
            overlay_key='bracket_intro',
            page_identifier='bracket_viewer',
            overlay_config={
                'steps': [
                    {'element': '#bracket-nav', 'title': 'Navigation', 'content': 'Use these controls.'},
                    {'element': '#match-card', 'title': 'Matches', 'content': 'Click to view details.'}
                ],
                'theme': 'dark',
                'position': 'center'
            },
            display_condition={'user_has_not_seen': True},
            is_active=True,
            created_at=datetime(2025, 1, 5)
        )
        
        assert dto.overlay_key == 'bracket_intro'
        assert dto.page_identifier == 'bracket_viewer'
        assert len(dto.overlay_config['steps']) == 2
        assert dto.display_condition['user_has_not_seen'] is True
    
    def test_to_dict_with_nested_config(self):
        """Test serialization preserves nested config structure."""
        dto = HelpOverlayDTO(
            id=2,
            overlay_key='first_tournament',
            page_identifier='organizer_dashboard',
            overlay_config={
                'welcome_message': 'Welcome to your first tournament!',
                'cta_button': 'Get Started'
            },
            display_condition={'tournament_count': 0},
            is_active=True,
            created_at=datetime(2025, 1, 10)
        )
        
        result = dto.to_dict()
        
        assert result['overlay_config']['welcome_message'] == 'Welcome to your first tournament!'
        assert result['display_condition']['tournament_count'] == 0


class TestOnboardingStepDTO:
    """Tests for OnboardingStepDTO."""
    
    def test_completed_step(self):
        """Test completed onboarding step."""
        dto = OnboardingStepDTO(
            step_key='create_first_tournament',
            is_completed=True,
            completed_at=datetime(2025, 1, 12, 10, 0, 0),
            is_dismissed=False,
            dismissed_at=None
        )
        
        assert dto.step_key == 'create_first_tournament'
        assert dto.is_completed is True
        assert dto.completed_at == datetime(2025, 1, 12, 10, 0, 0)
        assert dto.is_dismissed is False
    
    def test_dismissed_step(self):
        """Test dismissed onboarding step."""
        dto = OnboardingStepDTO(
            step_key='invite_staff',
            is_completed=False,
            completed_at=None,
            is_dismissed=True,
            dismissed_at=datetime(2025, 1, 13, 15, 30, 0)
        )
        
        assert dto.is_completed is False
        assert dto.is_dismissed is True
        assert dto.dismissed_at is not None
    
    def test_pending_step(self):
        """Test pending (not completed, not dismissed) step."""
        dto = OnboardingStepDTO(
            step_key='configure_bracket',
            is_completed=False,
            completed_at=None,
            is_dismissed=False,
            dismissed_at=None
        )
        
        assert dto.is_completed is False
        assert dto.is_dismissed is False
        assert dto.completed_at is None
        assert dto.dismissed_at is None


class TestHelpBundleDTO:
    """Tests for HelpBundleDTO aggregation."""
    
    def test_empty_bundle(self):
        """Test bundle with no content."""
        dto = HelpBundleDTO(
            help_content=[],
            overlays=[],
            onboarding_steps=[]
        )
        
        assert len(dto.help_content) == 0
        assert len(dto.overlays) == 0
        assert len(dto.onboarding_steps) == 0
    
    def test_full_bundle(self):
        """Test bundle with all content types."""
        help_content = [
            HelpContentDTO(
                id=1,
                content_type='tooltip',
                title='Test',
                content_body='Body',
                page_identifier='test_page',
                element_selector='#test',
                display_priority=10,
                is_active=True,
                created_at=datetime(2025, 1, 1)
            )
        ]
        
        overlays = [
            HelpOverlayDTO(
                id=1,
                overlay_key='test_overlay',
                page_identifier='test_page',
                overlay_config={'steps': []},
                display_condition={},
                is_active=True,
                created_at=datetime(2025, 1, 1)
            )
        ]
        
        onboarding_steps = [
            OnboardingStepDTO(
                step_key='step1',
                is_completed=True,
                completed_at=datetime(2025, 1, 1),
                is_dismissed=False,
                dismissed_at=None
            )
        ]
        
        dto = HelpBundleDTO(
            help_content=help_content,
            overlays=overlays,
            onboarding_steps=onboarding_steps
        )
        
        assert len(dto.help_content) == 1
        assert len(dto.overlays) == 1
        assert len(dto.onboarding_steps) == 1
        assert dto.help_content[0].title == 'Test'
        assert dto.overlays[0].overlay_key == 'test_overlay'
        assert dto.onboarding_steps[0].is_completed is True
    
    def test_to_dict_nested_structure(self):
        """Test serialization preserves nested DTO structure."""
        help_content = [
            HelpContentDTO(
                id=2,
                content_type='article',
                title='Article',
                content_body='Content',
                page_identifier='page1',
                element_selector=None,
                display_priority=5,
                is_active=True,
                created_at=datetime(2025, 1, 2)
            )
        ]
        
        dto = HelpBundleDTO(
            help_content=help_content,
            overlays=[],
            onboarding_steps=[]
        )
        
        result = dto.to_dict()
        
        assert 'help_content' in result
        assert 'overlays' in result
        assert 'onboarding_steps' in result
        assert len(result['help_content']) == 1
        assert result['help_content'][0]['title'] == 'Article'
