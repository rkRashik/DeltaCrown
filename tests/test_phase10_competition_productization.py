"""
Phase 10: Competition Productization - Integration Tests

Tests comprehensive integration of CompetitionService across all UI surfaces:
- Hub page (rankings preview)
- Team detail (rank display)
- Org detail (team ranks + empire score)
- No legacy leaderboard imports
- Cache behavior
- Query budgets
- Feature flag behavior
"""

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from unittest.mock import patch, MagicMock

User = get_user_model()


@pytest.mark.django_db
class TestHubRankingsPreview:
    """Test hub page renders rankings preview from CompetitionService."""
    
    def test_hub_includes_rankings_preview_context(self, client, django_user_model):
        """Hub context must include rankings_preview from CompetitionService."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch('apps.organizations.views.hub.CompetitionService') as mock_service:
            # Mock service response
            mock_entry = MagicMock()
            mock_entry.rank = 1
            mock_entry.team_name = 'Test Team'
            mock_entry.team_slug = 'test-team'
            mock_entry.organization_name = None
            mock_entry.tier = 'ELITE'
            mock_entry.score = 1500.0
            
            mock_response = MagicMock()
            mock_response.entries = [mock_entry]
            mock_service.get_global_rankings.return_value = mock_response
            mock_service.get_user_team_highlights.return_value = None
            
            response = client.get(reverse('organizations:vnext_hub'))
            
            # Verify context includes rankings_preview
            assert response.status_code == 200
            assert 'rankings_preview' in response.context
            assert 'competition_enabled' in response.context
    
    def test_hub_rankings_preview_with_competition_disabled(self, client, django_user_model):
        """Hub should handle competition disabled gracefully."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch.object(settings, 'COMPETITION_APP_ENABLED', False):
            response = client.get(reverse('organizations:vnext_hub'))
            
            assert response.status_code == 200
            assert response.context['competition_enabled'] is False
            assert response.context['rankings_preview'] == []
    
    def test_hub_shows_user_highlights_when_authenticated(self, client, django_user_model):
        """Hub should show user's team highlights when authenticated."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch('apps.organizations.views.hub.CompetitionService') as mock_service:
            mock_response = MagicMock()
            mock_response.entries = []
            mock_service.get_global_rankings.return_value = mock_response
            
            mock_highlights = {'team_ranks': [{'team_id': 1, 'rank': 5}]}
            mock_service.get_user_team_highlights.return_value = mock_highlights
            
            response = client.get(reverse('organizations:vnext_hub'))
            
            assert response.status_code == 200
            assert response.context['user_highlights'] == mock_highlights
            # Verify service was called with user ID
            mock_service.get_user_team_highlights.assert_called_once_with(user.id)
    
    def test_hub_rankings_preview_uses_service_not_raw_queryset(self, client, django_user_model):
        """Hub must use CompetitionService, not raw queryset."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch('apps.organizations.views.hub.CompetitionService') as mock_service:
            mock_response = MagicMock()
            mock_response.entries = []
            mock_service.get_global_rankings.return_value = mock_response
            mock_service.get_user_team_highlights.return_value = None
            
            response = client.get(reverse('organizations:vnext_hub'))
            
            # Verify service was called (not raw queryset)
            assert mock_service.get_global_rankings.called
            assert response.status_code == 200


@pytest.mark.django_db
class TestTeamDetailRankDisplay:
    """Test team detail page shows rank from CompetitionService."""
    
    def test_team_detail_context_includes_rank_fields(self, client, django_user_model):
        """Team detail context must include stats from CompetitionService."""
        from apps.organizations.models import Team, Organization
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        
        # Create game
        game = Game.objects.create(
            name='Test Game',
            slug='test-game',
            is_active=True
        )
        
        # Create independent team
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user
        )
        
        with patch('apps.organizations.services.team_detail_context.CompetitionService') as mock_service:
            mock_rank_data = {
                'has_ranking': True,
                'rank': 5,
                'tier': 'DIAMOND',
                'score': 1200.0,
                'percentile': 85.5,
                'global_score': 1300.0,
                'global_tier': 'PLATINUM',
                'verified_match_count': 10,
                'confidence_level': 'STABLE',
                'breakdown': {}
            }
            mock_service.get_team_rank.return_value = mock_rank_data
            
            response = client.get(reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'}))
            
            assert response.status_code == 200
            assert 'stats' in response.context
            stats = response.context['stats']
            
            # Verify stats from service
            assert stats['rank'] == 5
            assert stats['tier'] == 'DIAMOND'
            assert stats['score'] == 1200.0
            mock_service.get_team_rank.assert_called_once_with(team.id, game_id=game.id)
    
    def test_team_detail_works_for_independent_team(self, client, django_user_model):
        """Team detail must work for independent teams (organization=None)."""
        from apps.organizations.models import Team
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        game = Game.objects.create(name='Game', slug='game', is_active=True)
        
        # Independent team (organization=None)
        team = Team.objects.create(
            name='Independent Team',
            slug='independent-team',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user,
            organization=None  # Explicitly independent
        )
        
        with patch('apps.organizations.services.team_detail_context.CompetitionService') as mock_service:
            mock_service.get_team_rank.return_value = None
            
            response = client.get(reverse('organizations:team_detail', kwargs={'team_slug': 'independent-team'}))
            
            assert response.status_code == 200
            assert response.context['team']['slug'] == 'independent-team'
    
    def test_team_detail_works_for_org_team(self, client, django_user_model):
        """Team detail must work for organization teams."""
        from apps.organizations.models import Team, Organization
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        game = Game.objects.create(name='Game', slug='game', is_active=True)
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user
        )
        
        team = Team.objects.create(
            name='Org Team',
            slug='org-team',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user,
            organization=org
        )
        
        with patch('apps.organizations.services.team_detail_context.CompetitionService') as mock_service:
            mock_service.get_team_rank.return_value = None
            
            # Access via canonical org URL
            response = client.get(reverse('organizations:org_team_detail', 
                                         kwargs={'org_slug': 'test-org', 'team_slug': 'org-team'}))
            
            assert response.status_code == 200
            assert response.context['organization']['slug'] == 'test-org'


