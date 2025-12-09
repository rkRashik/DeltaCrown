"""
Unit tests for HelpAndOnboardingService

Tests business logic for help content and onboarding wizard.

Epic 7.6: Guidance & Help Overlays
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from apps.tournament_ops.services.help_service import HelpAndOnboardingService
from apps.tournament_ops.dtos.help import (
    HelpContentDTO,
    HelpOverlayDTO,
    OnboardingStepDTO,
    HelpBundleDTO
)


@pytest.fixture
def mock_adapter():
    """Create mock HelpContentAdapter."""
    return Mock()


@pytest.fixture
def service(mock_adapter):
    """Create service with mocked adapter."""
    return HelpAndOnboardingService(adapter=mock_adapter)


class TestGetHelpBundle:
    """Tests for get_help_bundle method."""
    
    def test_combines_all_help_sources(self, service, mock_adapter):
        """Test combines help content, overlays, and onboarding state."""
        # Mock adapter responses
        mock_help_content = [
            HelpContentDTO(
                id=1,
                content_type='tooltip',
                title='Help 1',
                content_body='Content',
                page_identifier='test_page',
                element_selector='#test',
                display_priority=10,
                is_active=True,
                created_at=datetime(2025, 1, 1)
            )
        ]
        
        mock_overlays = [
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
        
        mock_onboarding = [
            OnboardingStepDTO(
                step_key='step1',
                is_completed=True,
                completed_at=datetime(2025, 1, 1),
                is_dismissed=False,
                dismissed_at=None
            )
        ]
        
        mock_adapter.get_help_content_for_page.return_value = mock_help_content
        mock_adapter.get_overlays_for_page.return_value = mock_overlays
        mock_adapter.get_onboarding_state.return_value = mock_onboarding
        
        result = service.get_help_bundle('test_page', user_id=1, tournament_id=10)
        
        assert isinstance(result, HelpBundleDTO)
        assert len(result.help_content) == 1
        assert len(result.overlays) == 1
        assert len(result.onboarding_steps) == 1
        
        # Verify adapter calls
        mock_adapter.get_help_content_for_page.assert_called_once_with('test_page')
        mock_adapter.get_overlays_for_page.assert_called_once_with('test_page')
        mock_adapter.get_onboarding_state.assert_called_once_with(1, 10)
    
    def test_returns_empty_bundle_when_no_data(self, service, mock_adapter):
        """Test returns empty bundle when no help data exists."""
        mock_adapter.get_help_content_for_page.return_value = []
        mock_adapter.get_overlays_for_page.return_value = []
        mock_adapter.get_onboarding_state.return_value = []
        
        result = service.get_help_bundle('empty_page', user_id=1, tournament_id=10)
        
        assert isinstance(result, HelpBundleDTO)
        assert len(result.help_content) == 0
        assert len(result.overlays) == 0
        assert len(result.onboarding_steps) == 0


class TestCompleteOnboardingStep:
    """Tests for complete_onboarding_step method."""
    
    def test_marks_step_completed(self, service, mock_adapter):
        """Test delegates to adapter to mark step completed."""
        mock_step = OnboardingStepDTO(
            step_key='configure_bracket',
            is_completed=True,
            completed_at=datetime(2025, 1, 15, 10, 30, 0),
            is_dismissed=False,
            dismissed_at=None
        )
        
        mock_adapter.mark_step_completed.return_value = mock_step
        
        result = service.complete_onboarding_step(
            user_id=5,
            tournament_id=20,
            step_key='configure_bracket'
        )
        
        assert isinstance(result, OnboardingStepDTO)
        assert result.is_completed is True
        assert result.step_key == 'configure_bracket'
        
        mock_adapter.mark_step_completed.assert_called_once_with(5, 20, 'configure_bracket')


class TestDismissHelpItem:
    """Tests for dismiss_help_item method."""
    
    def test_dismisses_onboarding_step(self, service, mock_adapter):
        """Test delegates to adapter to dismiss step."""
        mock_step = OnboardingStepDTO(
            step_key='optional_tour',
            is_completed=False,
            completed_at=None,
            is_dismissed=True,
            dismissed_at=datetime(2025, 1, 16, 14, 0, 0)
        )
        
        mock_adapter.dismiss_step.return_value = mock_step
        
        result = service.dismiss_help_item(
            user_id=7,
            tournament_id=30,
            item_key='optional_tour'
        )
        
        assert isinstance(result, OnboardingStepDTO)
        assert result.is_dismissed is True
        assert result.step_key == 'optional_tour'
        
        mock_adapter.dismiss_step.assert_called_once_with(7, 30, 'optional_tour')


class TestGetOnboardingProgress:
    """Tests for get_onboarding_progress method."""
    
    def test_calculates_progress_metrics(self, service, mock_adapter):
        """Test calculates completion percentage and step counts."""
        mock_steps = [
            OnboardingStepDTO('step1', True, datetime(2025, 1, 1), False, None),
            OnboardingStepDTO('step2', True, datetime(2025, 1, 2), False, None),
            OnboardingStepDTO('step3', False, None, False, None),
            OnboardingStepDTO('step4', False, None, True, datetime(2025, 1, 3)),
            OnboardingStepDTO('step5', False, None, False, None),
        ]
        
        mock_adapter.get_onboarding_state.return_value = mock_steps
        
        result = service.get_onboarding_progress(user_id=10, tournament_id=40)
        
        assert result['total_steps'] == 5
        assert result['completed_steps'] == 2
        assert result['dismissed_steps'] == 1
        assert result['remaining_steps'] == 2  # Not completed and not dismissed
        assert result['completion_percentage'] == 40.0  # 2/5 * 100
        
        mock_adapter.get_onboarding_state.assert_called_once_with(10, 40)
    
    def test_handles_zero_steps(self, service, mock_adapter):
        """Test handles case with no onboarding steps."""
        mock_adapter.get_onboarding_state.return_value = []
        
        result = service.get_onboarding_progress(user_id=15, tournament_id=50)
        
        assert result['total_steps'] == 0
        assert result['completed_steps'] == 0
        assert result['dismissed_steps'] == 0
        assert result['remaining_steps'] == 0
        assert result['completion_percentage'] == 0.0
    
    def test_all_steps_completed(self, service, mock_adapter):
        """Test calculates 100% when all steps completed."""
        mock_steps = [
            OnboardingStepDTO('step1', True, datetime(2025, 1, 1), False, None),
            OnboardingStepDTO('step2', True, datetime(2025, 1, 2), False, None),
            OnboardingStepDTO('step3', True, datetime(2025, 1, 3), False, None),
        ]
        
        mock_adapter.get_onboarding_state.return_value = mock_steps
        
        result = service.get_onboarding_progress(user_id=20, tournament_id=60)
        
        assert result['completion_percentage'] == 100.0
        assert result['remaining_steps'] == 0


class TestServiceArchitectureCompliance:
    """Tests for architecture pattern compliance."""
    
    def test_service_has_no_orm_imports(self):
        """Test service does not import ORM models directly."""
        import inspect
        from apps.tournament_ops.services import help_service
        
        source = inspect.getsource(help_service)
        
        # Service should not import Django models
        assert 'from apps.siteui.models import' not in source
        assert 'from django.db' not in source
        assert 'from apps.tournaments.models import' not in source
    
    def test_service_methods_return_dtos_only(self, service, mock_adapter):
        """Test all service methods return DTOs, not ORM models."""
        # Mock adapter to return DTOs
        mock_adapter.get_help_content_for_page.return_value = []
        mock_adapter.get_overlays_for_page.return_value = []
        mock_adapter.get_onboarding_state.return_value = []
        
        bundle = service.get_help_bundle('test', 1, 10)
        assert isinstance(bundle, HelpBundleDTO)
        
        # Mock step operations
        mock_step = OnboardingStepDTO('step', True, datetime.now(), False, None)
        mock_adapter.mark_step_completed.return_value = mock_step
        mock_adapter.dismiss_step.return_value = mock_step
        
        completed = service.complete_onboarding_step(1, 10, 'step')
        assert isinstance(completed, OnboardingStepDTO)
        
        dismissed = service.dismiss_help_item(1, 10, 'step')
        assert isinstance(dismissed, OnboardingStepDTO)
        
        # Progress returns dict (acceptable for aggregation)
        progress = service.get_onboarding_progress(1, 10)
        assert isinstance(progress, dict)
