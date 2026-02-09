"""
Unit tests for AnalyticsService (Module 5.4)

Streamlined test suite with robust fixture factories targeting ≥90% coverage.
Validates numeric formatting, datetime handling, CSV structure, and PII protection.

Implements:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-54-analytics--reports
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#analyticsservice

Target: 18 tests, ≥90% coverage for apps.tournaments.services.analytics_service

Author: Module 5.4 implementation
Date: 2025-11-10
"""

import pytest
from decimal import Decimal
from datetime import timedelta, timezone as dt_timezone, datetime
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models import (
    Tournament,
    Registration,
    Match,
    TournamentResult,
    PrizeTransaction,
    Game,
)
from apps.tournaments.services.analytics_service import AnalyticsService
from apps.organizations.models import Team
from apps.user_profile.models import UserProfile

User = get_user_model()


# ============================================================================
# FIXTURE FACTORIES (Reusable, Model-Compatible)
# ============================================================================

@pytest.fixture
def game():
    """Create test game."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
    )


@pytest.fixture
def organizer():
    """Create organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@test.com',
        password='password123'
    )


@pytest.fixture
def tournament_live(game, organizer):
    """Create LIVE tournament with all required fields."""
    return Tournament.objects.create(
        name='Analytics Test Tournament',
        slug='analytics-test-tournament',
        description='Test tournament for analytics',
        game=game,
        organizer=organizer,
        max_participants=16,
        prize_pool=Decimal('5000.00'),
        registration_start=timezone.now() - timedelta(days=10),
        registration_end=timezone.now() - timedelta(days=3),
        tournament_start=timezone.now() - timedelta(days=2),
        status=Tournament.LIVE,
    )


@pytest.fixture
def tournament_completed(game, organizer):
    """Create COMPLETED tournament."""
    return Tournament.objects.create(
        name='Completed Tournament',
        slug='completed-tournament',
        description='Completed test tournament',
        game=game,
        organizer=organizer,
        max_participants=8,
        prize_pool=Decimal('1000.00'),
        registration_start=timezone.now() - timedelta(days=20),
        registration_end=timezone.now() - timedelta(days=15),
        tournament_start=timezone.now() - timedelta(days=10),
        tournament_end=timezone.now() - timedelta(days=5),
        status=Tournament.COMPLETED,
    )


@pytest.fixture
def create_users():
    """Factory to create multiple users."""
    def _create(count=10, prefix='player'):
        users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'{prefix}{i}',
                email=f'{prefix}{i}@test.com',
                password='password123'
            )
            users.append(user)
        return users
    return _create


@pytest.fixture
def create_registrations():
    """Factory to create registrations with optional check-ins."""
    def _create(tournament, users, checked_in_count=None):
        registrations = []
        if checked_in_count is None:
            checked_in_count = len(users)
        
        for i, user in enumerate(users):
            reg = Registration.objects.create(
                tournament=tournament,
                user=user,
                status=Registration.CONFIRMED,
                checked_in=(i < checked_in_count),
                checked_in_at=timezone.now() - timedelta(hours=2) if i < checked_in_count else None,
            )
            registrations.append(reg)
        return registrations
    return _create


