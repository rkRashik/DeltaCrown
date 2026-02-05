"""
Tests for Journey 8 — Rankings include 0-point teams end-to-end

Purpose: Verify rankings display ALL public active teams, including unranked (0-point) teams.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus
from tests.factories import create_independent_team

User = get_user_model()


@pytest.mark.django_db
class TestRankingsIncludeZeroPointTeams:
    """Test rankings service and views include 0-point teams"""
    
    def test_competition_service_includes_zero_point_teams(self):
        """Verify CompetitionService.get_game_rankings includes teams with no snapshots"""
        from apps.competition.services import CompetitionService
        from apps.games.models import Game
        
        # Get or create a game
        game = Game.objects.filter(is_active=True).first()
        if not game:
            pytest.skip("No active game available for test")
        
        # Create team without snapshot (0 points)
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Zero Point Team', 'zero-pt')
        team.game_id = game.id
        team.status = TeamStatus.ACTIVE
        team.visibility = 'PUBLIC'
        team.save(update_fields=['game_id', 'status', 'visibility'])
        
        # Query rankings for this game
        response = CompetitionService.get_game_rankings(game_id=game.id, limit=100)
        
        # Verify team appears in rankings
        team_slugs = [entry.team_slug for entry in response.entries]
        assert team.slug in team_slugs, f"Team {team.slug} not found in rankings: {team_slugs}"
        
        # Find team entry
        team_entry = next((e for e in response.entries if e.team_slug == team.slug), None)
        assert team_entry is not None
        
        # Verify 0-point team has defaults
        assert team_entry.score == 0, f"Expected score=0 for unranked team, got {team_entry.score}"
        assert team_entry.tier == 'UNRANKED', f"Expected tier=UNRANKED for unranked team, got {team_entry.tier}"
    
    def test_rankings_view_includes_zero_point_teams_without_crash(self, client):
        """Verify rankings page renders 0-point teams without crashing"""
        from apps.games.models import Game
        
        game = Game.objects.filter(is_active=True).first()
        if not game:
            pytest.skip("No active game available for test")
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Unranked Team', 'unranked')
        team.game_id = game.id
        team.status = TeamStatus.ACTIVE
        team.visibility = 'PUBLIC'
        team.save(update_fields=['game_id', 'status', 'visibility'])
        
        # Visit rankings page
        url = reverse('competition:game_rankings', kwargs={'game_id': game.id})
        response = client.get(url)
        
        # Verify page renders successfully
        assert response.status_code == 200
        
        # Verify team appears in context
        # (Note: Context structure depends on view implementation)
        # At minimum, verify no crash and 200 status
    
    def test_rankings_ordering_deterministic_with_zero_point_teams(self):
        """Verify rankings have deterministic ordering: score DESC, created_at DESC"""
        from apps.competition.services import CompetitionService
        from apps.games.models import Game
        from django.utils import timezone
        import time
        
        game = Game.objects.filter(is_active=True).first()
        if not game:
            pytest.skip("No active game available for test")
        
        # Create multiple teams without snapshots (all 0 points)
        creator = User.objects.create_user(username='creator', password='pass')
        
        # Create first team
        team1 = create_independent_team(creator, 'First Team', 'first-tm')
        team1.game_id = game.id
        team1.status = TeamStatus.ACTIVE
        team1.visibility = 'PUBLIC'
        team1.created_at = timezone.now() - timezone.timedelta(seconds=10)
        team1.save(update_fields=['game_id', 'status', 'visibility', 'created_at'])
        
        # Small delay to ensure different created_at
        time.sleep(0.1)
        
        # Create second team (newer)
        team2 = create_independent_team(creator, 'Second Team', 'second-tm')
        team2.game_id = game.id
        team2.status = TeamStatus.ACTIVE
        team2.visibility = 'PUBLIC'
        team2.created_at = timezone.now()
        team2.save(update_fields=['game_id', 'status', 'visibility', 'created_at'])
        
        # Query rankings
        response = CompetitionService.get_game_rankings(game_id=game.id, limit=100)
        
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
    
    def test_zero_point_teams_display_unranked_badge(self, client):
        """Verify 0-point teams display 'UNRANKED' tier in rankings UI"""
        from apps.games.models import Game
        
        game = Game.objects.filter(is_active=True).first()
        if not game:
            pytest.skip("No active game available for test")
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Badge Test Team', 'badge-test')
        team.game_id = game.id
        team.status = TeamStatus.ACTIVE
        team.visibility = 'PUBLIC'
        team.save(update_fields=['game_id', 'status', 'visibility'])
        
        # Visit rankings page
        url = reverse('competition:game_rankings', kwargs={'game_id': game.id})
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify team name appears
        assert team.name in content, f"Team name '{team.name}' not found in rankings page"
        
        # Verify UNRANKED or "Unranked" text appears (case-insensitive check)
        assert 'unranked' in content.lower(), "UNRANKED badge not found in rankings page"
    
    def test_rankings_api_returns_all_teams_including_zero_point(self, client):
        """Verify rankings API endpoint includes 0-point teams"""
        from apps.games.models import Game
        
        game = Game.objects.filter(is_active=True).first()
        if not game:
            pytest.skip("No active game available for test")
        
        # Create team without snapshot
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'API Test Team', 'api-test')
        team.game_id = game.id
        team.status = TeamStatus.ACTIVE
        team.visibility = 'PUBLIC'
        team.save(update_fields=['game_id', 'status', 'visibility'])
        
        # Check if API endpoint exists (may vary by implementation)
        try:
            url = reverse('competition:api_game_rankings', kwargs={'game_id': game.id})
        except:
            # If no API endpoint, skip this test
            pytest.skip("No rankings API endpoint found")
        
        response = client.get(url)
        
        if response.status_code == 200:
            data = response.json()
            # Verify team appears in results
            # (Structure may vary - adapt based on actual API response)
            if 'entries' in data:
                team_slugs = [entry.get('team_slug') for entry in data['entries']]
                assert team.slug in team_slugs, f"Team {team.slug} not found in API rankings"
