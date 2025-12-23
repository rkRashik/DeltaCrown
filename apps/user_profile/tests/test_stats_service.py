"""
Tests for StatsUpdateService

Validates:
- Stats recomputation accuracy
- Derived field calculations (win_rate, net_earnings)
- Profile cache sync
- Staleness detection
"""

import pytest
import uuid
from django.utils import timezone
from datetime import timedelta
from apps.user_profile.services.activity_service import UserActivityService
from apps.user_profile.services.stats_service import StatsUpdateService
from apps.user_profile.models.stats import UserProfileStats
from apps.user_profile.models.activity import UserActivity, EventType
from apps.accounts.models import User
from apps.user_profile.models import UserProfile


def unique_id():
    """Generate unique ID for test data."""
    return abs(hash(uuid.uuid4())) % 1000000


@pytest.fixture
def test_user(db):
    """Create test user with profile."""
    user = User.objects.create_user(
        username=f'statsuser_{unique_id()}',
        email=f'stats_{unique_id()}@example.com',
        password='testpass123'
    )
    # Ensure UserProfile exists (created by signal or explicitly)
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.mark.django_db
class TestStatsRecomputation:
    """Test stats recomputation from events."""
    
    def test_recompute_empty_stats(self, test_user):
        """Should create stats with zeros for user with no events."""
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        assert stats is not None
        assert stats.tournaments_played == 0
        assert stats.matches_played == 0
        assert stats.total_earnings == 0
        assert stats.total_spent == 0
    
    def test_recompute_tournament_stats(self, test_user):
        """Should count tournament events correctly."""
        # Create tournament events
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=unique_id(),
            registration_id=unique_id()
        )
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=unique_id(),
            registration_id=unique_id()
        )
        UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=1,
            prize_amount=500.00
        )
        
        # Recompute stats
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        assert stats.tournaments_played == 2
        assert stats.tournaments_won == 1
    
    def test_recompute_match_stats(self, test_user, db):
        """Should count match wins/losses correctly."""
        opponent = User.objects.create_user(
            username=f'opponent_{unique_id()}',
            email=f'opp_{unique_id()}@example.com',
            password='pass123'
        )
        UserProfile.objects.get_or_create(user=opponent)  # Ensure profile exists
        
        # Win 3 matches
        for i in range(3):
            UserActivityService.record_match_result(
                match_id=unique_id(),
                winner_id=test_user.id,
                loser_id=opponent.id
            )
        
        # Lose 1 match
        UserActivityService.record_match_result(
            match_id=unique_id(),
            winner_id=opponent.id,
            loser_id=test_user.id
        )
        
        # Recompute stats
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        assert stats.matches_played == 4
        assert stats.matches_won == 3
        assert stats.win_rate == 0.75
    
    def test_recompute_economy_stats(self, test_user):
        """Should sum earnings and spending correctly."""
        # Earn coins
        UserActivityService.record_economy_transaction(
            transaction_id=100,
            user_id=test_user.id,
            amount=500.00,
            reason='TOURNAMENT_WIN'
        )
        UserActivityService.record_economy_transaction(
            transaction_id=101,
            user_id=test_user.id,
            amount=200.00,
            reason='MATCH_WIN'
        )
        
        # Spend coins
        UserActivityService.record_economy_transaction(
            transaction_id=102,
            user_id=test_user.id,
            amount=-50.00,
            reason='ENTRY_FEE'
        )
        
        # Recompute stats
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        assert stats.total_earnings == 700.00
        assert stats.total_spent == 50.00
        assert stats.net_earnings == 650.00
    
    def test_recompute_timestamps(self, test_user, db):
        """Should track first/last activity timestamps."""
        opponent_id = unique_id()
        ts1 = timezone.now() - timedelta(days=10)
        ts2 = timezone.now() - timedelta(days=5)
        ts3 = timezone.now()
        
        # Create events at different times
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=unique_id(),
            registration_id=unique_id()
        )
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=unique_id(),
            registration_id=unique_id()
        )
        # Create opponent user for match
        opponent = User.objects.create_user(
            username=f'opp_time_{unique_id()}',
            email=f'opp_time_{unique_id()}@example.com',
            password='pass'
        )
        UserActivityService.record_match_result(
            match_id=unique_id(),
            winner_id=test_user.id,
            loser_id=opponent.id
        )
        
        # Recompute stats
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        # Should track first and last tournament
        assert stats.first_tournament_at is not None
        assert stats.last_tournament_at is not None
        assert stats.last_match_at is not None


