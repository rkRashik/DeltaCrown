"""
Unit tests for HelpContentAdapter

Tests data access layer for help content and onboarding state.

Epic 7.6: Guidance & Help Overlays
"""

import pytest
from datetime import datetime
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament
from apps.siteui.models import HelpContent, HelpOverlay, OrganizerOnboardingState
from apps.tournament_ops.adapters.help_content_adapter import HelpContentAdapter
from apps.tournament_ops.dtos.help import HelpContentDTO, HelpOverlayDTO, OnboardingStepDTO

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username='test_organizer',
        email='organizer@test.com',
        password='password123'
    )


@pytest.fixture
def tournament(db, user):
    """Create test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        organizer=user,
        status='active'
    )


@pytest.fixture
def adapter():
    """Create adapter instance."""
    return HelpContentAdapter()


@pytest.mark.django_db
class TestGetHelpContentForPage:
    """Tests for get_help_content_for_page method."""
    
    def test_returns_active_content_for_page(self, adapter, tournament):
        """Test returns only active content for specified page."""
        # Create active content for target page
        HelpContent.objects.create(
            content_type='tooltip',
            title='Page Help',
            content_body='Help for this page.',
            page_identifier='organizer_dashboard',
            display_priority=10,
            is_active=True
        )
        
        # Create inactive content (should not be returned)
        HelpContent.objects.create(
            content_type='tooltip',
            title='Inactive Help',
            content_body='Inactive.',
            page_identifier='organizer_dashboard',
            display_priority=5,
            is_active=False
        )
        
        # Create content for different page (should not be returned)
        HelpContent.objects.create(
            content_type='article',
            title='Other Page',
            content_body='Different page.',
            page_identifier='tournament_settings',
            display_priority=15,
            is_active=True
        )
        
        result = adapter.get_help_content_for_page('organizer_dashboard')
        
        assert len(result) == 1
        assert isinstance(result[0], HelpContentDTO)
        assert result[0].title == 'Page Help'
        assert result[0].is_active is True
    
    def test_orders_by_display_priority(self, adapter):
        """Test results ordered by display_priority descending."""
        HelpContent.objects.create(
            content_type='tooltip',
            title='Low Priority',
            content_body='Low.',
            page_identifier='test_page',
            display_priority=5,
            is_active=True
        )
        
        HelpContent.objects.create(
            content_type='tooltip',
            title='High Priority',
            content_body='High.',
            page_identifier='test_page',
            display_priority=20,
            is_active=True
        )
        
        HelpContent.objects.create(
            content_type='tooltip',
            title='Medium Priority',
            content_body='Medium.',
            page_identifier='test_page',
            display_priority=10,
            is_active=True
        )
        
        result = adapter.get_help_content_for_page('test_page')
        
        assert len(result) == 3
        assert result[0].title == 'High Priority'
        assert result[1].title == 'Medium Priority'
        assert result[2].title == 'Low Priority'
    
    def test_returns_empty_list_when_no_content(self, adapter):
        """Test returns empty list when no content exists."""
        result = adapter.get_help_content_for_page('nonexistent_page')
        assert result == []


@pytest.mark.django_db
class TestGetOverlaysForPage:
    """Tests for get_overlays_for_page method."""
    
    def test_returns_active_overlays_for_page(self, adapter):
        """Test returns only active overlays for specified page."""
        HelpOverlay.objects.create(
            overlay_key='bracket_intro',
            page_identifier='bracket_viewer',
            overlay_config={'steps': [{'title': 'Step 1'}]},
            display_condition={'first_visit': True},
            is_active=True
        )
        
        # Inactive overlay (should not be returned)
        HelpOverlay.objects.create(
            overlay_key='inactive_overlay',
            page_identifier='bracket_viewer',
            overlay_config={'steps': []},
            display_condition={},
            is_active=False
        )
        
        result = adapter.get_overlays_for_page('bracket_viewer')
        
        assert len(result) == 1
        assert isinstance(result[0], HelpOverlayDTO)
        assert result[0].overlay_key == 'bracket_intro'
    
    def test_returns_empty_list_when_no_overlays(self, adapter):
        """Test returns empty list when no overlays exist."""
        result = adapter.get_overlays_for_page('no_overlays_page')
        assert result == []


@pytest.mark.django_db
class TestGetOnboardingState:
    """Tests for get_onboarding_state method."""
    
    def test_returns_user_onboarding_state(self, adapter, user, tournament):
        """Test returns onboarding state for user and tournament."""
        # Create completed step
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='create_tournament',
            is_completed=True,
            is_dismissed=False
        )
        
        # Create dismissed step
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='invite_staff',
            is_completed=False,
            is_dismissed=True
        )
        
        result = adapter.get_onboarding_state(user.id, tournament.id)
        
        assert len(result) == 2
        assert all(isinstance(dto, OnboardingStepDTO) for dto in result)
        
        # Check completed step
        completed_step = next(s for s in result if s.step_key == 'create_tournament')
        assert completed_step.is_completed is True
        assert completed_step.is_dismissed is False
        
        # Check dismissed step
        dismissed_step = next(s for s in result if s.step_key == 'invite_staff')
        assert dismissed_step.is_completed is False
        assert dismissed_step.is_dismissed is True
    
    def test_returns_empty_list_when_no_state(self, adapter, user, tournament):
        """Test returns empty list when no onboarding state exists."""
        result = adapter.get_onboarding_state(user.id, tournament.id)
        assert result == []


@pytest.mark.django_db
class TestMarkStepCompleted:
    """Tests for mark_step_completed method."""
    
    def test_creates_completed_step(self, adapter, user, tournament):
        """Test creates new completed step when none exists."""
        result = adapter.mark_step_completed(user.id, tournament.id, 'first_bracket')
        
        assert isinstance(result, OnboardingStepDTO)
        assert result.step_key == 'first_bracket'
        assert result.is_completed is True
        assert result.completed_at is not None
        
        # Verify in database
        state = OrganizerOnboardingState.objects.get(
            user=user,
            tournament=tournament,
            step_key='first_bracket'
        )
        assert state.is_completed is True
    
    def test_updates_existing_step_to_completed(self, adapter, user, tournament):
        """Test updates existing dismissed step to completed."""
        # Create dismissed step
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='configure_rules',
            is_completed=False,
            is_dismissed=True
        )
        
        result = adapter.mark_step_completed(user.id, tournament.id, 'configure_rules')
        
        assert result.is_completed is True
        assert result.is_dismissed is False  # Dismissed flag cleared
        assert result.completed_at is not None


@pytest.mark.django_db
class TestDismissStep:
    """Tests for dismiss_step method."""
    
    def test_creates_dismissed_step(self, adapter, user, tournament):
        """Test creates new dismissed step when none exists."""
        result = adapter.dismiss_step(user.id, tournament.id, 'optional_tutorial')
        
        assert isinstance(result, OnboardingStepDTO)
        assert result.step_key == 'optional_tutorial'
        assert result.is_dismissed is True
        assert result.dismissed_at is not None
        
        # Verify in database
        state = OrganizerOnboardingState.objects.get(
            user=user,
            tournament=tournament,
            step_key='optional_tutorial'
        )
        assert state.is_dismissed is True
    
    def test_updates_existing_step_to_dismissed(self, adapter, user, tournament):
        """Test updates existing incomplete step to dismissed."""
        # Create incomplete step
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='invite_players',
            is_completed=False,
            is_dismissed=False
        )
        
        result = adapter.dismiss_step(user.id, tournament.id, 'invite_players')
        
        assert result.is_completed is False
        assert result.is_dismissed is True
        assert result.dismissed_at is not None