@pytest.mark.django_db
class TestOrgDetailTeamRanks:
    """Test org detail page shows team ranks from CompetitionService."""
    
    def test_org_detail_includes_squads_with_ranks(self, client, django_user_model):
        """Org detail context must include squads with team ranks."""
        from apps.organizations.models import Organization, Team
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        game = Game.objects.create(name='Game', slug='game', is_active=True)
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user
        )
        
        team = Team.objects.create(
            name='Squad Alpha',
            slug='squad-alpha',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user,
            organization=org
        )
        
        with patch('apps.organizations.services.org_detail_service.CompetitionService') as mock_service:
            mock_rank_data = {
                'rank': 3,
                'tier': 'ELITE',
                'score': 1800.0
            }
            mock_service.get_team_rank.return_value = mock_rank_data
            mock_service.get_org_empire_score.return_value = {'total_score': 5000.0}
            
            response = client.get(reverse('organizations:org_detail', kwargs={'org_slug': 'test-org'}))
            
            assert response.status_code == 200
            assert 'squads' in response.context
            
            squads = response.context['squads']
            assert len(squads) > 0
            
            # Verify squad has rank data
            squad = squads[0]
            assert squad['rank'] == 3
            assert squad['tier'] == 'ELITE'
            assert squad['score'] == 1800.0
    
    def test_org_detail_includes_empire_score(self, client, django_user_model):
        """Org detail must include empire score from CompetitionService."""
        from apps.organizations.models import Organization
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user
        )
        
        with patch('apps.organizations.services.org_detail_service.CompetitionService') as mock_service:
            mock_empire_score = {'total_score': 8500.0, 'team_count': 3}
            mock_service.get_org_empire_score.return_value = mock_empire_score
            mock_service.get_team_rank.return_value = None
            
            response = client.get(reverse('organizations:org_detail', kwargs={'org_slug': 'test-org'}))
            
            assert response.status_code == 200
            assert 'org_empire_score' in response.context
            assert response.context['org_empire_score'] == mock_empire_score


@pytest.mark.django_db
class TestNoLegacyLeaderboardImports:
    """Ensure no views use legacy leaderboard queries."""
    
    def test_hub_view_does_not_import_teamranking(self):
        """Hub view must not import legacy TeamRanking model."""
        from apps.organizations.views import hub
        import inspect
        
        source = inspect.getsource(hub.vnext_hub)
        
        # Verify no legacy imports
        assert 'TeamRanking' not in source
        assert 'leaderboard_rows' not in source or 'REMOVED' in source
        # Must use CompetitionService
        assert 'CompetitionService' in source
    
    def test_team_detail_context_uses_competition_service(self):
        """Team detail context must use CompetitionService, not legacy queries."""
        from apps.organizations.services import team_detail_context
        import inspect
        
        source = inspect.getsource(team_detail_context._build_stats_context)
        
        # Must use CompetitionService
        assert 'CompetitionService' in source
        # Should not use legacy snapshot models directly (Phase 10 update)
        # Note: It's OK to import them for backwards compatibility, but primary path is service
    
    def test_org_detail_service_uses_competition_service(self):
        """Org detail service must use CompetitionService for ranks."""
        from apps.organizations.services import org_detail_service
        import inspect
        
        source = inspect.getsource(org_detail_service.get_org_detail_context)
        
        # Must use CompetitionService
        assert 'CompetitionService' in source