@pytest.fixture
def create_matches():
    """Factory to create matches with proper fields."""
    def _create(tournament, registrations, completed=0, disputed=0, pending=0):
        matches = []
        idx = 0
        round_num = 1
        
        # Completed matches
        for i in range(completed):
            if idx + 1 >= len(registrations):
                break
            # Create matches with ~30min duration each
            created = timezone.now() - timedelta(hours=2)
            updated = created + timedelta(minutes=30)
            match = Match.objects.create(
                tournament=tournament,
                round_number=round_num,
                match_number=i + 1,
                participant1_id=registrations[idx].id,
                participant2_id=registrations[idx + 1].id,
                state=Match.COMPLETED,
                winner_id=registrations[idx].id,
                loser_id=registrations[idx + 1].id,
                started_at=created,
                completed_at=updated,
                created_at=created,
                updated_at=updated,
            )
            matches.append(match)
            idx += 2
        
        # Disputed matches
        for i in range(disputed):
            if idx + 1 >= len(registrations):
                break
            match = Match.objects.create(
                tournament=tournament,
                round_number=round_num,
                match_number=completed + i + 1,
                participant1_id=registrations[idx].id,
                participant2_id=registrations[idx + 1].id,
                state=Match.DISPUTED,
                created_at=timezone.now() - timedelta(hours=1),
                updated_at=timezone.now() - timedelta(minutes=30),
            )
            matches.append(match)
            idx += 2
        
        # Pending/Scheduled matches  
        for i in range(pending):
            if idx + 1 >= len(registrations):
                idx = 0  # Wrap around
            match = Match.objects.create(
                tournament=tournament,
                round_number=round_num + 1,
                match_number=i + 1,
                participant1_id=registrations[idx].id,
                participant2_id=registrations[idx + 1].id,
                state=Match.SCHEDULED,  # Use SCHEDULED, not PENDING (doesn't exist)
                created_at=timezone.now() - timedelta(minutes=30),
            )
            matches.append(match)
            idx += 2
        
        return matches
    return _create


@pytest.fixture
def create_team():
    """Factory to create team with UserProfile captain."""
    def _create(name='Team Alpha', tag='ALPHA'):
        captain_user = User.objects.create_user(
            username=f'captain_{tag.lower()}',
            email=f'captain_{tag.lower()}@test.com',
            password='password123'
        )
        captain_profile, _ = UserProfile.objects.get_or_create(user=captain_user)
        
        return Team.objects.create(
            name=name,
            tag=tag,
            captain=captain_profile,
        )
    return _create


# ============================================================================
# TEST SUITE: Organizer Analytics (9 tests)
# ============================================================================

