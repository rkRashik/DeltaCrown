"""
Phase 14: Test rankings show ALL teams (including 0-point teams).

Test Objectives:
1. Newly created teams appear in /competition/rankings/ (global)
2. Newly created teams appear in game-specific rankings
3. 0-point teams ordered by created_at (tie-breaker)
4. Rankings show score=0, tier=UNRANKED for teams without snapshots
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.organizations.models import Team, Organization
from apps.organizations.choices import TeamStatus
from apps.competition.models import TeamGlobalRankingSnapshot, TeamGameRankingSnapshot
from apps.competition.services.competition_service import CompetitionService

User = get_user_model()


@pytest.mark.django_db
class TestZeroPointTeamRankings(TestCase):
    """Test that rankings include teams with 0 points (no snapshots)."""
    
    def setUp(self):
        """Set up test users and teams."""
        self.client = Client()
        
        # Create test users
        self.user1 = User.objects.create_user(username='alpha_creator', password='pass123')
        self.user2 = User.objects.create_user(username='bravo_creator', password='pass123')
        self.user3 = User.objects.create_user(username='charlie_creator', password='pass123')
        
        # Create teams WITHOUT snapshots (0 points)
        self.team_alpha = Team.objects.create(
            name='Alpha Team',
            slug='alpha-team',
            created_by=self.user1,
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id='1',  # String, not int
        )
        
        self.team_bravo = Team.objects.create(
            name='Bravo Team',
            slug='bravo-team',
            created_by=self.user2,
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id='1',  # String, not int
        )
        
        # Create team WITH snapshot (100 points)
        self.team_charlie = Team.objects.create(
            name='Charlie Team',
            slug='charlie-team',
            created_by=self.user3,
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id='1',  # String, not int
        )
        
        # Give Charlie team a ranking snapshot (using actual fields)
        TeamGlobalRankingSnapshot.objects.create(
            team=self.team_charlie,
            global_score=100,
            global_rank=1,
            global_tier='GOLD',
            games_played=5,  # Real field instead of confidence_level
        )
        
        TeamGameRankingSnapshot.objects.create(
            team=self.team_charlie,
            game_id='1',  # String, not int
            score=100,
            rank=1,
            tier='GOLD',
            confidence_level='STABLE',  # This model HAS confidence_level
            verified_match_count=5,
        )
    
    def test_global_rankings_include_zero_point_teams(self):
        """Test global rankings show teams with 0 points."""
        service = CompetitionService()
        
        # Get global rankings (no tier filter)
        rankings = service.get_global_rankings(
            tier=None,
            verified_only=False,
            limit=50,
            offset=0
        )
        
        # Should have 3 teams (1 with points + 2 with 0 points)
        assert rankings.total_count == 3, f"Expected 3 teams, got {rankings.total_count}"
        
        # Check entries
        team_names = [entry.team_name for entry in rankings.entries]
        assert 'Alpha Team' in team_names, "Alpha Team (0 points) missing from rankings"
        assert 'Bravo Team' in team_names, "Bravo Team (0 points) missing from rankings"
        assert 'Charlie Team' in team_names, "Charlie Team (100 points) missing from rankings"
        
        # Check ordering: Charlie (100 points) should be first
        assert rankings.entries[0].team_name == 'Charlie Team', "Charlie Team should rank 1st (100 points)"
        assert rankings.entries[0].score == 100
        assert rankings.entries[0].tier == 'GOLD'
        
        # Check 0-point teams appear
        zero_point_entries = [e for e in rankings.entries if e.score == 0]
        assert len(zero_point_entries) == 2, f"Expected 2 zero-point teams, got {len(zero_point_entries)}"
        
        # Check 0-point teams have UNRANKED tier
        for entry in zero_point_entries:
            assert entry.tier == 'UNRANKED', f"{entry.team_name} should have tier=UNRANKED, got {entry.tier}"
    
    def test_game_rankings_include_zero_point_teams(self):
        """Test game-specific rankings show teams with 0 points."""
        service = CompetitionService()
        
        # Get Valorant rankings (game_id='1' as string)
        rankings = service.get_game_rankings(
            game_id='1',
            tier=None,
            verified_only=False,
            limit=50,
            offset=0
        )
        
        # Should have 3 teams (all are game_id=1)
        assert rankings.total_count == 3, f"Expected 3 teams, got {rankings.total_count}"
        
        # Check entries
        team_names = [entry.team_name for entry in rankings.entries]
        assert 'Alpha Team' in team_names, "Alpha Team (0 points) missing from game rankings"
        assert 'Bravo Team' in team_names, "Bravo Team (0 points) missing from game rankings"
        assert 'Charlie Team' in team_names, "Charlie Team (100 points) missing from game rankings"
    
    def test_zero_point_teams_ordered_by_created_at(self):
        """Test 0-point teams use created_at as tie-breaker."""
        service = CompetitionService()
        
        # Get rankings
        rankings = service.get_global_rankings(
            tier=None,
            verified_only=False,
            limit=50,
            offset=0
        )
        
        # Get 0-point entries
        zero_point_entries = [e for e in rankings.entries if e.score == 0]
        
        # Should be ordered by created_at DESC (newer teams first)
        # Bravo created after Alpha, so Bravo should rank higher
        zero_point_names = [e.team_name for e in zero_point_entries]
        alpha_index = zero_point_names.index('Alpha Team')
        bravo_index = zero_point_names.index('Bravo Team')
        
        # Bravo created AFTER Alpha, so Bravo should appear BEFORE Alpha (DESC order)
        assert bravo_index < alpha_index, "Bravo Team (newer) should rank higher than Alpha Team (older) for 0-point tie"
    
    def test_rankings_endpoint_renders_zero_point_teams(self):
        """Test /competition/rankings/ endpoint shows 0-point teams."""
        # Make request to rankings page
        response = self.client.get('/competition/rankings/')
        
        # Should render successfully
        assert response.status_code == 200, f"Rankings page returned {response.status_code}"
        
        # Check content includes team names
        content = response.content.decode('utf-8')
        assert 'Alpha Team' in content, "Alpha Team (0 points) not visible in rankings page"
        assert 'Bravo Team' in content, "Bravo Team (0 points) not visible in rankings page"
        assert 'Charlie Team' in content, "Charlie Team (100 points) not visible in rankings page"


@pytest.mark.django_db
class TestHubTeamVisibility(TestCase):
    """Test that newly created teams appear in hub (/teams/vnext/)."""
    
    def setUp(self):
        """Set up test user and team."""
        self.client = Client()
        self.user = User.objects.create_user(username='team_creator', password='pass123')
        
        # Create team
        self.team = Team.objects.create(
            name='Delta Team',
            slug='delta-team',
            created_by=self.user,
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id='1',  # String
        )
    
    def test_hub_shows_newly_created_team(self):
        """Test hub page shows newly created team in featured grid."""
        # Make request to hub page
        response = self.client.get('/teams/vnext/')
        
        # Should render successfully
        assert response.status_code == 200, f"Hub page returned {response.status_code}"
        
        # Check content includes team name
        content = response.content.decode('utf-8')
        assert 'Delta Team' in content, "Delta Team not visible in hub featured teams"
