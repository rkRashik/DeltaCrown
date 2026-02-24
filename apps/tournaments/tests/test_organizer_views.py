"""
Tests for organizer console views.

ARCHIVED: Legacy organizer views (organizer_dashboard, organizer_tournament_detail)
were replaced by the Tournament Operations Center (TOC) in Sprint 0.
URL patterns removed during TOC Purge — all tests in this module are skipped.
See: apps/tournaments/urls_toc.py and apps/tournaments/api/toc/ for TOC implementation.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game

User = get_user_model()

# Skip entire module — legacy organizer views replaced by TOC
pytestmark = pytest.mark.skip(reason="Legacy organizer views replaced by TOC (Sprint 0 purge)")

@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score'
    )


@pytest.fixture
def organizer_user(db):
    """Create a user who will be an organizer."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user (not an organizer)."""
    return User.objects.create_user(
        username='regular',
        email='regular@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return User.objects.create_user(
        username='staff',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def tournament(db, game, organizer_user):
    """Create a test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        description='Test description',
        organizer=organizer_user,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        max_participants=16,
        min_participants=4,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN
    )


@pytest.mark.django_db
class TestOrganizerDashboardAccess:
    """Test access control for organizer dashboard."""
    
    def test_anonymous_user_redirected_to_login(self, client):
        """Anonymous users should be redirected to login."""
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_regular_user_without_tournaments_denied(self, client, regular_user):
        """Regular users who don't organize tournaments should be denied."""
        client.force_login(regular_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        # Should be denied (403) or redirected
        assert response.status_code in [302, 403]
    
    def test_organizer_user_can_access(self, client, organizer_user, tournament):
        """Users who organize tournaments can access dashboard."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'tournaments' in response.context
    
    def test_staff_user_can_access(self, client, staff_user):
        """Staff users can access dashboard even without tournaments."""
        client.force_login(staff_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_dashboard_uses_organizer_template(self, client, organizer_user, tournament):
        """Dashboard should use the organizer template path."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
        # Check that it uses the organizer template
        template_names = [t.name for t in response.templates]
        assert 'tournaments/organizer/dashboard.html' in template_names
    
    def test_non_staff_organizer_permission_model(self, client, organizer_user, tournament):
        """Non-staff organizer should have access if they organize at least one tournament."""
        # Ensure user is not staff
        organizer_user.is_staff = False
        organizer_user.save()
        
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        # Should have access because they organize a tournament
        assert response.status_code == 200
        assert organizer_user in [t.organizer for t in response.context['tournaments']]


@pytest.mark.django_db
class TestOrganizerDashboardContent:
    """Test dashboard content and functionality."""
    
    def test_dashboard_shows_organizer_tournaments(self, client, organizer_user, tournament):
        """Dashboard should show tournaments organized by the user."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        assert tournament in response.context['tournaments']
    
    def test_dashboard_shows_stats(self, client, organizer_user, tournament):
        """Dashboard should show summary statistics."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        stats = response.context['stats']
        assert 'total_tournaments' in stats
        assert 'active_tournaments' in stats
        assert 'draft_tournaments' in stats
        assert 'completed_tournaments' in stats
    
    def test_dashboard_only_shows_own_tournaments(self, client, organizer_user, tournament, game):
        """Regular organizers should only see their own tournaments."""
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        other_tournament = Tournament.objects.create(
            name='Other Tournament',
            slug='other-tournament',
            description='Other description',
            organizer=other_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14),
            status=Tournament.DRAFT
        )
        
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        tournaments = list(response.context['tournaments'])
        assert tournament in tournaments
        assert other_tournament not in tournaments
    
    def test_staff_sees_all_tournaments(self, client, staff_user, tournament, game, organizer_user):
        """Staff users should see all tournaments."""
        other_tournament = Tournament.objects.create(
            name='Other Tournament',
            slug='other-tournament',
            description='Other description',
            organizer=organizer_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14),
            status=Tournament.DRAFT
        )
        
        client.force_login(staff_user)
        url = reverse('tournaments:organizer_dashboard')
        response = client.get(url)
        
        tournaments = list(response.context['tournaments'])
        assert tournament in tournaments
        assert other_tournament in tournaments


@pytest.mark.django_db
class TestOrganizerTournamentDetail:
    """Test tournament detail view for organizers."""
    
    def test_organizer_can_access_own_tournament(self, client, organizer_user, tournament):
        """Organizer can access their own tournament detail."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['tournament'] == tournament
    
    def test_organizer_cannot_access_others_tournament(self, client, regular_user, tournament):
        """Regular organizer cannot access someone else's tournament."""
        client.force_login(regular_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 404
    
    def test_staff_can_access_any_tournament(self, client, staff_user, tournament):
        """Staff users can access any tournament."""
        client.force_login(staff_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_detail_view_shows_stats(self, client, organizer_user, tournament):
        """Detail view should show tournament statistics."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert 'registration_stats' in response.context
        assert 'match_stats' in response.context
        assert 'dispute_stats' in response.context
        assert 'time_status' in response.context
    
    def test_detail_uses_organizer_template(self, client, organizer_user, tournament):
        """Detail view should use the organizer template path."""
        client.force_login(organizer_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'tournaments/organizer/tournament_detail.html' in template_names
    
    def test_non_staff_organizer_access_control(self, client, game):
        """Non-staff organizer should only access their own tournaments, not others."""
        # Create two separate organizers
        organizer1 = User.objects.create_user(
            username='organizer1',
            email='organizer1@example.com',
            password='testpass123',
            is_staff=False
        )
        organizer2 = User.objects.create_user(
            username='organizer2',
            email='organizer2@example.com',
            password='testpass123',
            is_staff=False
        )
        
        # Create tournament for organizer1
        tournament1 = Tournament.objects.create(
            name='Tournament 1',
            slug='tournament-1',
            description='Description 1',
            organizer=organizer1,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14),
            status=Tournament.REGISTRATION_OPEN
        )
        
        # organizer1 should be able to access their own tournament
        client.force_login(organizer1)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament1.slug})
        response = client.get(url)
        assert response.status_code == 200
        
        # organizer2 should NOT be able to access organizer1's tournament
        client.force_login(organizer2)
        response = client.get(url)
        assert response.status_code == 404
    
    def test_non_organizer_gets_403(self, client, regular_user, tournament):
        """Non-organizer authenticated user should get 403 Forbidden."""
        # Ensure regular_user has no tournaments
        assert not Tournament.objects.filter(organizer=regular_user).exists()
        
        client.force_login(regular_user)
        url = reverse('tournaments:organizer_tournament_detail', kwargs={'slug': tournament.slug})
        response = client.get(url)
        
        # Should get 404 (because queryset filters them out) or 403
        assert response.status_code in [403, 404]
