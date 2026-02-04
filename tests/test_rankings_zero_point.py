"""
Rankings Zero-Point Teams Tests - Ensure all active teams appear

Tests ensure rankings query includes teams without ranking snapshots:
- Teams with score=0 appear in rankings
- Teams without snapshots default to score=0, tier=UNRANKED
- Private teams excluded
- Ordering stable (score DESC, created DESC)
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from apps.organizations.models import Team
from apps.games.models import Game
from apps.competition.models import TeamGlobalRankingSnapshot


@pytest.mark.django_db
class TestRankingsZeroPointTeams:
    """Ensure rankings include teams without snapshots (0-point teams)"""

    @pytest.fixture
    def game(self):
        """Create test game"""
        return Game.objects.create(
            name='Test Game',
            display_name='TEST GAME',
            slug='test-game',
            short_code='TEST',
            category='FPS'
        )

    @pytest.fixture
    def team_with_snapshot(self, game):
        """Team WITH ranking snapshot (has score)"""
        team = Team.objects.create(
            name='Ranked Team',
            slug='ranked-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC'
        )
        TeamGlobalRankingSnapshot.objects.create(
            team=team,
            global_score=1500,
            global_tier='GOLD',
            global_rank=42,
            games_played=10
        )
        return team

    @pytest.fixture
    def team_without_snapshot(self, game):
        """Team WITHOUT ranking snapshot (new team, 0 points)"""
        return Team.objects.create(
            name='New Team',
            slug='new-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC',
            created_at=timezone.now() - timedelta(days=1)
        )

    @pytest.fixture
    def private_team(self, game):
        """Private team (should be excluded from rankings)"""
        return Team.objects.create(
            name='Private Team',
            slug='private-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PRIVATE'
        )

    def test_zero_point_team_appears_in_rankings(self, team_without_snapshot):
        """New teams without snapshots appear with score=0"""
        from apps.competition.services import CompetitionService
        
        response = CompetitionService.get_global_rankings()
        
        # Ensure new team appears
        team_slugs = [entry.team_slug for entry in response.entries]
        assert team_without_snapshot.slug in team_slugs, "Zero-point team missing from rankings"
        
        # Verify default values
        zero_team_data = next((e for e in response.entries if e.team_slug == team_without_snapshot.slug), None)
        assert zero_team_data is not None
        assert zero_team_data.score == 0, f"Expected score=0, got {zero_team_data.score}"
        assert zero_team_data.tier == 'UNRANKED', f"Expected tier=UNRANKED, got {zero_team_data.tier}"

    def test_private_teams_excluded(self, private_team):
        """Private teams excluded from global rankings"""
        from apps.competition.services import CompetitionService
        
        response = CompetitionService.get_global_rankings()
        
        team_slugs = [entry.team_slug for entry in response.entries]
        assert private_team.slug not in team_slugs, "Private team should not appear in rankings"

    def test_ordering_stable(self, team_with_snapshot, team_without_snapshot):
        """Rankings ordered by score DESC, created_at DESC"""
        from apps.competition.services import CompetitionService
        
        response = CompetitionService.get_global_rankings()
        
        # Find indices
        ranked_idx = next((i for i, e in enumerate(response.entries) if e.team_slug == team_with_snapshot.slug), None)
        new_idx = next((i for i, e in enumerate(response.entries) if e.team_slug == team_without_snapshot.slug), None)
        
        assert ranked_idx is not None, "Ranked team missing"
        assert new_idx is not None, "New team missing"
        
        # Ranked team (1500 score) should appear before new team (0 score)
        assert ranked_idx < new_idx, f"Ranked team (idx {ranked_idx}) should appear before new team (idx {new_idx})"

    def test_multiple_zero_point_teams_ordered_by_created(self, game):
        """Multiple zero-point teams ordered by created_at DESC"""
        from apps.competition.services import CompetitionService
        
        # Create 3 teams without snapshots, different creation times
        team_old = Team.objects.create(
            name='Old Team',
            slug='old-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC',
            created_at=timezone.now() - timedelta(days=10)
        )
        team_mid = Team.objects.create(
            name='Mid Team',
            slug='mid-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC',
            created_at=timezone.now() - timedelta(days=5)
        )
        team_new = Team.objects.create(
            name='New Team',
            slug='new-team-latest',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC',
            created_at=timezone.now()
        )
        
        response = CompetitionService.get_global_rankings()
        
        # Find indices
        old_idx = next((i for i, e in enumerate(response.entries) if e.team_slug == 'old-team'), None)
        mid_idx = next((i for i, e in enumerate(response.entries) if e.team_slug == 'mid-team'), None)
        new_idx = next((i for i, e in enumerate(response.entries) if e.team_slug == 'new-team-latest'), None)
        
        assert all(idx is not None for idx in [old_idx, mid_idx, new_idx]), "Some teams missing"
        
        # Within same score (0), newer teams appear first
        assert new_idx < mid_idx < old_idx, f"Zero-point teams not ordered by created_at DESC: new={new_idx}, mid={mid_idx}, old={old_idx}"