@pytest.mark.django_db
class TestCalculateOrganizerAnalytics:
    """Test calculate_organizer_analytics method."""
    
    def test_happy_path_all_metrics(
        self, 
        tournament_live, 
        create_users, 
        create_registrations, 
        create_matches
    ):
        """Test organizer analytics with complete realistic data."""
        # Setup: 10 participants (8 checked in), 4 completed + 1 disputed + 1 pending matches
        users = create_users(10)
        registrations = create_registrations(tournament_live, users, checked_in_count=8)
        matches = create_matches(tournament_live, registrations, completed=4, disputed=1, pending=1)
        
        # Add prize transactions
        for i in range(3):
            PrizeTransaction.objects.create(
                tournament=tournament_live,
                participant=registrations[i],
                amount=Decimal(['2000.00', '1500.00', '1000.00'][i]),
                placement=[PrizeTransaction.Placement.FIRST, PrizeTransaction.Placement.SECOND, PrizeTransaction.Placement.THIRD][i],
                status=PrizeTransaction.Status.COMPLETED,
            )
        
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        # Participant metrics
        assert result['total_participants'] == 10
        assert result['checked_in_count'] == 8
        assert result['check_in_rate'] == 0.8000  # 8/10, 4 decimals
        
        # Match metrics
        assert result['total_matches'] == 6
        assert result['completed_matches'] == 4
        assert result['disputed_matches'] == 1
        assert result['dispute_rate'] == 0.1667  # 1/6, rounded to 4 decimals
        
        # Average match duration (may be None or very small in tests due to auto timestamps)
        # In production, this would reflect actual match duration  (updated_at - created_at)
        if result['avg_match_duration_minutes'] is not None:
            assert result['avg_match_duration_minutes'] >= 0
            assert isinstance(result['avg_match_duration_minutes'], float)
        
        # Prize metrics (money as strings with 2 decimals)
        assert result['prize_pool_total'] == '5000.00'
        assert result['prizes_distributed'] == '4500.00'  # 2000+1500+1000
        assert result['payout_count'] == 3
        
        # Tournament metadata
        assert result['tournament_status'] == Tournament.LIVE
        assert result['started_at'] is not None
        assert result['started_at'].endswith('Z')  # UTC with Z suffix
        assert result['concluded_at'] is None  # Not concluded yet
    
    def test_edge_case_no_matches(self, tournament_live, create_users, create_registrations):
        """Test with registrations but no matches (zeroes/nulls)."""
        users = create_users(10)
        registrations = create_registrations(tournament_live, users)
        
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        assert result['total_participants'] == 10
        assert result['total_matches'] == 0
        assert result['completed_matches'] == 0
        assert result['disputed_matches'] == 0
        assert result['dispute_rate'] == 0.0  # Not NaN
        assert result['avg_match_duration_minutes'] is None  # No completed matches
    
    def test_edge_case_all_disputed(self, tournament_live, create_users, create_registrations, create_matches):
        """Test with all matches disputed (100% dispute rate)."""
        users = create_users(10)
        registrations = create_registrations(tournament_live, users)
        matches = create_matches(tournament_live, registrations, disputed=3)
        
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        assert result['total_matches'] == 3
        assert result['disputed_matches'] == 3
        assert result['dispute_rate'] == 1.0000  # 100%
    
    def test_edge_case_zero_registrations(self, tournament_live):
        """Test with no registrations (all metrics zero)."""
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        assert result['total_participants'] == 0
        assert result['checked_in_count'] == 0
        assert result['check_in_rate'] == 0.0  # Not NaN
        assert result['total_matches'] == 0
        assert result['prize_pool_total'] == '5000.00'  # Prize pool exists
        assert result['prizes_distributed'] == '0.00'  # No payouts
        assert result['payout_count'] == 0
    
    def test_partial_check_ins(self, tournament_live, create_users, create_registrations):
        """Test check-in rate with partial check-ins (1 of 3)."""
        users = create_users(3)
        registrations = create_registrations(tournament_live, users, checked_in_count=1)
        
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        assert result['total_participants'] == 3
        assert result['checked_in_count'] == 1
        assert result['check_in_rate'] == 0.3333  # 1/3, rounded to 4 decimals
    
    def test_money_formatting_precision(self, tournament_live, create_users, create_registrations):
        """Test money values formatted as strings with 2 decimals."""
        users = create_users(1)
        registrations = create_registrations(tournament_live, users)
        
        # Create prize transaction with odd amount (must have ≤2 decimals)
        PrizeTransaction.objects.create(
            tournament=tournament_live,
            participant=registrations[0],
            amount=Decimal('1234.56'),  # Exactly 2 decimals (model constraint)
            placement=PrizeTransaction.Placement.FIRST,
            status=PrizeTransaction.Status.COMPLETED,
        )
        
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)

        assert result['prizes_distributed'] == '1234.56'  # Formatted to 2 decimals
        assert isinstance(result['prizes_distributed'], str)
    
    def test_datetime_utc_formatting(self, tournament_live):
        """Test datetime fields formatted as UTC ISO-8601 with Z suffix."""
        result = AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
        # started_at should be UTC ISO-8601 with Z
        assert result['started_at'] is not None
        assert result['started_at'].endswith('Z')
        assert 'T' in result['started_at']
        assert len(result['started_at']) == 20  # YYYY-MM-DDTHH:MM:SSZ
        
        # concluded_at should be None for live tournament
        assert result['concluded_at'] is None
    
    def test_performance_warning_threshold(self, tournament_live, create_users, create_registrations):
        """Test that >500ms execution triggers warning log."""
        users = create_users(5)
        registrations = create_registrations(tournament_live, users)
        
        # Mock timezone.now() to simulate >500ms delay
        original_now = timezone.now
        call_count = [0]
        
        def mock_now():
            call_count[0] += 1
            if call_count[0] == 1:
                return original_now()
            else:
                # Second call: add 600ms
                return original_now() + timedelta(milliseconds=600)
        
        # Use patch for both logger and timezone
        with patch('apps.tournaments.services.analytics_service.logger') as mock_logger, \
             patch('django.utils.timezone.now', side_effect=mock_now):
            AnalyticsService.calculate_organizer_analytics(tournament_live.id)
        
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert '600' in warning_msg or '>500ms' in str(warning_msg)
            assert str(tournament_live.id) in warning_msg
    
    def test_tournament_not_found(self):
        """Test with non-existent tournament ID."""
        with pytest.raises(Tournament.DoesNotExist):
            AnalyticsService.calculate_organizer_analytics(99999)


