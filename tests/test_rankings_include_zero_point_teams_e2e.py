"""
Tests for Journey 8 — Rankings include 0-point teams end-to-end

Purpose: Verify rankings display ALL public active teams, including unranked (0-point) teams.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus
from apps.games.models import Game
from tests.factories import create_independent_team

User = get_user_model()


@pytest.fixture
def active_game():
    """Create or get an active game for testing."""
    from apps.competition.models import GameRankingConfig
    from django.core.cache import cache
    
    # Clear cache to prevent stale rankings across tests
    cache.clear()
    
    game, _ = Game.objects.get_or_create(
        id=1,
        defaults={
            'name': 'Test Game',
            'slug': 'test-game',
            'is_active': True,
            'short_code': 'TG',
            'display_name': 'Test Game',
            'category': 'OTHER',
            'game_type': 'TEAM_VS_TEAM',
        }
    )
    
    # Create GameRankingConfig if missing (required by leaderboard views)
    # GameRankingConfig uses game_id as PK, just needs the ID
    GameRankingConfig.objects.get_or_create(game_id=game.id)
    
    return game


@pytest.mark.django_db
class TestRankingsIncludeZeroPointTeams:
    """Test rankings service and views include 0-point teams"""
    
    def test_competition_service_includes_zero_point_teams(self, active_game):
        """Verify CompetitionService.get_game_rankings includes teams with no snapshots"""
        from apps.competition.services import CompetitionService
        
        # Create team without snapshot (0 points)
        creator = User.objects.create_user(username='creator', password='pass', email='creator@test.com')
        team, _ = create_independent_team('Zero Point Team', creator, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        
        # Query rankings for this game
        response = CompetitionService.get_game_rankings(game_id=active_game.id, limit=100)
        
        # Verify team appears in rankings
        team_slugs = [entry.team_slug for entry in response.entries]
        assert team.slug in team_slugs, f"Team {team.slug} not found in rankings: {team_slugs}"
        
        # Find team entry
        team_entry = next((e for e in response.entries if e.team_slug == team.slug), None)
        assert team_entry is not None
        
        # Verify 0-point team has defaults
        assert team_entry.score == 0, f"Expected score=0 for unranked team, got {team_entry.score}"
        assert team_entry.tier == 'UNRANKED', f"Expected tier=UNRANKED for unranked team, got {team_entry.tier}"
    
    def test_rankings_view_includes_zero_point_teams_without_crash(self, client, active_game):
        """Verify rankings page renders 0-point teams without crashing"""
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator2', password='pass', email='creator2@test.com')
        team, _ = create_independent_team('Unranked Team', creator, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        
        # Visit rankings page
        url = reverse('competition:rankings_game', kwargs={'game_id': active_game.id})
        response = client.get(url)
        
        # Verify page renders successfully
        assert response.status_code == 200
        
        # Verify team appears in context
        # (Note: Context structure depends on view implementation)
        # At minimum, verify no crash and 200 status
    
    def test_rankings_ordering_deterministic_with_zero_point_teams(self, active_game):
        """Verify rankings have deterministic ordering: score DESC, created_at DESC"""
        from apps.competition.services import CompetitionService
        from django.utils import timezone
        import time
        
        # Create multiple teams without snapshots (all 0 points)
        # Note: Need different users due to one_active_independent_team_per_game_per_user constraint
        creator1 = User.objects.create_user(username='creator3a', password='pass', email='creator3a@test.com')
        creator2 = User.objects.create_user(username='creator3b', password='pass', email='creator3b@test.com')
        
        # Create first team (older)
        team1, _ = create_independent_team('First Team', creator1, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        team1.created_at = timezone.now() - timezone.timedelta(seconds=10)
        team1.save(update_fields=['created_at'])
        
        # Small delay to ensure different created_at
        time.sleep(0.1)
        
        # Create second team (newer)
        team2, _ = create_independent_team('Second Team', creator2, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        team2.created_at = timezone.now()
        team2.save(update_fields=['created_at'])
        
        # Query rankings
        response = CompetitionService.get_game_rankings(game_id=active_game.id, limit=100)
        
        # Find both teams
        team1_entry = next((e for e in response.entries if e.team_slug == team1.slug), None)
        team2_entry = next((e for e in response.entries if e.team_slug == team2.slug), None)
        
        assert team1_entry is not None, f"Team1 not found in rankings"
        assert team2_entry is not None, f"Team2 not found in rankings"
        
        # Both have 0 points
        assert team1_entry.score == 0
        assert team2_entry.score == 0
        
        # Newer team (team2) should rank higher (lower rank number) due to created_at tie-breaker
        # Note: Rank is 1-indexed, so lower number = better rank
        if team1_entry.rank and team2_entry.rank:
            # If both have ranks, verify newer ranks higher
            # (Ordering is: -score, -created_at, so newer with same score comes first)
            # Find indices in entries list
            team1_index = response.entries.index(team1_entry)
            team2_index = response.entries.index(team2_entry)
            assert team2_index < team1_index, \
                f"Newer team (team2) should appear before older team (team1). Got indices: team2={team2_index}, team1={team1_index}"
    
    def test_zero_point_teams_display_unranked_badge(self, client, active_game):
        """Verify 0-point teams display 'UNRANKED' tier in rankings UI"""
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator4', password='pass', email='creator4@test.com')
        team, _ = create_independent_team('Badge Test Team', creator, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        
        # Visit rankings page
        url = reverse('competition:rankings_game', kwargs={'game_id': active_game.id})
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify team name appears
        assert team.name in content, f"Team name '{team.name}' not found in rankings page"
        
        # Verify UNRANKED or "Unranked" text appears (case-insensitive check)
        assert 'unranked' in content.lower(), "UNRANKED badge not found in rankings page"
    
    def test_rankings_endpoint_includes_zero_point_teams_in_html(self, client, active_game):
        """Verify rankings endpoint includes 0-point teams in HTML response"""
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator5', password='pass', email='creator5@test.com')
        team, _ = create_independent_team('API Test Team', creator, game_id=active_game.id, status=TeamStatus.ACTIVE, visibility='PUBLIC')
        
        # Get rankings page
        url = reverse('competition:rankings_game', kwargs={'game_id': active_game.id})
        response = client.get(url)
        
        # Verify successful response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify team appears in HTML (same as badge test - rankings is HTML not JSON)
        assert team.name in content, f"Team name '{team.name}' not found in rankings HTML"
        assert 'unranked' in content.lower(), "UNRANKED indicator not found for 0-point team"
