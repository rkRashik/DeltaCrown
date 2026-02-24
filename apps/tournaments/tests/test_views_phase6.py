"""
Phase 6 — Task 6.3: View Tests

Smoke/integration tests for the core public tournament views:
- TournamentListView  (GET /tournaments/)
- TournamentDetailView (GET /tournaments/<slug>/)

Validates HTTP status, template selection, and key context variables.
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.games.models.game import Game

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def game(db):
    return Game.objects.create(
        name='View Test Game', slug='view-test-game',
        display_name='View Test Game', short_code='VTG',
        category='FPS', game_type='TEAM_VS_TEAM',
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='view_organizer', email='view_org@test.test', password='pass123',
    )


@pytest.fixture
def published_tournament(db, game, organizer):
    """A REGISTRATION_OPEN tournament (visible on the public list)."""
    now = timezone.now()
    return Tournament.objects.create(
        name='Open Cup',
        slug='open-cup-viewtest',
        description='Open cup for view testing.',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='team',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('500'),
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        registration_form_overrides={'enabled': True},
        status=Tournament.REGISTRATION_OPEN,
        published_at=now - timedelta(days=1),
    )


@pytest.fixture
def draft_tournament(db, game, organizer):
    """A DRAFT tournament (NOT visible on the public list)."""
    now = timezone.now()
    return Tournament.objects.create(
        name='Draft Only',
        slug='draft-only-viewtest',
        description='Draft tournament for view testing.',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='solo',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('100'),
        registration_start=now + timedelta(days=5),
        registration_end=now + timedelta(days=10),
        tournament_start=now + timedelta(days=15),
        registration_form_overrides={'enabled': True},
        status=Tournament.DRAFT,
    )


# ---------------------------------------------------------------------------
# List View
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTournamentListView:
    """Verify the public tournament listing page."""

    def test_list_returns_200(self, client):
        url = reverse('tournaments:list')
        response = client.get(url)
        assert response.status_code == 200

    def test_list_uses_correct_template(self, client):
        url = reverse('tournaments:list')
        response = client.get(url)
        template_names = [t.name for t in response.templates]
        assert any('list' in name for name in template_names)

    def test_list_shows_published_tournaments(self, client, published_tournament):
        url = reverse('tournaments:list')
        response = client.get(url)
        content = response.content.decode()
        assert published_tournament.name in content

    def test_list_hides_draft_tournaments(self, client, draft_tournament, published_tournament):
        url = reverse('tournaments:list')
        response = client.get(url)
        content = response.content.decode()
        assert draft_tournament.name not in content
        assert published_tournament.name in content

    def test_list_pagination_context(self, client):
        url = reverse('tournaments:list')
        response = client.get(url)
        assert 'tournament_list' in response.context or 'page_obj' in response.context


# ---------------------------------------------------------------------------
# Detail View
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTournamentDetailView:
    """Verify the tournament detail page."""

    def test_detail_returns_200(self, client, published_tournament):
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_uses_correct_template(self, client, published_tournament):
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        template_names = [t.name for t in response.templates]
        assert any('detail' in name for name in template_names)

    def test_detail_context_has_tournament(self, client, published_tournament):
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        assert 'tournament' in response.context
        assert response.context['tournament'].id == published_tournament.id

    def test_detail_nonexistent_slug_404(self, client):
        url = reverse('tournaments:detail', kwargs={'slug': 'does-not-exist-xyz'})
        response = client.get(url)
        assert response.status_code == 404

    def test_detail_anonymous_allowed(self, client, published_tournament):
        """Public detail page should be accessible without login."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_shows_tournament_name(self, client, published_tournament):
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        content = response.content.decode()
        assert published_tournament.name in content


# ---------------------------------------------------------------------------
# Authenticated Views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuthenticatedViews:
    """Verify views that require authentication."""

    def test_my_tournaments_redirects_anon(self, client):
        url = reverse('tournaments:my_tournaments')
        response = client.get(url)
        # Should redirect to login
        assert response.status_code in (302, 301)

    def test_my_tournaments_200_for_auth(self, client, organizer):
        client.force_login(organizer)
        url = reverse('tournaments:my_tournaments')
        response = client.get(url)
        assert response.status_code == 200

    @pytest.mark.skip(reason="Legacy create_tournament URL purged in TOC Sprint 0")
    def test_create_tournament_requires_auth(self, client):
        url = reverse('tournaments:create_tournament')
        response = client.get(url)
        assert response.status_code in (302, 301)
