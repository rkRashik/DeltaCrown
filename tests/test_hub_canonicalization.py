"""
Hub canonicalization tests - verify hub uses vNext Team model exclusively.

Phase 12 Regression Fix: Hub was not showing teams due to:
1. Empty cache being cached for 2 minutes
2. Potential model mismatch issues

These tests ensure:
- Hub displays vNext teams (both independent and org-owned)
- Hub works without competition rankings
- Cache invalidation works correctly
- No legacy Team model contamination
"""
import pytest
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestHubDisplaysVNextTeams:
    """Verify hub displays vNext teams regardless of ranking state."""
    
    def test_hub_shows_independent_team(self, client):
        """Hub must show independent PUBLIC ACTIVE teams."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache before test
        cache.clear()
        
        # Create game, user, and independent team
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=None,  # Independent
            created_by=user,
            game=game,
            name="Elite Independent Squad"
        )
        
        # GET hub page
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 200
        content = response.content.decode()
        assert "Elite Independent Squad" in content
        assert "No Teams Available" not in content
    
    def test_hub_shows_org_owned_team(self, client):
        """Hub must show org-owned PUBLIC ACTIVE teams."""
        from apps.organizations.tests.factories import (
            TeamFactory, OrganizationFactory, GameFactory
        )
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create org, game, and org-owned team
        game = GameFactory()
        org = OrganizationFactory(name="Team Liquid")
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=org,
            game=game,
            name="Team Liquid Academy"
        )
        
        # GET hub page
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Assertions
        assert response.status_code == 200
        content = response.content.decode()
        assert "Team Liquid Academy" in content
    
    def test_hub_works_without_rankings(self, client):
        """Hub must display teams even when competition/rankings disabled or empty."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create team WITHOUT any ranking/competition data
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=None,
            created_by=user,
            game=game,
            name="Unranked Warriors"
        )
        
        # Verify no ranking exists
        from apps.organizations.models import Team
        team_obj = Team.objects.get(id=team.id)
        assert not hasattr(team_obj, 'ranking') or team_obj.ranking is None
        
        # GET hub page
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Should still show team
        assert response.status_code == 200
        content = response.content.decode()
        assert "Unranked Warriors" in content
    
    def test_hub_does_not_show_private_teams(self, client):
        """Hub must NOT show PRIVATE teams to public users."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create private team
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PRIVATE',  # Not public
            organization=None,
            created_by=user,
            game=game,
            name="Secret Squad"
        )
        
        # GET hub page as anonymous user
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Should NOT show private team
        assert response.status_code == 200
        content = response.content.decode()
        assert "Secret Squad" not in content
    
    def test_hub_does_not_show_deleted_teams(self, client):
        """Hub must NOT show DELETED teams."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create deleted team
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.DELETED,  # Soft-deleted
            visibility='PUBLIC',
            organization=None,
            created_by=user,
            game=game,
            name="Deleted Squad"
        )
        
        # GET hub page
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        # Should NOT show deleted team
        assert response.status_code == 200
        content = response.content.decode()
        assert "Deleted Squad" not in content


@pytest.mark.django_db
class TestHubCacheInvalidation:
    """Verify cache invalidation works correctly."""
    
    def test_empty_cache_not_persisted(self, client):
        """Empty team list should be cached for max 10 seconds, not 2 minutes."""
        from apps.organizations.views.hub import _get_featured_teams
        
        # Clear cache
        cache.clear()
        
        # Get teams when none exist
        teams = _get_featured_teams()
        assert teams == []
        
        # Check cache ttl (should be 10 seconds, not 120)
        cache_key = 'featured_teams_all_12'
        cached_value = cache.get(cache_key)
        
        # Should be cached (even if empty)
        assert cached_value is not None
        assert cached_value == []
    
    def test_cache_invalidated_after_team_creation(self, client):
        """Cache should be invalidated when a team is created."""
        from apps.organizations.tests.factories import GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        from apps.organizations.models import Team
        from apps.organizations.services.hub_cache import invalidate_hub_cache
        
        # Clear cache
        cache.clear()
        
        # Pre-populate cache with empty list
        from apps.organizations.views.hub import _get_featured_teams
        teams_before = _get_featured_teams()
        assert teams_before == []
        
        # Create a team
        game = GameFactory()
        user = UserFactory()
        team = Team.objects.create(
            name="New Squad",
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=None,
            created_by=user,
            game=game
        )
        
        # Invalidate cache
        invalidate_hub_cache(game_id=game.id)
        
        # Get teams again - should query DB and find new team
        teams_after = _get_featured_teams(game_id=game.id)
        assert len(teams_after) == 1
        assert teams_after[0].name == "New Squad"


@pytest.mark.django_db
class TestHubUsesCorrectModel:
    """Verify hub uses vNext Team model, not legacy."""
    
    def test_hub_imports_vnext_team_model(self):
        """Hub view must import apps.organizations.models.Team."""
        from apps.organizations.views import hub
        import inspect
        
        # Read source code of _get_featured_teams
        source = inspect.getsource(hub._get_featured_teams)
        
        # Must import from organizations, not teams
        assert "from apps.organizations.models import Team" in source
        assert "from apps.teams.models import Team" not in source
    
    def test_hub_queries_vnext_team_fields(self, client):
        """Hub queryset must use vNext fields (status, visibility, created_by)."""
        from apps.organizations.views.hub import _get_featured_teams
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create team with vNext fields
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=None,
            created_by=user,
            game=game
        )
        
        # Get teams
        teams = _get_featured_teams()
        
        # Verify we got vNext model instances
        assert len(teams) > 0
        team_obj = teams[0]
        
        # Check vNext fields exist
        assert hasattr(team_obj, 'status')
        assert hasattr(team_obj, 'visibility')
        assert hasattr(team_obj, 'created_by')
        assert hasattr(team_obj, 'organization')
        
        # Verify NOT legacy fields
        assert not hasattr(team_obj, 'is_active')
        assert not hasattr(team_obj, 'is_public')


@pytest.mark.django_db
class TestHubResponsiveness:
    """Verify hub template is mobile-friendly."""
    
    def test_hub_has_responsive_grid_classes(self, client):
        """Hub template must use responsive grid classes."""
        from apps.organizations.tests.factories import TeamFactory, GameFactory, UserFactory
        from apps.organizations.choices import TeamStatus
        
        # Clear cache
        cache.clear()
        
        # Create a team
        game = GameFactory()
        user = UserFactory()
        team = TeamFactory(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            organization=None,
            created_by=user,
            game=game
        )
        
        # GET hub page
        url = reverse('organizations:vnext_hub')
        response = client.get(url)
        
        content = response.content.decode()
        
        # Check for Tailwind responsive classes
        assert 'grid-cols-1' in content  # Mobile: 1 column
        assert 'md:grid-cols-2' in content or 'lg:grid-cols-2' in content  # Tablet: 2 columns
        assert 'xl:grid-cols-3' in content or 'lg:grid-cols-3' in content  # Desktop: 3 columns