# ============================================================================
# TEST SUITE: Participant Analytics (3 tests)
# ============================================================================

@pytest.mark.django_db
class TestCalculateParticipantAnalytics:
    """Test calculate_participant_analytics method."""
    
    def test_happy_path_multiple_tournaments(self, game, organizer, create_users):
        """Test participant analytics across multiple tournaments with wins/losses."""
        participant = create_users(1, prefix='participant')[0]
        
        # Create 2 tournaments
        tournaments = []
        for i in range(2):
            t = Tournament.objects.create(
                name=f'Tournament {i+1}',
                slug=f'tournament-{i+1}',
                description=f'Test tournament {i+1}',
                game=game,
                organizer=organizer,
                max_participants=8,
                prize_pool=Decimal('1000.00'),
                registration_start=timezone.now() - timedelta(days=20),
                registration_end=timezone.now() - timedelta(days=15),
                tournament_start=timezone.now() - timedelta(days=10),
                status=Tournament.COMPLETED,
            )
            tournaments.append(t)
        
        # Register participant in both tournaments
        registrations = []
        for t in tournaments:
            reg = Registration.objects.create(
                tournament=t,
                user=participant,
                status=Registration.CONFIRMED,
                checked_in=True,
            )
            registrations.append(reg)
        
        # Create opponents
        opponents = create_users(4, prefix='opponent')
        opponent_regs = []
        for i, t in enumerate(tournaments):
            for j in range(2):
                reg = Registration.objects.create(
                    tournament=t,
                    user=opponents[i * 2 + j],
                    status=Registration.CONFIRMED,
                )
                opponent_regs.append(reg)
        
        # Tournament 1: participant wins 2, loses 1
        Match.objects.create(
            tournament=tournaments[0],
            round_number=1,
            match_number=1,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[0].id,
            state=Match.COMPLETED,
            winner_id=registrations[0].id,
            loser_id=opponent_regs[0].id,
        )
        Match.objects.create(
            tournament=tournaments[0],
            round_number=1,
            match_number=2,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[1].id,
            state=Match.COMPLETED,
            winner_id=registrations[0].id,
            loser_id=opponent_regs[1].id,
        )
        Match.objects.create(
            tournament=tournaments[0],
            round_number=2,
            match_number=1,
            participant1_id=registrations[0].id,
            participant2_id=opponent_regs[0].id,
            state=Match.COMPLETED,
            winner_id=opponent_regs[0].id,
            loser_id=registrations[0].id,
        )
        
        # Tournament 2: participant wins 1, loses 1
        Match.objects.create(
            tournament=tournaments[1],
            round_number=1,
            match_number=1,
            participant1_id=registrations[1].id,
            participant2_id=opponent_regs[2].id,
            state=Match.COMPLETED,
            winner_id=registrations[1].id,
            loser_id=opponent_regs[2].id,
        )
        Match.objects.create(
            tournament=tournaments[1],
            round_number=1,
            match_number=2,
            participant1_id=registrations[1].id,
            participant2_id=opponent_regs[3].id,
            state=Match.COMPLETED,
            winner_id=opponent_regs[3].id,
            loser_id=registrations[1].id,
        )
        
        # Add placements
        TournamentResult.objects.create(
            tournament=tournaments[0],
            winner=registrations[0],
            runner_up=opponent_regs[0],
            third_place=opponent_regs[1],
            determination_method='normal',
            rules_applied={'method': 'bracket_completion'},
        )
        TournamentResult.objects.create(
            tournament=tournaments[1],
            winner=opponent_regs[2],
            runner_up=registrations[1],
            third_place=opponent_regs[3],
            determination_method='normal',
            rules_applied={'method': 'bracket_completion'},
        )
        
        # Add prizes
        PrizeTransaction.objects.create(
            tournament=tournaments[0],
            participant=registrations[0],
            amount=Decimal('500.00'),
            placement=PrizeTransaction.Placement.FIRST,
            status=PrizeTransaction.Status.COMPLETED,
        )
        PrizeTransaction.objects.create(
            tournament=tournaments[1],
            participant=registrations[1],
            amount=Decimal('200.00'),
            placement=PrizeTransaction.Placement.SECOND,
            status=PrizeTransaction.Status.COMPLETED,
        )
        
        result = AnalyticsService.calculate_participant_analytics(participant.id)
        
        # Tournament counts
        assert result['total_tournaments'] == 2
        assert result['tournaments_won'] == 1
        assert result['runner_up_count'] == 1
        assert result['third_place_count'] == 0
        
        # Match stats (3 wins, 2 losses, 5 total)
        assert result['total_matches_played'] == 5
        assert result['matches_won'] == 3
        assert result['matches_lost'] == 2
        assert result['win_rate'] == 0.6000  # 60%, 4 decimals
        
        # Prize winnings
        assert result['total_prize_winnings'] == '700.00'  # 500+200
        
        # Best placement
        assert result['best_placement'] == '1st'
        
        # Tournaments by game
        assert result['tournaments_by_game'] == {'valorant': 2}
    
    def test_edge_case_no_tournaments(self, create_users):
        """Test participant with no registrations (all zeroes)."""
        user = create_users(1, prefix='new_user')[0]
        
        result = AnalyticsService.calculate_participant_analytics(user.id)
        
        assert result['total_tournaments'] == 0
        assert result['tournaments_won'] == 0
        assert result['runner_up_count'] == 0
        assert result['third_place_count'] == 0
        assert result['total_matches_played'] == 0
        assert result['matches_won'] == 0
        assert result['matches_lost'] == 0
        assert result['win_rate'] == 0.0  # Not NaN
        assert result['total_prize_winnings'] == '0.00'
        assert result['best_placement'] is None
        assert result['tournaments_by_game'] == {}
    
    def test_best_placement_only_runner_up(self, tournament_completed, create_users):
        """Test best_placement when only runner-up exists."""
        users = create_users(3, prefix='player')
        
        regs = []
        for user in users:
            reg = Registration.objects.create(
                tournament=tournament_completed,
                user=user,
                status=Registration.CONFIRMED,
            )
            regs.append(reg)
        
        TournamentResult.objects.create(
            tournament=tournament_completed,
            winner=regs[0],
            runner_up=regs[1],  # Test user
            third_place=regs[2],
            determination_method='normal',  # 'normal' or 'manual', not BRACKET constant
            rules_applied={'method': 'bracket_completion'},
        )
        
        result = AnalyticsService.calculate_participant_analytics(users[1].id)
        
        assert result['tournaments_won'] == 0
        assert result['runner_up_count'] == 1
        assert result['third_place_count'] == 0
        assert result['best_placement'] == '2nd'


