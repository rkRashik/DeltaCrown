"""
Tests for tournament admin actions.

Tests bulk actions like publish, open/close registration, and cancel tournaments.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game
from apps.tournaments.admin import TournamentAdmin

User = get_user_model()


@pytest.fixture
def admin_site():
    """Create admin site instance."""
    return AdminSite()


@pytest.fixture
def tournament_admin(admin_site):
    """Create TournamentAdmin instance."""
    return TournamentAdmin(Tournament, admin_site)


@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


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
def draft_tournaments(db, game, admin_user):
    """Create draft tournaments for testing."""
    tournaments = []
    for i in range(3):
        tournament = Tournament.objects.create(
            name=f'Draft Tournament {i+1}',
            slug=f'draft-tournament-{i+1}',
            description=f'Description {i+1}',
            organizer=admin_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now() + timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=8),
            tournament_start=timezone.now() + timedelta(days=15),
            status=Tournament.DRAFT
        )
        tournaments.append(tournament)
    return tournaments


@pytest.mark.django_db
class TestPublishTournamentsAction:
    """Test bulk publish action."""
    
    def test_publish_action_changes_status(self, tournament_admin, draft_tournaments, admin_user):
        """Publish action should change status to PUBLISHED."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        queryset = Tournament.objects.filter(id__in=[t.id for t in draft_tournaments])
        tournament_admin.publish_tournaments(request, queryset)
        
        # Refresh from database
        for tournament in draft_tournaments:
            tournament.refresh_from_db()
            assert tournament.status == Tournament.PUBLISHED
            assert tournament.published_at is not None
    
    def test_publish_action_only_affects_drafts(self, tournament_admin, game, admin_user):
        """Publish action should only affect DRAFT tournaments."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        # Create one draft and one already published
        draft = Tournament.objects.create(
            name='Draft Tournament',
            slug='draft-tournament',
            description='Description',
            organizer=admin_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now() + timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=8),
            tournament_start=timezone.now() + timedelta(days=15),
            status=Tournament.DRAFT
        )
        
        already_published = Tournament.objects.create(
            name='Published Tournament',
            slug='published-tournament',
            description='Description',
            organizer=admin_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now() + timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=8),
            tournament_start=timezone.now() + timedelta(days=15),
            status=Tournament.PUBLISHED,
            published_at=timezone.now()
        )
        
        queryset = Tournament.objects.filter(id__in=[draft.id, already_published.id])
        tournament_admin.publish_tournaments(request, queryset)
        
        draft.refresh_from_db()
        already_published.refresh_from_db()
        
        assert draft.status == Tournament.PUBLISHED
        # Already published should remain published (status doesn't change from PUBLISHED to PUBLISHED)
        assert already_published.status == Tournament.PUBLISHED


@pytest.mark.django_db
class TestRegistrationActions:
    """Test open and close registration actions."""
    
    def test_open_registration_action(self, tournament_admin, game, admin_user):
        """Open registration action should change status to REGISTRATION_OPEN."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Description',
            organizer=admin_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=14),
            status=Tournament.PUBLISHED
        )
        
        queryset = Tournament.objects.filter(id=tournament.id)
        tournament_admin.open_registration(request, queryset)
        
        tournament.refresh_from_db()
        assert tournament.status == Tournament.REGISTRATION_OPEN
    
    def test_close_registration_action(self, tournament_admin, game, admin_user):
        """Close registration action should change status to REGISTRATION_CLOSED."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Description',
            organizer=admin_user,
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
        
        queryset = Tournament.objects.filter(id=tournament.id)
        tournament_admin.close_registration(request, queryset)
        
        tournament.refresh_from_db()
        assert tournament.status == Tournament.REGISTRATION_CLOSED


@pytest.mark.django_db
class TestCancelTournamentsAction:
    """Test cancel tournaments action."""
    
    def test_cancel_action_changes_status(self, tournament_admin, game, admin_user):
        """Cancel action should change status to CANCELLED."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Description',
            organizer=admin_user,
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
        
        queryset = Tournament.objects.filter(id=tournament.id)
        tournament_admin.cancel_tournaments(request, queryset)
        
        tournament.refresh_from_db()
        assert tournament.status == Tournament.CANCELLED
    
    def test_cancel_does_not_affect_completed(self, tournament_admin, game, admin_user):
        """Cancel action should not affect COMPLETED tournaments."""
        factory = RequestFactory()
        request = factory.get('/')
        request.user = admin_user
        
        tournament = Tournament.objects.create(
            name='Completed Tournament',
            slug='completed-tournament',
            description='Description',
            organizer=admin_user,
            game=game,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.TEAM,
            max_participants=16,
            min_participants=4,
            registration_start=timezone.now() - timedelta(days=30),
            registration_end=timezone.now() - timedelta(days=23),
            tournament_start=timezone.now() - timedelta(days=16),
            tournament_end=timezone.now() - timedelta(days=2),
            status=Tournament.COMPLETED
        )
        
        queryset = Tournament.objects.filter(id=tournament.id)
        tournament_admin.cancel_tournaments(request, queryset)
        
        tournament.refresh_from_db()
        # Should remain COMPLETED
        assert tournament.status == Tournament.COMPLETED
