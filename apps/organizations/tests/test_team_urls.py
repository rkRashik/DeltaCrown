"""
Regression tests for Team URL routing.

These tests ensure the URL contract between models and URL patterns stays consistent.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.organizations.models import Team, Organization
from apps.games.models import Game

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def test_game(db):
    """Create test game."""
    game, _ = Game.objects.get_or_create(
        slug='valorant',
        defaults={
            'name': 'Valorant',
            'display_name': 'VALORANT',
            'short_code': 'VAL',
            'is_active': True,
        }
    )
    return game


@pytest.fixture
def test_organization(db, test_user):
    """Create test organization."""
    org = Organization.objects.create(
        name='Test Org',
        slug='test-org',
        ceo=test_user
    )
    return org


@pytest.mark.django_db
class TestTeamURLRouting:
    """Tests for Team URL routing and reverse matching."""
    
    def test_team_get_absolute_url_resolves_independent(self, test_user, test_game):
        """Independent team get_absolute_url() matches URL pattern."""
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            owner=test_user,
            game_id=test_game.id,
            region='Bangladesh',
            status='ACTIVE'
        )
        
        # Get URL from model
        url = team.get_absolute_url()
        
        # Get expected URL from reverse
        expected_url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        
        # They must match
        assert url == expected_url
        assert url == '/teams/test-team/'
    
    def test_team_get_absolute_url_resolves_organization(self, test_user, test_game, test_organization):
        """Organization team get_absolute_url() matches URL pattern."""
        team = Team.objects.create(
            name='Org Team',
            slug='org-team',
            organization=test_organization,
            game_id=test_game.id,
            region='Bangladesh',
            status='ACTIVE'
        )
        
        # Get URL from model
        url = team.get_absolute_url()
        
        # Get expected URL from reverse (org-prefixed)
        expected_url = reverse('organizations:org_team_detail', kwargs={
            'org_slug': 'test-org',
            'team_slug': 'org-team'
        })
        
        # They must match
        assert url == expected_url
    
    def test_team_detail_url_reverse_works(self):
        """URL reverse for team_detail with team_slug kwarg works."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'my-team'})
        
        assert url == '/teams/my-team/'
    
    def test_team_detail_url_pattern_uses_team_slug(self):
        """URL pattern uses 'team_slug' parameter name (not 'slug')."""
        # This test documents the contract
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'example'})
        
        # If this succeeds, the pattern uses team_slug
        assert 'example' in url
        
        # Try with wrong kwarg name - should raise NoReverseMatch
        with pytest.raises(Exception):  # NoReverseMatch
            reverse('organizations:team_detail', kwargs={'slug': 'example'})
    
    def test_hub_template_can_render_team_links(self, client, test_user, test_game):
        """Hub template can render team profile links without NoReverseMatch."""
        # Create team
        team = Team.objects.create(
            name='Hub Test Team',
            slug='hub-test-team',
            owner=test_user,
            game_id=test_game.id,
            region='Test',
            status='ACTIVE'
        )
        
        # Login and visit hub
        client.force_login(test_user)
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Should render without NoReverseMatch error
        assert response.status_code == 200
        
        # Should contain team profile link
        expected_url = team.get_absolute_url()
        assert expected_url.encode() in response.content
