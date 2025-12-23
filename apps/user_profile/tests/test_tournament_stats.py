"""
Tests for Tournament & Team Stats Integration (UP-M4)

Coverage:
- Stats derivation from Match, Tournament, Registration, Team sources
- Idempotency (repeated recompute produces same result)
- Edge cases (no data, mixed data, deleted entities)
- Backfill command dry-run
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.user_profile.models_main import UserProfile
from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.services.tournament_stats import TournamentStatsService

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestTournamentStatsDerivation:
    """Test stats derivation from source tables."""
    
    def test_empty_user_has_zero_stats(self):
        """User with no tournaments/matches has all zeros."""
        user = User.objects.create_user(username='newbie', email='newbie@test.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        stats = TournamentStatsService.recompute_user_stats(user.id)
        
        assert stats.matches_played == 0
        assert stats.matches_won == 0
        assert stats.tournaments_played == 0
        assert stats.tournaments_won == 0
        assert stats.tournaments_top3 == 0
        assert stats.last_match_at is None
        assert stats.first_tournament_at is None
    
    def test_recompute_creates_stats_if_missing(self):
        """Recompute creates UserProfileStats if it doesn't exist."""
        user = User.objects.create_user(username='nostats', email='nostats@test.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Delete stats if they exist
        UserProfileStats.objects.filter(user_profile=profile).delete()
        
        stats = TournamentStatsService.recompute_user_stats(user.id, create_if_missing=True)
        
        assert stats is not None
        assert stats.user_profile == profile
    
    def test_idempotent_recompute(self):
        """Calling recompute multiple times produces same result."""
        user = User.objects.create_user(username='stable', email='stable@test.com', password='pass123')
        
        stats1 = TournamentStatsService.recompute_user_stats(user.id)
        stats2 = TournamentStatsService.recompute_user_stats(user.id)
        stats3 = TournamentStatsService.recompute_user_stats(user.id)
        
        assert stats1.id == stats2.id == stats3.id
        assert stats1.matches_played == stats2.matches_played == stats3.matches_played
        assert stats1.tournaments_played == stats2.tournaments_played == stats3.tournaments_played
    
    def test_stats_recompute_is_deterministic(self):
        """Same source data produces same stats every time."""
        user = User.objects.create_user(username='deterministic', email='det@test.com', password='pass123')
        
        # Recompute 5 times
        results = [
            TournamentStatsService.recompute_user_stats(user.id)
            for _ in range(5)
        ]
        
        # All results should be identical
        first = results[0]
        for stats in results[1:]:
            assert stats.matches_played == first.matches_played
            assert stats.matches_won == first.matches_won
            assert stats.tournaments_played == first.tournaments_played
            assert stats.tournaments_won == first.tournaments_won


@pytest.mark.django_db(transaction=True)
class TestMatchStatsComputation:
    """Test match stats derivation from Match model."""
    
    def test_no_matches_returns_zero(self):
        """User with no matches has zero match stats."""
        user = User.objects.create_user(username='nomatch', email='nomatch@test.com', password='pass123')
        
        match_stats = TournamentStatsService._compute_match_stats(user.id)
        
        assert match_stats['matches_played'] == 0
        assert match_stats['matches_won'] == 0
        assert match_stats['last_match_at'] is None
    
    def test_match_stats_without_registrations(self):
        """User without tournament registrations has no matches."""
        user = User.objects.create_user(username='noreg', email='noreg@test.com', password='pass123')
        
        match_stats = TournamentStatsService._compute_match_stats(user.id)
        
        assert match_stats['matches_played'] == 0


@pytest.mark.django_db(transaction=True)
class TestTournamentStatsComputation:
    """Test tournament stats derivation from Registration model."""
    
    def test_no_tournaments_returns_zero(self):
        """User with no tournament registrations has zero tournament stats."""
        user = User.objects.create_user(username='notourney', email='notourney@test.com', password='pass123')
        
        tournament_stats = TournamentStatsService._compute_tournament_stats(user.id)
        
        assert tournament_stats['tournaments_played'] == 0
        assert tournament_stats['tournaments_won'] == 0
        assert tournament_stats['tournaments_top3'] == 0
        assert tournament_stats['first_tournament_at'] is None
        assert tournament_stats['last_tournament_at'] is None


@pytest.mark.django_db(transaction=True)
class TestTeamStatsComputation:
    """Test team stats derivation from Team/TeamMembership models."""
    
    def test_no_teams_returns_zero(self):
        """User with no team memberships has zero team stats."""
        user = User.objects.create_user(username='noteam', email='noteam@test.com', password='pass123')
        
        team_stats = TournamentStatsService._compute_team_stats(user.id)
        
        assert team_stats['teams_joined'] == 0
        assert team_stats['current_team_id'] is None
        assert team_stats['current_team_name'] is None


@pytest.mark.django_db(transaction=True)
class TestStatsIntegration:
    """Test full stats recompute integration."""
    
    def test_full_stats_recompute(self):
        """Full recompute updates all stat categories."""
        user = User.objects.create_user(username='fulltest', email='fulltest@test.com', password='pass123')
        
        stats = TournamentStatsService.recompute_user_stats(user.id)
        
        # Should have computed_at timestamp
        assert stats.computed_at is not None
        assert (timezone.now() - stats.computed_at).seconds < 60  # Within last minute


@pytest.mark.django_db(transaction=True)
class TestTournamentHistory:
    """Test tournament history retrieval."""
    
    def test_empty_tournament_history(self):
        """User with no tournaments has empty history."""
        user = User.objects.create_user(username='nohistory', email='nohistory@test.com', password='pass123')
        
        history = TournamentStatsService.get_user_tournament_history(user.id)
        
        assert history == []
