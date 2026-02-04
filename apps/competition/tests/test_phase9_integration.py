"""
Phase 9 Tests: Competition Integration

Tests for Competition service layer, rankings endpoints, and admin integration.
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings

from apps.organizations.models import Team, Organization, TeamMembership
from apps.competition.models import (
    TeamGlobalRankingSnapshot,
    TeamGameRankingSnapshot,
    GameRankingConfig,
)
from apps.competition.services import CompetitionService

User = get_user_model()


@pytest.mark.django_db
class TestCompetitionService:
    """Test CompetitionService methods."""
    
    def setup_method(self):
        """Setup test data."""
        # Create users
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        
        # Create independent team
        self.indie_team = Team.objects.create(
            name='Independent Squad',
            slug='independent-squad',
            game_id=1,
            created_by=self.user1,
            organization=None,  # Independent
            status='ACTIVE'
        )
        
        # Create organization and org team
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            owner=self.user2
        )
        
        self.org_team = Team.objects.create(
            name='Org Team Alpha',
            slug='org-team-alpha',
            game_id=1,
            created_by=self.user2,
            organization=self.org,
            status='ACTIVE'
        )
        
        # Create game config
        self.game_config = GameRankingConfig.objects.create(
            game_id='valorant',
            game_name='Valorant',
            is_active=True,
            scoring_weights={'verified_match_win': 10}
        )
        
        # Create ranking snapshots
        self.indie_global_snapshot = TeamGlobalRankingSnapshot.objects.create(
            team=self.indie_team,
            global_rank=1,
            global_score=1000,
            global_tier='DIAMOND',
            confidence_level='STABLE',
            games_played=10
        )
        
        self.org_global_snapshot = TeamGlobalRankingSnapshot.objects.create(
            team=self.org_team,
            global_rank=2,
            global_score=800,
            global_tier='PLATINUM',
            confidence_level='ESTABLISHED',
            games_played=8
        )
        
        self.indie_game_snapshot = TeamGameRankingSnapshot.objects.create(
            team=self.indie_team,
            game_id='valorant',
            rank=1,
            score=500,
            tier='DIAMOND',
            confidence_level='STABLE'
        )
        
        self.org_game_snapshot = TeamGameRankingSnapshot.objects.create(
            team=self.org_team,
            game_id='valorant',
            rank=2,
            score=400,
            tier='PLATINUM',
            confidence_level='ESTABLISHED'
        )
    
    def test_get_global_rankings_basic(self):
        """Test basic global rankings retrieval."""
        response = CompetitionService.get_global_rankings(limit=10)
        
        assert response.total_count == 2
        assert len(response.entries) == 2
        assert response.is_global is True
        assert response.query_count <= 3  # Query budget
        
        # Check entries
        assert response.entries[0].rank == 1
        assert response.entries[0].team_name == 'Independent Squad'
        assert response.entries[0].is_independent is True
        
        assert response.entries[1].rank == 2
        assert response.entries[1].team_name == 'Org Team Alpha'
        assert response.entries[1].is_independent is False
        assert response.entries[1].organization_name == 'Test Org'
    
    def test_get_global_rankings_tier_filter(self):
        """Test global rankings with tier filter."""
        response = CompetitionService.get_global_rankings(tier='DIAMOND', limit=10)
        
        assert response.total_count == 1
        assert len(response.entries) == 1
        assert response.entries[0].tier == 'DIAMOND'
    
    def test_get_game_rankings_basic(self):
        """Test game-specific rankings retrieval."""
        response = CompetitionService.get_game_rankings(game_id='valorant', limit=10)
        
        assert response.total_count == 2
        assert len(response.entries) == 2
        assert response.is_global is False
        assert response.game_id == 'valorant'
        
        # Check both team types represented
        assert response.entries[0].is_independent is True
        assert response.entries[1].is_independent is False
    
    def test_get_team_rank_global(self):
        """Test getting team's global rank."""
        result = CompetitionService.get_team_rank(self.indie_team.id)
        
        assert result is not None
        assert result['rank'] == 1
        assert result['tier'] == 'DIAMOND'
        assert result['score'] == 1000
        assert result['is_global'] is True
    
    def test_get_team_rank_game_specific(self):
        """Test getting team's game-specific rank."""
        result = CompetitionService.get_team_rank(self.indie_team.id, game_id='valorant')
        
        assert result is not None
        assert result['rank'] == 1
        assert result['tier'] == 'DIAMOND'
        assert result['game_id'] == 'valorant'
        assert result['is_global'] is False
    
    def test_get_org_empire_score(self):
        """Test organization empire score aggregation."""
        result = CompetitionService.get_org_empire_score(self.org.id)
        
        assert result['total_score'] == 800
        assert result['team_count'] == 1
        assert result['top_tier'] == 'PLATINUM'
        assert len(result['teams']) == 1
        assert result['teams'][0]['team_name'] == 'Org Team Alpha'
    
    def test_get_user_team_highlights(self):
        """Test user's team highlights."""
        # Add membership
        TeamMembership.objects.create(
            team=self.indie_team,
            user=self.user1,
            role='OWNER',
            status='ACTIVE'
        )
        
        result = CompetitionService.get_user_team_highlights(self.user1.id)
        
        assert result['total_teams'] == 1
        assert result['best_rank'] == 1
        assert result['teams'][0]['team_name'] == 'Independent Squad'
        assert result['teams'][0]['is_independent'] is True