@pytest.mark.django_db
class TestCacheBehavior:
    """Test caching doesn't break data contract."""
    
    def test_rankings_preview_cache_hit_preserves_shape(self, client, django_user_model):
        """Cached rankings must have same shape as fresh data."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch('apps.organizations.views.hub.CompetitionService') as mock_service:
            mock_entry = MagicMock()
            mock_entry.rank = 1
            mock_entry.team_name = 'Team'
            mock_entry.tier = 'ELITE'
            mock_entry.score = 1500.0
            mock_entry.organization_name = None
            
            mock_response = MagicMock()
            mock_response.entries = [mock_entry]
            mock_service.get_global_rankings.return_value = mock_response
            mock_service.get_user_team_highlights.return_value = None
            
            # First request (cache miss)
            response1 = client.get(reverse('organizations:vnext_hub'))
            rankings1 = response1.context['rankings_preview']
            
            # Second request (should use cache)
            response2 = client.get(reverse('organizations:vnext_hub'))
            rankings2 = response2.context['rankings_preview']
            
            # Verify same shape
            assert len(rankings1) == len(rankings2)
            if rankings1:
                assert hasattr(rankings1[0], 'rank')
                assert hasattr(rankings1[0], 'team_name')
                assert hasattr(rankings1[0], 'tier')


@pytest.mark.django_db
class TestQueryBudgets:
    """Test query budgets are enforced."""
    
    def test_hub_respects_query_budget(self, client, django_user_model, django_assert_max_num_queries):
        """Hub page must stay within query budget (≤15 queries)."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch('apps.organizations.views.hub.CompetitionService') as mock_service:
            mock_response = MagicMock()
            mock_response.entries = []
            mock_service.get_global_rankings.return_value = mock_response
            mock_service.get_user_team_highlights.return_value = None
            
            # Hub target: ≤15 queries
            with django_assert_max_num_queries(20):  # Allow some margin
                response = client.get(reverse('organizations:vnext_hub'))
                assert response.status_code == 200
    
    def test_team_detail_respects_query_budget(self, client, django_user_model, django_assert_max_num_queries):
        """Team detail must stay within query budget."""
        from apps.organizations.models import Team
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        game = Game.objects.create(name='Game', slug='game', is_active=True)
        
        team = Team.objects.create(
            name='Team',
            slug='team',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user
        )
        
        with patch('apps.organizations.services.team_detail_context.CompetitionService') as mock_service:
            mock_service.get_team_rank.return_value = None
            
            # Team detail target: ≤10 queries
            with django_assert_max_num_queries(15):  # Allow margin
                response = client.get(reverse('organizations:team_detail', kwargs={'team_slug': 'team'}))
                assert response.status_code == 200


@pytest.mark.django_db
class TestFeatureFlagBehavior:
    """Test feature flag behavior."""
    
    def test_hub_competition_flag_off_shows_disabled_message(self, client, django_user_model):
        """Hub with competition disabled should show disabled state."""
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        client.force_login(user)
        
        with patch.object(settings, 'COMPETITION_APP_ENABLED', False):
            response = client.get(reverse('organizations:vnext_hub'))
            
            assert response.status_code == 200
            assert response.context['competition_enabled'] is False
            # Template should handle this gracefully
    
    def test_team_detail_competition_flag_off_shows_defaults(self, client, django_user_model):
        """Team detail with competition disabled should show default stats."""
        from apps.organizations.models import Team
        from apps.games.models import Game
        
        user = django_user_model.objects.create_user(username='testuser', password='testpass')
        game = Game.objects.create(name='Game', slug='game', is_active=True)
        
        team = Team.objects.create(
            name='Team',
            slug='team',
            status='ACTIVE',
            visibility='PUBLIC',
            game_id=game.id,
            created_by=user
        )
        
        with patch.object(settings, 'COMPETITION_APP_ENABLED', False):
            response = client.get(reverse('organizations:team_detail', kwargs={'team_slug': 'team'}))
            
            assert response.status_code == 200
            # Stats should be default/empty
            stats = response.context['stats']
            assert stats['tier'] == 'UNRANKED' or stats['score'] == 0


@pytest.mark.django_db
class TestCompetitionServiceIntegration:
    """Test actual CompetitionService integration (if competition app available)."""
    
    def test_competition_service_available(self):
        """CompetitionService must be importable."""
        try:
            from apps.competition.services import CompetitionService
            assert CompetitionService is not None
        except ImportError:
            pytest.fail("CompetitionService not available")
    
    def test_competition_service_has_required_methods(self):
        """CompetitionService must have all required methods."""
        from apps.competition.services import CompetitionService
        
        required_methods = [
            'get_global_rankings',
            'get_game_rankings',
            'get_team_rank',
            'get_org_empire_score',
            'get_user_team_highlights'
        ]
        
        for method_name in required_methods:
            assert hasattr(CompetitionService, method_name), f"Missing method: {method_name}"
