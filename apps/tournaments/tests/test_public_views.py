"""
Tests for public tournament views (browse and detail pages).

Ensures public views use correct template paths after frontend reorganization.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game

User = get_user_model()


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
def published_tournament(db, game):
    """Create a published tournament."""
    organizer = User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123'
    )
    
    return Tournament.objects.create(
        name='Public Tournament',
        slug='public-tournament',
        description='Public description',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        max_participants=16,
        min_participants=4,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        published_at=timezone.now()
    )


@pytest.mark.django_db
class TestTournamentListView:
    """Test public tournament list/browse page."""
    
    def test_list_view_uses_public_template(self, client, published_tournament):
        """Tournament list should use public/browse template."""
        url = reverse('tournaments:list')
        response = client.get(url)
        
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'tournaments/public/browse/list.html' in template_names
    
    def test_list_view_shows_published_tournaments(self, client, published_tournament):
        """List view should display published tournaments."""
        url = reverse('tournaments:list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert published_tournament in response.context['tournament_list']
    
    def test_list_view_filters_by_game(self, client, published_tournament, game):
        """List view should filter tournaments by game."""
        url = reverse('tournaments:list') + f'?game={game.slug}'
        response = client.get(url)
        
        assert response.status_code == 200
        tournaments = list(response.context['tournament_list'])
        assert all(t.game == game for t in tournaments)


@pytest.mark.django_db
class TestTournamentDetailView:
    """Test public tournament detail page."""
    
    def test_detail_view_uses_public_template(self, client, published_tournament):
        """Tournament detail should use public/detail template."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'tournaments/public/detail/overview.html' in template_names
    
    def test_detail_view_shows_tournament_info(self, client, published_tournament):
        """Detail view should show tournament information."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['tournament'] == published_tournament
        assert 'cta_state' in response.context
        assert 'slots_filled' in response.context
    
    def test_detail_view_shows_registration_cta(self, client, published_tournament):
        """Detail view should show registration CTA with proper state."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        # Anonymous users should see login_required state
        assert response.context['cta_state'] in ['login_required', 'open', 'closed']