@pytest.mark.django_db
class TestRankingsEndpoints:
    """Test ranking URL endpoints."""
    
    def setup_method(self):
        """Setup test data and client."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        
        # Create team
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            created_by=self.user,
            status='ACTIVE'
        )
        
        # Create game config
        self.game_config = GameRankingConfig.objects.create(
            game_id='valorant',
            game_name='Valorant',
            is_active=True
        )
        
        # Create snapshots
        TeamGlobalRankingSnapshot.objects.create(
            team=self.team,
            global_rank=5,
            global_score=500,
            global_tier='GOLD',
            confidence_level='STABLE'
        )
        
        TeamGameRankingSnapshot.objects.create(
            team=self.team,
            game_id='valorant',
            rank=3,
            score=300,
            tier='GOLD',
            confidence_level='STABLE'
        )
    
    def test_global_rankings_endpoint(self):
        """Test GET /competition/rankings/"""
        # Enable competition app
        with self.settings(COMPETITION_APP_ENABLED=True):
            response = self.client.get(reverse('competition:rankings_global'))
            
            assert response.status_code == 200
            assert 'entries' in response.context
            assert response.context['is_global'] is True
    
    def test_game_rankings_endpoint(self):
        """Test GET /competition/rankings/<game>/"""
        with self.settings(COMPETITION_APP_ENABLED=True):
            response = self.client.get(
                reverse('competition:rankings_game', args=['valorant'])
            )
            
            assert response.status_code == 200
            assert 'entries' in response.context
            assert response.context['game_id'] == 'valorant'
    
    def test_rankings_disabled_fallback(self):
        """Test rankings unavailable when COMPETITION_APP_ENABLED=False."""
        with self.settings(COMPETITION_APP_ENABLED=False):
            response = self.client.get(reverse('competition:rankings_global'))
            
            assert response.status_code == 200
            assert 'unavailable' in response.template_name[0]
    
    def test_rankings_with_filters(self):
        """Test rankings with query param filters."""
        with self.settings(COMPETITION_APP_ENABLED=True):
            response = self.client.get(
                reverse('competition:rankings_global'),
                {'tier': 'GOLD', 'verified_only': '1'}
            )
            
            assert response.status_code == 200
            assert response.context['tier_filter'] == 'GOLD'
            assert response.context['verified_only'] is True
    
    def test_user_highlights_authenticated(self):
        """Test user highlights appear for authenticated users."""
        self.client.login(username='testuser', password='pass')
        
        # Add membership
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role='OWNER',
            status='ACTIVE'
        )
        
        with self.settings(COMPETITION_APP_ENABLED=True):
            response = self.client.get(reverse('competition:rankings_global'))
            
            assert response.status_code == 200
            assert 'user_highlights' in response.context
            assert response.context['user_highlights'] is not None


@pytest.mark.django_db
class TestQueryBudgets:
    """Test query count enforcement for rankings endpoints."""
    
    def setup_method(self):
        """Setup test data."""
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        
        # Create 10 teams with rankings
        for i in range(10):
            team = Team.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                game_id=1,
                created_by=self.user,
                status='ACTIVE'
            )
            
            TeamGlobalRankingSnapshot.objects.create(
                team=team,
                global_rank=i + 1,
                global_score=1000 - (i * 50),
                global_tier='GOLD',
                confidence_level='STABLE'
            )
    
    def test_global_rankings_query_budget(self):
        """Test global rankings stays within query budget."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with self.settings(COMPETITION_APP_ENABLED=True):
            with CaptureQueriesContext(connection) as context:
                response = self.client.get(reverse('competition:rankings_global'))
                
                # Should be <= 6 queries (per performance contract)
                assert len(context.captured_queries) <= 6, \
                    f"Query budget exceeded: {len(context.captured_queries)} queries"
    
    def test_service_layer_query_count(self):
        """Test service layer returns query count metadata."""
        response = CompetitionService.get_global_rankings(limit=10)
        
        assert hasattr(response, 'query_count')
        assert response.query_count <= 3  # Service layer budget