@pytest.mark.django_db
class TestStatsAccuracy:
    """Test stats calculation accuracy."""
    
    def test_win_rate_calculation(self, test_user, db):
        """Should calculate win rate correctly."""
        opponent = User.objects.create_user(
            username=f'opp_wr_{unique_id()}',
            email=f'opp_wr_{unique_id()}@example.com',
            password='pass'
        )
        
        # Win 7, lose 3 (70% win rate)
        for i in range(7):
            UserActivityService.record_match_result(
                match_id=unique_id(),
                winner_id=test_user.id,
                loser_id=opponent.id
            )
        
        for i in range(3):
            UserActivityService.record_match_result(
                match_id=unique_id(),
                winner_id=opponent.id,
                loser_id=test_user.id
            )
        
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        assert stats.matches_played == 10
        assert stats.matches_won == 7
        assert stats.win_rate == 0.7
    
    def test_win_rate_zero_matches(self, test_user):
        """Should return 0 win rate if no matches played."""
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        assert stats.win_rate == 0.0
    
    def test_top3_placement_count(self, test_user):
        """Should count top 3 tournament placements."""
        # 1st, 2nd, 3rd, 4th place
        UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=1
        )
        UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=2
        )
        UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=3
        )
        UserActivityService.record_tournament_placed(
            user_id=test_user.id,
            tournament_id=unique_id(),
            placement=4
        )
        
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        # Only top 3 should count
        assert stats.tournaments_top3 == 3


@pytest.mark.django_db
class TestStatsIdempotency:
    """Test recomputation idempotency."""
    
    def test_recompute_idempotent(self, test_user):
        """Should produce same results when run multiple times."""
        # Create events
        UserActivityService.record_tournament_join(
            user_id=test_user.id,
            tournament_id=100,
            registration_id=200
        )
        
        # Recompute twice
        stats1 = StatsUpdateService.update_stats_for_user(test_user.id)
        stats2 = StatsUpdateService.update_stats_for_user(test_user.id)
        
        # Should be same instance (OneToOne)
        assert stats1.id == stats2.id
        assert stats1.tournaments_played == stats2.tournaments_played == 1


@pytest.mark.django_db
class TestStatsStaleness:
    """Test staleness detection."""
    
    def test_fresh_stats(self, test_user):
        """Should not be stale when just computed."""
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        assert not stats.is_stale(max_age_hours=24)
    
    def test_stale_stats(self, test_user):
        """Should be stale after max_age_hours."""
        stats = StatsUpdateService.update_stats_for_user(test_user.id)
        
        # Manually set computed_at to 48 hours ago
        # Use update() to bypass auto_now
        old_time = timezone.now() - timedelta(hours=48)
        UserProfileStats.objects.filter(id=stats.id).update(computed_at=old_time)
        stats.refresh_from_db()
        
        # Should be stale (older than 24 hours)
        assert stats.is_stale(max_age_hours=24)


@pytest.mark.django_db
class TestBatchUpdate:
    """Test batch stats updates."""
    
    def test_batch_update_multiple_users(self, db):
        """Should update stats for multiple users."""
        # Create 3 users
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'user{i}_{unique_id()}',
                email=f'user{i}_{unique_id()}@example.com',
                password='pass'
            )
            UserProfile.objects.get_or_create(user=user)  # Ensure profile exists
            users.append(user)
            
            # Create event for each
            UserActivityService.record_tournament_join(
                user_id=user.id,
                tournament_id=100 + i,
                registration_id=200 + i + unique_id()  # Make unique
            )
        
        # Batch update
        user_ids = [u.id for u in users]
        result = StatsUpdateService.update_stats_for_users(user_ids)
        
        assert len(result['success']) == 3
        assert len(result['failed']) == 0
        
        # Verify all stats created
        for user in users:
            stats = UserProfileStats.objects.get(user_profile__user=user)
            assert stats.tournaments_played == 1
