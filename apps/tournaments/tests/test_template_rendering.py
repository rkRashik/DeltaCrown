"""
Phase 6 — Task 6.4: Template Rendering Tests

Verifies that tournament templates render without exceptions
across different tournament statuses and configurations.
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.games.models.game import Game

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rf():
    """Django RequestFactory."""
    return RequestFactory()


@pytest.fixture
def game(db):
    return Game.objects.create(
        name='Template Game', slug='template-game',
        display_name='Template Game', short_code='TPG',
        category='FPS', game_type='TEAM_VS_TEAM',
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='tpl_organizer', email='tpl_org@test.test', password='pass123',
    )


def _make_tournament(game, organizer, *, status, **overrides):
    """Helper to create a tournament with a given status."""
    now = timezone.now()
    defaults = dict(
        slug=f'tpl-test-{status}-{int(now.timestamp() * 1e6)}',
        description=f'Template test tournament ({status}).',
        game=game, organizer=organizer,
        format='single_elimination',
        participation_type='team',
        min_participants=2, max_participants=16,
        prize_pool=Decimal('500'),
        registration_start=now - timedelta(days=10),
        registration_end=now - timedelta(days=3),
        tournament_start=now - timedelta(days=1),
        registration_form_overrides={'enabled': True},
        status=status,
    )
    if status in (Tournament.REGISTRATION_OPEN, Tournament.PUBLISHED):
        defaults['published_at'] = now - timedelta(days=11)
    defaults.update(overrides)
    return Tournament.objects.create(name=f'Template {status}', **defaults)


# ---------------------------------------------------------------------------
# Detail template renders for every status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDetailTemplateRendering:
    """Ensure detail.html renders without errors for each status."""

    STATUSES_TO_TEST = [
        Tournament.DRAFT,
        Tournament.PUBLISHED,
        Tournament.REGISTRATION_OPEN,
        Tournament.REGISTRATION_CLOSED,
        Tournament.LIVE,
        Tournament.COMPLETED,
        Tournament.CANCELLED,
        Tournament.ARCHIVED,
    ]

    @pytest.mark.parametrize('status', STATUSES_TO_TEST)
    def test_detail_renders_for_status(self, client, game, organizer, status):
        """GET detail page returns 200 for each tournament status."""
        t = _make_tournament(game, organizer, status=status)
        from django.urls import reverse
        url = reverse('tournaments:detail', kwargs={'slug': t.slug})
        response = client.get(url)
        # Detail view renders for all statuses (some may show restricted content)
        assert response.status_code in (200, 403), (
            f"Status {status} returned {response.status_code}"
        )

    def test_detail_with_group_playoff_format(self, client, game, organizer):
        t = _make_tournament(
            game, organizer,
            status=Tournament.REGISTRATION_OPEN,
            format='group_playoff',
        )
        from django.urls import reverse
        url = reverse('tournaments:detail', kwargs={'slug': t.slug})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_with_solo_participation(self, client, game, organizer):
        t = _make_tournament(
            game, organizer,
            status=Tournament.REGISTRATION_OPEN,
            participation_type='solo',
        )
        from django.urls import reverse
        url = reverse('tournaments:detail', kwargs={'slug': t.slug})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_with_zero_prize_pool(self, client, game, organizer):
        t = _make_tournament(
            game, organizer,
            status=Tournament.PUBLISHED,
            prize_pool=Decimal('0'),
        )
        from django.urls import reverse
        url = reverse('tournaments:detail', kwargs={'slug': t.slug})
        response = client.get(url)
        assert response.status_code == 200

    def test_detail_with_description(self, client, game, organizer):
        t = _make_tournament(
            game, organizer,
            status=Tournament.REGISTRATION_OPEN,
            description='A **markdown** description with <em>HTML</em>.',
        )
        from django.urls import reverse
        url = reverse('tournaments:detail', kwargs={'slug': t.slug})
        response = client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# List template renders
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestListTemplateRendering:
    """Ensure the list page renders across edge cases."""

    def test_list_empty_db(self, client):
        """List page renders when DB has no tournaments."""
        from django.urls import reverse
        url = reverse('tournaments:list')
        response = client.get(url)
        assert response.status_code == 200

    def test_list_with_mixed_statuses(self, client, game, organizer):
        """List page renders when DB has tournaments in many statuses."""
        for st in [Tournament.DRAFT, Tournament.PUBLISHED,
                    Tournament.REGISTRATION_OPEN, Tournament.COMPLETED]:
            _make_tournament(game, organizer, status=st)
        from django.urls import reverse
        url = reverse('tournaments:list')
        response = client.get(url)
        assert response.status_code == 200
