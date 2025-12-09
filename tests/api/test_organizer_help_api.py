"""
API tests for Organizer Help endpoints

Tests REST API for help content, overlays, and onboarding wizard.

Epic 7.6: Guidance & Help Overlays
"""

import pytest
from datetime import datetime
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament
from apps.siteui.models import HelpContent, HelpOverlay, OrganizerOnboardingState

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create authenticated user."""
    return User.objects.create_user(
        username='test_organizer',
        email='organizer@test.com',
        password='testpass123'
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
def authenticated_client(api_client, user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestHelpBundleView:
    """Tests for GET /api/organizer/help/bundle/ endpoint."""
    
    def test_requires_authentication(self, api_client):
        """Test endpoint requires authentication."""
        url = reverse('api:organizer-help-bundle')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_returns_help_bundle_for_page(self, authenticated_client, tournament):
        """Test returns help content, overlays, and onboarding state."""
        # Create help content
        HelpContent.objects.create(
            content_type='tooltip',
            title='Dashboard Help',
            content_body='Welcome to your dashboard.',
            page_identifier='organizer_dashboard',
            element_selector='#dashboard-header',
            display_priority=10,
            is_active=True
        )
        
        # Create overlay
        HelpOverlay.objects.create(
            overlay_key='dashboard_tour',
            page_identifier='organizer_dashboard',
            overlay_config={'steps': [{'title': 'Welcome'}]},
            display_condition={'first_login': True},
            is_active=True
        )
        
        # Create onboarding step
        OrganizerOnboardingState.objects.create(
            user=tournament.organizer,
            tournament=tournament,
            step_key='create_tournament',
            is_completed=True
        )
        
        url = reverse('api:organizer-help-bundle')
        response = authenticated_client.get(url, {
            'page_identifier': 'organizer_dashboard',
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert 'help_content' in data
        assert 'overlays' in data
        assert 'onboarding_steps' in data
        
        assert len(data['help_content']) == 1
        assert data['help_content'][0]['title'] == 'Dashboard Help'
        
        assert len(data['overlays']) == 1
        assert data['overlays'][0]['overlay_key'] == 'dashboard_tour'
        
        assert len(data['onboarding_steps']) == 1
        assert data['onboarding_steps'][0]['step_key'] == 'create_tournament'
        assert data['onboarding_steps'][0]['is_completed'] is True
    
    def test_requires_page_identifier_param(self, authenticated_client):
        """Test requires page_identifier query parameter."""
        url = reverse('api:organizer-help-bundle')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'page_identifier' in response.json()['error']
    
    def test_filters_inactive_content(self, authenticated_client, tournament):
        """Test does not return inactive help content or overlays."""
        # Active content
        HelpContent.objects.create(
            content_type='tooltip',
            title='Active Help',
            content_body='Active.',
            page_identifier='test_page',
            display_priority=10,
            is_active=True
        )
        
        # Inactive content
        HelpContent.objects.create(
            content_type='tooltip',
            title='Inactive Help',
            content_body='Inactive.',
            page_identifier='test_page',
            display_priority=5,
            is_active=False
        )
        
        url = reverse('api:organizer-help-bundle')
        response = authenticated_client.get(url, {
            'page_identifier': 'test_page',
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data['help_content']) == 1
        assert data['help_content'][0]['title'] == 'Active Help'


@pytest.mark.django_db
class TestCompleteOnboardingStepView:
    """Tests for POST /api/organizer/help/complete-step/ endpoint."""
    
    def test_requires_authentication(self, api_client):
        """Test endpoint requires authentication."""
        url = reverse('api:organizer-help-complete-step')
        response = api_client.post(url, {})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_marks_step_completed(self, authenticated_client, user, tournament):
        """Test marks onboarding step as completed."""
        url = reverse('api:organizer-help-complete-step')
        response = authenticated_client.post(url, {
            'tournament_id': tournament.id,
            'step_key': 'configure_bracket'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data['step_key'] == 'configure_bracket'
        assert data['is_completed'] is True
        assert data['completed_at'] is not None
        
        # Verify in database
        state = OrganizerOnboardingState.objects.get(
            user=user,
            tournament=tournament,
            step_key='configure_bracket'
        )
        assert state.is_completed is True
    
    def test_requires_step_key(self, authenticated_client, tournament):
        """Test requires step_key in request body."""
        url = reverse('api:organizer-help-complete-step')
        response = authenticated_client.post(url, {
            'tournament_id': tournament.id
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_requires_tournament_id(self, authenticated_client):
        """Test requires tournament_id in request body."""
        url = reverse('api:organizer-help-complete-step')
        response = authenticated_client.post(url, {
            'step_key': 'test_step'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDismissHelpItemView:
    """Tests for POST /api/organizer/help/dismiss/ endpoint."""
    
    def test_requires_authentication(self, api_client):
        """Test endpoint requires authentication."""
        url = reverse('api:organizer-help-dismiss')
        response = api_client.post(url, {})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_dismisses_help_item(self, authenticated_client, user, tournament):
        """Test dismisses onboarding step."""
        url = reverse('api:organizer-help-dismiss')
        response = authenticated_client.post(url, {
            'tournament_id': tournament.id,
            'item_key': 'optional_tutorial'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data['step_key'] == 'optional_tutorial'
        assert data['is_dismissed'] is True
        assert data['dismissed_at'] is not None
        
        # Verify in database
        state = OrganizerOnboardingState.objects.get(
            user=user,
            tournament=tournament,
            step_key='optional_tutorial'
        )
        assert state.is_dismissed is True
    
    def test_requires_item_key(self, authenticated_client, tournament):
        """Test requires item_key in request body."""
        url = reverse('api:organizer-help-dismiss')
        response = authenticated_client.post(url, {
            'tournament_id': tournament.id
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOnboardingProgressView:
    """Tests for GET /api/organizer/help/progress/ endpoint."""
    
    def test_requires_authentication(self, api_client):
        """Test endpoint requires authentication."""
        url = reverse('api:organizer-help-progress')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_returns_progress_metrics(self, authenticated_client, user, tournament):
        """Test returns onboarding progress statistics."""
        # Create onboarding steps
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='step1',
            is_completed=True
        )
        
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='step2',
            is_completed=True
        )
        
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='step3',
            is_completed=False,
            is_dismissed=False
        )
        
        OrganizerOnboardingState.objects.create(
            user=user,
            tournament=tournament,
            step_key='step4',
            is_completed=False,
            is_dismissed=True
        )
        
        url = reverse('api:organizer-help-progress')
        response = authenticated_client.get(url, {
            'tournament_id': tournament.id
        })
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data['total_steps'] == 4
        assert data['completed_steps'] == 2
        assert data['dismissed_steps'] == 1
        assert data['remaining_steps'] == 1
        assert data['completion_percentage'] == 50.0
    
    def test_requires_tournament_id_param(self, authenticated_client):
        """Test requires tournament_id query parameter."""
        url = reverse('api:organizer-help-progress')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'tournament_id' in response.json()['error']


@pytest.mark.django_db
class TestAPIArchitectureCompliance:
    """Tests for API architecture pattern compliance."""
    
    def test_views_use_facade_only(self):
        """Test views use TournamentOpsService façade, not direct service access."""
        import inspect
        from apps.api.views import organizer_help_views
        
        source = inspect.getsource(organizer_help_views)
        
        # Should use façade
        assert 'get_tournament_ops_service()' in source
        
        # Should not import services directly
        assert 'from apps.tournament_ops.services.help_service import' not in source
        assert 'HelpAndOnboardingService()' not in source
    
    def test_views_do_not_import_orm_models(self):
        """Test views do not import ORM models directly."""
        import inspect
        from apps.api.views import organizer_help_views
        
        source = inspect.getsource(organizer_help_views)
        
        # Should not import models
        assert 'from apps.siteui.models import' not in source
        assert 'from apps.tournaments.models import Tournament' not in source