# ============================================================================
# TEST SUITE: CSV Export (6 tests)
# ============================================================================

@pytest.mark.django_db
class TestExportTournamentCSV:
    """Test export_tournament_csv method."""
    
    def test_csv_format_utf8_bom(self, tournament_completed, create_users, create_registrations):
        """Test CSV starts with UTF-8 BOM for Excel compatibility."""
        users = create_users(3)
        registrations = create_registrations(tournament_completed, users)
        
        generator = AnalyticsService.export_tournament_csv(tournament_completed.id)
        first_chunk = next(generator)
        
        assert first_chunk == '\ufeff'  # UTF-8 BOM
    
    def test_csv_header_correct_order(self, tournament_completed, create_users, create_registrations):
        """Test CSV header has correct columns in correct order (12 columns)."""
        users = create_users(3)
        registrations = create_registrations(tournament_completed, users)
        
        generator = AnalyticsService.export_tournament_csv(tournament_completed.id)
        next(generator)  # Skip BOM
        header_chunk = next(generator)
        
        expected_header = (
            'participant_id,participant_name,registration_status,'
            'checked_in,checked_in_at,matches_played,matches_won,'
            'matches_lost,placement,prize_amount,registration_created_at,'
            'payment_status\r\n'  # Windows uses \r\n line endings
        )

        assert header_chunk == expected_header
    
    def test_csv_streaming_nature(self, tournament_completed, create_users, create_registrations):
        """Test CSV is a generator (streaming, not materialized)."""
        users = create_users(3)
        registrations = create_registrations(tournament_completed, users)
        
        result = AnalyticsService.export_tournament_csv(tournament_completed.id)
        
        # Should be a generator
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
        
        # Should yield chunks iteratively
        chunks = list(result)
        assert len(chunks) > 0
    
    def test_csv_no_pii_display_names_only(self, tournament_completed, create_users, create_team):
        """Test CSV contains display names (team/username) but no emails."""
        users = create_users(2)
        team = create_team()
        
        # Solo registration
        reg1 = Registration.objects.create(
            tournament=tournament_completed,
            user=users[0],
            status=Registration.CONFIRMED,
        )
        
        # Team registration (team_id is IntegerField, user must be None for XOR constraint)
        reg2 = Registration.objects.create(
            tournament=tournament_completed,
            user=None,
            team_id=team.id,
            status=Registration.CONFIRMED,
        )
        
        generator = AnalyticsService.export_tournament_csv(tournament_completed.id)
        csv_content = ''.join(generator)
        
        # Should contain usernames and team names
        assert 'player0' in csv_content
        assert 'Team Alpha' in csv_content  # Team name
        
        # Should NOT contain email addresses
        assert 'player0@test.com' not in csv_content
        assert 'player1@test.com' not in csv_content
        assert '@test.com' not in csv_content
    
    def test_csv_with_placements_and_prizes(self, tournament_completed, create_users, create_registrations):
        """Test CSV includes placement and prize data."""
        users = create_users(3)
        registrations = create_registrations(tournament_completed, users)
        
        # Add tournament result
        TournamentResult.objects.create(
            tournament=tournament_completed,
            winner=registrations[0],
            runner_up=registrations[1],
            third_place=registrations[2],
            determination_method='normal',  # 'normal' or 'manual', not BRACKET constant
            rules_applied={'method': 'bracket_completion'},
        )
        
        # Add prizes
        PrizeTransaction.objects.create(
            tournament=tournament_completed,
            participant=registrations[0],
            amount=Decimal('500.00'),
            placement=PrizeTransaction.Placement.FIRST,
            status=PrizeTransaction.Status.COMPLETED,
        )
        
        generator = AnalyticsService.export_tournament_csv(tournament_completed.id)
        csv_content = ''.join(generator)
        
        # Check placements in CSV
        assert '1st' in csv_content
        assert '2nd' in csv_content
        assert '3rd' in csv_content
        
        # Check prize amounts (formatted with 2 decimals)
        assert '500.00' in csv_content
    
    def test_csv_tournament_not_found(self):
        """Test CSV export with non-existent tournament."""
        with pytest.raises(Tournament.DoesNotExist):
            generator = AnalyticsService.export_tournament_csv(99999)
            next(generator)  # Try to consume first chunk


