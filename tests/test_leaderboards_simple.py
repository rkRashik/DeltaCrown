"""
Simple unit tests for Milestone E: Leaderboards & Standings.

This test suite validates the LeaderboardService implementation with minimal dependencies.
Full integration tests will be added in Phase 3 (API endpoints).

Target: 10 core tests covering key scenarios
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from apps.tournaments.models import Game, Tournament, TournamentResult
from apps.tournaments.services.leaderboard import LeaderboardService

User = get_user_model()


@pytest.fixture
def staff_user(db):
    """Create staff user for override tests."""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def tournament(db, staff_user):
    """Create a basic tournament."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create game
    fake_icon = SimpleUploadedFile(
        name='test.png',
        content=b'fake-image-content',
        content_type='image/png'
    )
    
    game = Game.objects.create(
        name='Test Game',
        slug='test-game',
        icon=fake_icon,
        default_team_size=Game.TEAM_SIZE_5V5,
        profile_id_field='game_id',
        default_result_type=Game.MAP_SCORE,
    )
    
    now = timezone.now()
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        description='Test Description',
        game=game,
        organizer=staff_user,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        tournament_start=now,
        registration_start=now - timezone.timedelta(days=7),
        registration_end=now - timezone.timedelta(days=1),
        min_participants=4,
        max_participants=16,
        status=Tournament.LIVE
    )


# ===========================
# BR Leaderboard Tests
# ===========================

@pytest.mark.django_db
class TestBRLeaderboards:
    """Test BR leaderboard calculations (Free Fire, PUBG Mobile)."""
    
    def test_calculate_br_standings_empty_matches(self, tournament):
        """Empty match IDs with non-BR game raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.calculate_br_standings(tournament.id, [])
        
        assert 'not a BR game' in str(exc.value)
    
    def test_calculate_br_standings_invalid_game(self, tournament):
        """Non-BR game raises ValidationError."""
        # tournament.game.slug is 'test-game', not 'free-fire' or 'pubg-mobile'
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.calculate_br_standings(tournament.id, [1, 2, 3])
        
        assert 'not a BR game' in str(exc.value)


# ===========================
# Series Summary Tests  
# ===========================

@pytest.mark.django_db
class TestSeriesSummaries:
    """Test series summary aggregation (Best-of-1/3/5/7)."""
    
    def test_calculate_series_summary_empty_matches(self):
        """Empty match IDs raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.calculate_series_summary([])
        
        assert 'match_ids cannot be empty' in str(exc.value)
    
    def test_calculate_series_summary_nonexistent_matches(self):
        """Nonexistent match IDs raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.calculate_series_summary([99999, 99998])
        
        assert 'No completed matches found' in str(exc.value)


# ===========================
# Staff Override Tests
# ===========================

@pytest.mark.django_db
class TestStaffOverrides:
    """Test staff placement overrides with audit trails."""
    
    def test_override_placement_missing_reason(self, tournament, staff_user):
        """Override without reason raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.override_placement(
                tournament_id=tournament.id,
                registration_id=1,
                new_rank=1,
                reason='',  # Empty reason
                actor_id=staff_user.id
            )
        
        assert 'override reason is required' in str(exc.value).lower()
    
    def test_override_placement_invalid_rank(self, tournament, staff_user):
        """Override with rank < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.override_placement(
                tournament_id=tournament.id,
                registration_id=1,
                new_rank=0,  # Invalid rank
                reason='Test override',
                actor_id=staff_user.id
            )
        
        assert 'new_rank must be >= 1' in str(exc.value).lower()
    
    def test_override_placement_nonexistent_tournament(self, staff_user):
        """Override with invalid tournament ID raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            LeaderboardService.override_placement(
                tournament_id=99999,
                registration_id=1,
                new_rank=1,
                reason='Test override',
                actor_id=staff_user.id
            )
        
        assert 'Tournament 99999 not found' in str(exc.value)
    
    def test_override_placement_valid_creates_result(self, tournament, staff_user):
        """Valid override creates TournamentResult with audit trail."""
        # Create a registration first
        registration = tournament.registrations.create(
            user=staff_user,
            status='confirmed'
        )
        
        result = LeaderboardService.override_placement(
            tournament_id=tournament.id,
            registration_id=registration.id,
            new_rank=1,
            reason='Manual correction after dispute resolution',
            actor_id=staff_user.id
        )
        
        # Verify result created
        assert result['success'] is True
        assert result['result_id'] is not None
        assert result['new_rank'] == 1
        assert result['override_timestamp'] is not None
    
    def test_override_placement_idempotent(self, tournament, staff_user):
        """Applying same override twice is idempotent."""
        # Create a registration first
        registration = tournament.registrations.create(
            user=staff_user,
            status='confirmed'
        )
        
        # First override
        result1 = LeaderboardService.override_placement(
            tournament_id=tournament.id,
            registration_id=registration.id,
            new_rank=1,
            reason='Test override',
            actor_id=staff_user.id
        )
        
        # Second override with same rank
        result2 = LeaderboardService.override_placement(
            tournament_id=tournament.id,
            registration_id=registration.id,
            new_rank=1,
            reason='Test override 2',
            actor_id=staff_user.id
        )
        
        # Should update existing result, not create new one
        assert result1['result_id'] == result2['result_id']
        assert TournamentResult.objects.filter(tournament=tournament).count() == 1


# ===========================
# Integration Tests
# ===========================

@pytest.mark.django_db
class TestLeaderboardServiceIntegration:
    """Integration tests for LeaderboardService."""
    
    def test_service_methods_exist(self):
        """Verify all service methods are available."""
        assert hasattr(LeaderboardService, 'calculate_br_standings')
        assert hasattr(LeaderboardService, 'calculate_series_summary')
        assert hasattr(LeaderboardService, 'override_placement')
    
    def test_service_methods_callable(self):
        """Verify all service methods are callable."""
        assert callable(LeaderboardService.calculate_br_standings)
        assert callable(LeaderboardService.calculate_series_summary)
        assert callable(LeaderboardService.override_placement)
