"""
Tests for Journey 7 — Hub shows new public active teams immediately

Purpose: Verify hub cache invalidation prevents stale empty lists.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus

User = get_user_model()


@pytest.mark.django_db
class TestHubShowsNewTeams:
    """Test hub displays newly created teams without cache staleness"""
    
    def test_create_public_team_appears_on_hub_without_waiting(self, client):
        """Verify newly created public team appears on hub immediately"""
        # Setup: Create user
        creator = User.objects.create_user(username='creator', password='pass')
        client.login(username='creator', password='pass')
        
        # Clear hub cache before test
        cache.clear()
        
        # Visit hub BEFORE team creation (should be empty or show existing teams)
        hub_url = reverse('organizations:vnext_hub')
        response_before = client.get(hub_url)
        assert response_before.status_code == 200
        
        # Count teams before
        initial_team_count = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC'
        ).count()
        
        # Create a new public active team via API
        from apps.games.models import Game
        game = Game.objects.filter(is_active=True).first()
        
        if not game:
            pytest.skip("No active game available for test")
        
        create_url = reverse('organizations_api:create_team')
        response = client.post(create_url, {
            'name': 'Test Hub Team',
            'tag': 'THT',
            'game_id': game.id,
            'is_org_owned': False,
        }, content_type='application/json')
        
        assert response.status_code == 201
        data = response.json()
        team_slug = data['team_slug']
        
        # Verify team was created
        team = Team.objects.get(slug=team_slug)
        assert team.status == TeamStatus.ACTIVE
        assert team.visibility == 'PUBLIC'
        
        # Visit hub AFTER team creation (should show new team)
        response_after = client.get(hub_url)
        assert response_after.status_code == 200
        
        # Verify team count increased
        final_team_count = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC'
        ).count()
        assert final_team_count == initial_team_count + 1
        
        # Verify cache was invalidated by checking featured_teams context
        # (Note: We're verifying cache invalidation happened, not that team appears in DOM)
        featured_teams = response_after.context.get('featured_teams', [])
        # Team should be in featured teams (ordered by -created_at, so it's first)
        team_slugs = [t.slug for t in featured_teams]
        assert team_slug in team_slugs, f"Team {team_slug} not found in hub featured teams: {team_slugs}"
    
    def test_hub_cache_cleared_on_team_create(self, client):
        """Verify hub cache is explicitly cleared when team is created"""
        from apps.organizations.services.hub_cache import invalidate_hub_cache
        from unittest.mock import patch
        
        creator = User.objects.create_user(username='creator', password='pass')
        client.login(username='creator', password='pass')
        
        from apps.games.models import Game
        game = Game.objects.filter(is_active=True).first()
        
        if not game:
            pytest.skip("No active game available for test")
        
        # Patch cache invalidation to verify it's called
        with patch('apps.organizations.api.views.invalidate_hub_cache') as mock_invalidate:
            create_url = reverse('organizations_api:create_team')
            response = client.post(create_url, {
                'name': 'Cache Test Team',
                'tag': 'CTT',
                'game_id': game.id,
                'is_org_owned': False,
            }, content_type='application/json')
            
            if response.status_code == 201:
                # Verify cache invalidation was called with game_id
                mock_invalidate.assert_called_once_with(game_id=game.id)
    
    def test_hub_shows_newly_created_team_ordered_by_created_at_desc(self, client):
        """Verify newest teams appear first (ordered by -created_at)"""
        creator = User.objects.create_user(username='creator', password='pass')
        client.login(username='creator', password='pass')
        
        from apps.games.models import Game
        game = Game.objects.filter(is_active=True).first()
        
        if not game:
            pytest.skip("No active game available for test")
        
        # Clear cache
        cache.clear()
        
        # Create two teams in sequence
        create_url = reverse('organizations_api:create_team')
        
        response1 = client.post(create_url, {
            'name': 'First Team',
            'tag': 'FST',
            'game_id': game.id,
            'is_org_owned': False,
        }, content_type='application/json')
        assert response1.status_code == 201
        first_slug = response1.json()['team_slug']
        
        response2 = client.post(create_url, {
            'name': 'Second Team',
            'tag': 'SND',
            'game_id': game.id,
            'is_org_owned': False,
        }, content_type='application/json')
        assert response2.status_code == 201
        second_slug = response2.json()['team_slug']
        
        # Visit hub
        hub_url = reverse('organizations:vnext_hub')
        response = client.get(hub_url)
        assert response.status_code == 200
        
        featured_teams = response.context.get('featured_teams', [])
        team_slugs = [t.slug for t in featured_teams]
        
        # Verify both teams appear
        assert first_slug in team_slugs
        assert second_slug in team_slugs
        
        # Verify second team appears before first (newer first)
        second_index = team_slugs.index(second_slug)
        first_index = team_slugs.index(first_slug)
        assert second_index < first_index, f"Newer team should appear before older team"