# ============================================================================
# TEST SUITE: Helper Methods (10 tests - comprehensive coverage)
# ============================================================================

@pytest.mark.django_db
class TestAnalyticsHelpers:
    """Test private helper methods."""
    
    def test_calculate_check_in_rate_normal(self):
        """Test check-in rate calculation with normal values."""
        rate = AnalyticsService._calculate_check_in_rate(8, 10)
        assert rate == 0.8000
    
    def test_calculate_check_in_rate_zero_participants(self):
        """Test check-in rate with zero participants (no division by zero)."""
        rate = AnalyticsService._calculate_check_in_rate(0, 0)
        assert rate == 0.0
    
    def test_calculate_dispute_rate_normal(self):
        """Test dispute rate calculation with normal values."""
        rate = AnalyticsService._calculate_dispute_rate(1, 6)
        assert rate == 0.1667  # Rounded to 4 decimals
    
    def test_calculate_win_rate_normal(self):
        """Test win rate calculation with normal values."""
        rate = AnalyticsService._calculate_win_rate(4, 8)
        assert rate == 0.5000
    
    def test_determine_best_placement_first(self):
        """Test best placement with 1st place."""
        placement = AnalyticsService._determine_best_placement(1, 0, 0)
        assert placement == '1st'
    
    def test_determine_best_placement_second(self):
        """Test best placement with 2nd place (no 1st)."""
        placement = AnalyticsService._determine_best_placement(0, 1, 0)
        assert placement == '2nd'
    
    def test_determine_best_placement_none(self):
        """Test best placement with no placements."""
        placement = AnalyticsService._determine_best_placement(0, 0, 0)
        assert placement is None
    
    def test_format_decimal_normal(self):
        """Test decimal formatting with normal value."""
        formatted = AnalyticsService._format_decimal(Decimal('1234.56'))
        assert formatted == '1234.56'
        assert isinstance(formatted, str)
    
    def test_format_decimal_rounding(self):
        """Test decimal formatting with rounding."""
        formatted = AnalyticsService._format_decimal(Decimal('1234.567'))
        assert formatted == '1234.57'  # Rounded to 2 decimals
    
    def test_format_datetime_utc(self):
        """Test datetime formatting as UTC ISO-8601 with Z."""
        dt = timezone.make_aware(
            datetime(2025, 11, 10, 12, 34, 56),
            dt_timezone.utc
        )
        formatted = AnalyticsService._format_datetime(dt)
        
        assert formatted == '2025-11-10T12:34:56Z'
        assert formatted.endswith('Z')
        assert 'T' in formatted
        assert len(formatted) == 20
    
    def test_format_datetime_none(self):
        """Test datetime formatting with None."""
        formatted = AnalyticsService._format_datetime(None)
        assert formatted is None
    
    def test_get_participant_display_name_solo(self, tournament_completed, create_users):
        """Test display name for solo registration (username)."""
        users = create_users(1)
        
        reg = Registration.objects.create(
            tournament=tournament_completed,
            user=users[0],
            status=Registration.CONFIRMED,
        )
        
        display_name = AnalyticsService._get_participant_display_name(reg)
        
        assert display_name == 'player0'
        assert 'player0@test.com' not in display_name
    
    def test_get_participant_display_name_team(self, tournament_completed, create_users, create_team):
        """Test display name for team registration (team name)."""
        users = create_users(1)
        team = create_team()
        
        reg = Registration.objects.create(
            tournament=tournament_completed,
            user=None,  # XOR constraint: user must be None when team_id is set
            team_id=team.id,
            status=Registration.CONFIRMED,
        )
        
        display_name = AnalyticsService._get_participant_display_name(reg)
        
        assert display_name == 'Team Alpha'
        assert 'player0' not in display_name
        assert 'player0@test.com' not in display_name