@pytest.mark.django_db
class TestAdminIntegration:
    """Test Competition admin pages work correctly."""
    
    def setup_method(self):
        """Setup admin user and client."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            'admin', 'admin@test.com', 'adminpass'
        )
        self.client.login(username='admin', password='adminpass')
        
        # Create test data
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.team = Team.objects.create(
            name='Admin Test Team',
            slug='admin-test-team',
            game_id=1,
            created_by=self.user,
            status='ACTIVE'
        )
    
    def test_team_global_snapshot_admin_list(self):
        """Test TeamGlobalRankingSnapshot admin list page."""
        TeamGlobalRankingSnapshot.objects.create(
            team=self.team,
            global_rank=1,
            global_score=1000,
            global_tier='DIAMOND',
            confidence_level='STABLE'
        )
        
        response = self.client.get('/admin/competition/teamglobalrankingsnapshot/')
        
        assert response.status_code == 200
        assert b'Admin Test Team' in response.content
    
    def test_game_ranking_config_admin(self):
        """Test GameRankingConfig admin page."""
        response = self.client.get('/admin/competition/gamerankingconfig/')
        
        assert response.status_code == 200
        # No crash even if no configs exist


@pytest.mark.django_db
class TestFeatureFlagBehavior:
    """Test behavior with COMPETITION_APP_ENABLED flag."""
    
    def setup_method(self):
        """Setup client."""
        self.client = Client()
    
    def test_rankings_enabled(self):
        """Test rankings accessible when flag enabled."""
        with self.settings(COMPETITION_APP_ENABLED=True):
            response = self.client.get(reverse('competition:rankings_global'))
            
            assert response.status_code == 200
            assert 'unavailable' not in response.template_name[0]
    
    def test_rankings_disabled(self):
        """Test rankings show fallback when flag disabled."""
        with self.settings(COMPETITION_APP_ENABLED=False):
            response = self.client.get(reverse('competition:rankings_global'))
            
            assert response.status_code == 200
            assert 'unavailable' in response.template_name[0]
    
    def test_legacy_redirect_when_enabled(self):
        """Test legacy URLs redirect to competition app when enabled."""
        # This would be tested once legacy redirect middleware is implemented
        pass


@pytest.mark.django_db
class TestIndependentAndOrgTeams:
    """Test rankings correctly handle both team types."""
    
    def setup_method(self):
        """Setup both team types."""
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        
        # Independent team
        self.indie = Team.objects.create(
            name='Independent',
            slug='independent',
            game_id=1,
            created_by=self.user1,
            organization=None,
            status='ACTIVE'
        )
        
        # Org team
        self.org = Organization.objects.create(
            name='Pro Org',
            slug='pro-org',
            owner=self.user2
        )
        
        self.org_team = Team.objects.create(
            name='Pro Team',
            slug='pro-team',
            game_id=1,
            created_by=self.user2,
            organization=self.org,
            status='ACTIVE'
        )
        
        # Create rankings
        TeamGlobalRankingSnapshot.objects.create(
            team=self.indie,
            global_rank=1,
            global_score=1000,
            global_tier='DIAMOND',
            confidence_level='STABLE'
        )
        
        TeamGlobalRankingSnapshot.objects.create(
            team=self.org_team,
            global_rank=2,
            global_score=900,
            global_tier='DIAMOND',
            confidence_level='STABLE'
        )
    
    def test_both_team_types_in_rankings(self):
        """Test rankings include both independent and org teams."""
        response = CompetitionService.get_global_rankings(limit=10)
        
        assert response.total_count == 2
        assert response.entries[0].is_independent is True
        assert response.entries[1].is_independent is False
    
    def test_url_generation_correct(self):
        """Test URLs generated correctly for both team types."""
        response = CompetitionService.get_global_rankings(limit=10)
        
        # Independent team uses /teams/<slug>/
        assert '/teams/independent/' in response.entries[0].team_url
        
        # Org team uses /teams/<slug>/ (for now)
        assert '/teams/pro-team/' in response.entries[1].team_url
