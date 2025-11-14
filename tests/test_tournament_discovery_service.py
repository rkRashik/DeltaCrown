"""
Tests for Tournament Discovery Service (Module 2.4).

Source Documents:
- Documents/ExecutionPlan/BACKEND_ONLY_BACKLOG.md (Module 2.4, Lines 214-241)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Section 5.1)

Test Coverage:
- Full-text search functionality
- Game filtering
- Date range filtering
- Status filtering
- Prize pool filtering
- Entry fee filtering
- Format filtering
- Upcoming tournaments query
- Live tournaments query
- Featured tournaments query
- Permission and visibility logic
- Query optimization validation

Success Criteria (from planning docs):
- 20+ service tests
- ≥80% coverage
- All filtering combinations work correctly
- Visibility rules enforced
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tournaments.models.tournament import Tournament, Game
from apps.tournaments.services.tournament_discovery_service import TournamentDiscoveryService

User = get_user_model()


@pytest.mark.django_db
class TestSearchTournaments:
    """Test full-text search functionality."""
    
    def test_search_by_name(self, sample_organizer):
        """Test searching tournaments by name."""
        # Create two different games to avoid name collision
        game1 = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        game2 = Game.objects.create(name='eFootball', slug='efootball', is_active=True)
        
        # Create tournaments with different names
        Tournament.objects.create(
            name='Valorant Champions Cup',
            description='Championship tournament',
            game=game1,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='eFootball League',
            description='Competitive eFootball tournament',
            game=game2,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        # Search for "Champions" (specific to Valorant tournament)
        results = TournamentDiscoveryService.search_tournaments(query='Champions')
        
        assert results.count() == 1
        assert 'Champions' in results.first().name
    
    def test_search_by_description(self, sample_game, sample_organizer):
        """Test searching tournaments by description."""
        Tournament.objects.create(
            name='Summer Cup',
            description='A competitive esports championship for all players',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.search_tournaments(query='championship')
        
        assert results.count() == 1
        assert 'championship' in results.first().description.lower()
    
    def test_search_with_filters(self, sample_game, sample_organizer):
        """Test search with additional filters."""
        # Create tournaments
        Tournament.objects.create(
            name='Valorant Champions',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED,
            is_official=True
        )
        Tournament.objects.create(
            name='Valorant Community Cup',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED,
            is_official=False
        )
        
        # Search with official filter
        results = TournamentDiscoveryService.search_tournaments(
            query='Valorant',
            filters={'is_official': True}
        )
        
        assert results.count() == 1
        assert results.first().is_official is True
    
    def test_search_empty_query(self, sample_game, sample_organizer):
        """Test search with empty query returns all visible tournaments."""
        Tournament.objects.create(
            name='Tournament 1',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Tournament 2',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.search_tournaments(query='')
        
        assert results.count() == 2
    
    def test_search_ordering(self, sample_game, sample_organizer):
        """Test search with custom ordering."""
        # Create tournaments with different prize pools
        Tournament.objects.create(
            name='Low Prize Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='High Prize Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('10000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.search_tournaments(
            query='',
            ordering='-prize_pool'
        )
        
        assert results.first().name == 'High Prize Tournament'
    
    def test_search_invalid_ordering(self, sample_game):
        """Test search with invalid ordering raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ordering field"):
            TournamentDiscoveryService.search_tournaments(
                query='',
                ordering='invalid_field'
            )


@pytest.mark.django_db
class TestFilterByGame:
    """Test game filtering functionality."""
    
    def test_filter_by_game_basic(self, sample_organizer):
        """Test filtering tournaments by game."""
        game1 = Game.objects.create(name='Valorant', slug='valorant', is_active=True)
        game2 = Game.objects.create(name='eFootball', slug='efootball', is_active=True)
        
        # Create tournaments for different games
        Tournament.objects.create(
            name='Valorant Cup',
            game=game1,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='eFootball League',
            game=game2,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.filter_by_game(game_id=game1.id)
        
        assert results.count() == 1
        assert results.first().game == game1
    
    def test_filter_by_game_excludes_drafts(self, sample_game, sample_organizer):
        """Test that game filter excludes drafts by default."""
        Tournament.objects.create(
            name='Published Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Draft Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        
        results = TournamentDiscoveryService.filter_by_game(
            game_id=sample_game.id,
            include_draft=False
        )
        
        assert results.count() == 1
        assert results.first().status == Tournament.PUBLISHED
    
    def test_filter_by_game_with_organizer_sees_own_drafts(self, sample_game, sample_organizer):
        """Test that organizers can see their own drafts when include_draft=True."""
        Tournament.objects.create(
            name='Published Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='My Draft Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        
        # Organizer with include_draft=True sees own draft
        results_with_drafts = TournamentDiscoveryService.filter_by_game(
            game_id=sample_game.id,
            include_draft=True,
            user=sample_organizer
        )
        assert results_with_drafts.count() == 2
        
        # Organizer with include_draft=False only sees published
        results_without_drafts = TournamentDiscoveryService.filter_by_game(
            game_id=sample_game.id,
            include_draft=False,
            user=sample_organizer
        )
        assert results_without_drafts.count() == 1
    
    def test_filter_by_invalid_game(self):
        """Test filtering by invalid game ID raises DoesNotExist."""
        with pytest.raises(Game.DoesNotExist):
            TournamentDiscoveryService.filter_by_game(game_id=9999)


@pytest.mark.django_db
class TestFilterByDateRange:
    """Test date range filtering functionality."""
    
    def test_filter_by_date_range_basic(self, sample_game, sample_organizer):
        """Test filtering tournaments by date range."""
        # Create tournaments with different start dates
        Tournament.objects.create(
            name='Early Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Late Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() + timedelta(days=30),
            registration_end=timezone.now() + timedelta(days=35),
            tournament_start=timezone.now() + timedelta(days=37),
            status=Tournament.PUBLISHED
        )
        
        # Filter for tournaments starting in next 10 days
        start_date = timezone.now()
        end_date = timezone.now() + timedelta(days=10)
        
        results = TournamentDiscoveryService.filter_by_date_range(
            start_date=start_date,
            end_date=end_date,
            date_filter_type='tournament_start'
        )
        
        assert results.count() == 1
        assert results.first().name == 'Early Tournament'
    
    def test_filter_by_registration_dates(self, sample_game, sample_organizer):
        """Test filtering by registration date range."""
        Tournament.objects.create(
            name='Registration Opens Soon',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() + timedelta(days=2),
            registration_end=timezone.now() + timedelta(days=7),
            tournament_start=timezone.now() + timedelta(days=10),
            status=Tournament.PUBLISHED
        )
        
        start_date = timezone.now()
        end_date = timezone.now() + timedelta(days=5)
        
        results = TournamentDiscoveryService.filter_by_date_range(
            start_date=start_date,
            end_date=end_date,
            date_filter_type='registration_start'
        )
        
        assert results.count() == 1
    
    def test_filter_invalid_date_range(self):
        """Test filtering with start_date after end_date raises ValueError."""
        start_date = timezone.now() + timedelta(days=10)
        end_date = timezone.now()
        
        with pytest.raises(ValueError, match="start_date must be before or equal to end_date"):
            TournamentDiscoveryService.filter_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
    
    def test_filter_invalid_date_type(self):
        """Test filtering with invalid date_filter_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date_filter_type"):
            TournamentDiscoveryService.filter_by_date_range(
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=10),
                date_filter_type='invalid_type'
            )


@pytest.mark.django_db
class TestFilterByStatus:
    """Test status filtering functionality."""
    
    def test_filter_by_single_status(self, sample_game, sample_organizer):
        """Test filtering by single status."""
        Tournament.objects.create(
            name='Published Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Live Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE
        )
        
        results = TournamentDiscoveryService.filter_by_status(status=Tournament.LIVE)
        
        assert results.count() == 1
        assert results.first().status == Tournament.LIVE
    
    def test_filter_by_upcoming_status(self, sample_game, sample_organizer):
        """Test filtering by 'upcoming' meta-status."""
        Tournament.objects.create(
            name='Published',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Registration Open',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.REGISTRATION_OPEN
        )
        Tournament.objects.create(
            name='Live',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE
        )
        
        results = TournamentDiscoveryService.filter_by_status(status='upcoming')
        
        assert results.count() == 2
        assert all(t.status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN] for t in results)
    
    def test_filter_by_active_status(self, sample_game, sample_organizer):
        """Test filtering by 'active' meta-status."""
        Tournament.objects.create(
            name='Registration Open',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.REGISTRATION_OPEN
        )
        Tournament.objects.create(
            name='Live',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE
        )
        Tournament.objects.create(
            name='Completed',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=20),
            registration_end=timezone.now() - timedelta(days=15),
            tournament_start=timezone.now() - timedelta(days=13),
            status=Tournament.COMPLETED
        )
        
        results = TournamentDiscoveryService.filter_by_status(status='active')
        
        assert results.count() == 2
        assert all(t.status in [Tournament.REGISTRATION_OPEN, Tournament.LIVE] for t in results)
    
    def test_filter_invalid_status(self):
        """Test filtering with invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            TournamentDiscoveryService.filter_by_status(status='invalid_status')


@pytest.mark.django_db
class TestFilterByPrizePool:
    """Test prize pool filtering functionality."""
    
    def test_filter_by_min_prize(self, sample_game, sample_organizer):
        """Test filtering by minimum prize pool."""
        Tournament.objects.create(
            name='Low Prize',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='High Prize',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('10000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.filter_by_prize_pool(
            min_prize=Decimal('5000.00')
        )
        
        assert results.count() == 1
        assert results.first().name == 'High Prize'
    
    def test_filter_by_max_prize(self, sample_game, sample_organizer):
        """Test filtering by maximum prize pool."""
        Tournament.objects.create(
            name='Low Prize',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('1000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='High Prize',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('10000.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.filter_by_prize_pool(
            max_prize=Decimal('5000.00')
        )
        
        assert results.count() == 1
        assert results.first().name == 'Low Prize'
    
    def test_filter_by_prize_range(self, sample_game, sample_organizer):
        """Test filtering by prize pool range."""
        for i, prize in enumerate([1000, 5000, 10000, 20000]):
            Tournament.objects.create(
                name=f'Tournament {i+1}',
                game=sample_game,
                organizer=sample_organizer,
                format=Tournament.SINGLE_ELIM,
                max_participants=16,
                prize_pool=Decimal(str(prize)),
                registration_start=timezone.now(),
                registration_end=timezone.now() + timedelta(days=5),
                tournament_start=timezone.now() + timedelta(days=7),
                status=Tournament.PUBLISHED
            )
        
        results = TournamentDiscoveryService.filter_by_prize_pool(
            min_prize=Decimal('4000.00'),
            max_prize=Decimal('15000.00')
        )
        
        assert results.count() == 2
    
    def test_filter_negative_prize(self):
        """Test filtering with negative prize raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            TournamentDiscoveryService.filter_by_prize_pool(
                min_prize=Decimal('-100.00')
            )
    
    def test_filter_invalid_prize_range(self):
        """Test filtering with min > max raises ValueError."""
        with pytest.raises(ValueError, match="min_prize must be less than or equal to max_prize"):
            TournamentDiscoveryService.filter_by_prize_pool(
                min_prize=Decimal('10000.00'),
                max_prize=Decimal('1000.00')
            )


@pytest.mark.django_db
class TestFilterByEntryFee:
    """Test entry fee filtering functionality."""
    
    def test_filter_free_only(self, sample_game, sample_organizer):
        """Test filtering for free tournaments only."""
        Tournament.objects.create(
            name='Free Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            has_entry_fee=False,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Paid Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500.00'),
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.filter_by_entry_fee(free_only=True)
        
        assert results.count() == 1
        assert results.first().has_entry_fee is False
    
    def test_filter_by_fee_range(self, sample_game, sample_organizer):
        """Test filtering by entry fee range."""
        for i, fee in enumerate([100, 300, 500, 1000]):
            Tournament.objects.create(
                name=f'Tournament {i+1}',
                game=sample_game,
                organizer=sample_organizer,
                format=Tournament.SINGLE_ELIM,
                max_participants=16,
                has_entry_fee=True,
                entry_fee_amount=Decimal(str(fee)),
                registration_start=timezone.now(),
                registration_end=timezone.now() + timedelta(days=5),
                tournament_start=timezone.now() + timedelta(days=7),
                status=Tournament.PUBLISHED
            )
        
        results = TournamentDiscoveryService.filter_by_entry_fee(
            min_fee=Decimal('200.00'),
            max_fee=Decimal('600.00')
        )
        
        assert results.count() == 2


@pytest.mark.django_db
class TestFilterByFormat:
    """Test format filtering functionality."""
    
    def test_filter_by_format(self, sample_game, sample_organizer):
        """Test filtering tournaments by format."""
        Tournament.objects.create(
            name='Single Elim',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Double Elim',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.DOUBLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.filter_by_format(
            format=Tournament.SINGLE_ELIM
        )
        
        assert results.count() == 1
        assert results.first().format == Tournament.SINGLE_ELIM
    
    def test_filter_invalid_format(self):
        """Test filtering with invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            TournamentDiscoveryService.filter_by_format(format='invalid_format')


@pytest.mark.django_db
class TestConvenienceMethods:
    """Test convenience query methods."""
    
    def test_get_upcoming_tournaments(self, sample_game, sample_organizer):
        """Test getting upcoming tournaments within timeframe."""
        # Tournament starting in 5 days
        Tournament.objects.create(
            name='Soon',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=3),
            tournament_start=timezone.now() + timedelta(days=5),
            status=Tournament.PUBLISHED
        )
        # Tournament starting in 40 days
        Tournament.objects.create(
            name='Later',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() + timedelta(days=35),
            registration_end=timezone.now() + timedelta(days=38),
            tournament_start=timezone.now() + timedelta(days=40),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.get_upcoming_tournaments(days_ahead=30)
        
        assert results.count() == 1
        assert results.first().name == 'Soon'
    
    def test_get_live_tournaments(self, sample_game, sample_organizer):
        """Test getting currently live tournaments."""
        Tournament.objects.create(
            name='Live Now',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now() - timedelta(days=10),
            registration_end=timezone.now() - timedelta(days=5),
            tournament_start=timezone.now() - timedelta(days=3),
            status=Tournament.LIVE
        )
        Tournament.objects.create(
            name='Upcoming',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.get_live_tournaments()
        
        assert results.count() == 1
        assert results.first().status == Tournament.LIVE
    
    def test_get_featured_tournaments(self, sample_game, sample_organizer):
        """Test getting featured tournaments (official + high prize)."""
        # Official tournament
        Tournament.objects.create(
            name='Official Cup',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('5000.00'),
            is_official=True,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        # Community tournament with high prize
        Tournament.objects.create(
            name='Community High Prize',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('10000.00'),
            is_official=False,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        # Low prize community tournament
        Tournament.objects.create(
            name='Small Tournament',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            prize_pool=Decimal('500.00'),
            is_official=False,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        
        results = TournamentDiscoveryService.get_featured_tournaments(limit=2)
        
        assert results.count() == 2
        # Official should come first
        assert results[0].is_official is True


@pytest.mark.django_db
class TestVisibilityAndPermissions:
    """Test visibility rules and permission logic."""
    
    def test_anonymous_user_sees_public_only(self, sample_game, sample_organizer):
        """Test anonymous users only see published tournaments."""
        Tournament.objects.create(
            name='Published',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Draft',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        
        results = TournamentDiscoveryService.search_tournaments(query='', user=None)
        
        assert results.count() == 1
        assert results.first().status == Tournament.PUBLISHED
    
    def test_organizer_sees_own_drafts(self, sample_game, sample_organizer):
        """Test organizers can see their own draft tournaments."""
        other_user = User.objects.create_user(username='other', email='other@test.com')
        
        # Organizer's draft
        Tournament.objects.create(
            name='My Draft',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        # Other user's draft
        Tournament.objects.create(
            name='Other Draft',
            game=sample_game,
            organizer=other_user,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        
        results = TournamentDiscoveryService.search_tournaments(
            query='',
            user=sample_organizer
        )
        
        assert results.count() == 1
        assert results.first().name == 'My Draft'
    
    def test_regular_user_cannot_see_others_drafts(self, sample_organizer):
        """Test that regular users cannot see other users' draft tournaments."""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com'
        )
        
        # Create tournaments
        Tournament.objects.create(
            name='Published',
            game=Game.objects.create(name='TestGame', slug='testgame', is_active=True),
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        Tournament.objects.create(
            name='Draft',
            game=Game.objects.get(slug='testgame'),
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.DRAFT
        )
        
        # other_user should only see published tournaments
        results = TournamentDiscoveryService.search_tournaments(
            query='',
            user=other_user
        )
        
        # Should only see published, not draft from different organizer
        game = Game.objects.get(slug='testgame')
        results_for_game = results.filter(game=game)
        assert results_for_game.count() == 1
        assert results_for_game.first().status == Tournament.PUBLISHED
    
    def test_soft_deleted_tournaments_excluded(self, sample_game, sample_organizer):
        """Test soft-deleted tournaments are excluded from results."""
        tournament = Tournament.objects.create(
            name='Deleted',
            game=sample_game,
            organizer=sample_organizer,
            format=Tournament.SINGLE_ELIM,
            max_participants=16,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timedelta(days=5),
            tournament_start=timezone.now() + timedelta(days=7),
            status=Tournament.PUBLISHED
        )
        tournament.soft_delete(user=sample_organizer)
        
        results = TournamentDiscoveryService.search_tournaments(query='')
        
        assert results.count() == 0


# =====================================================================
# FIXTURES
# =====================================================================

@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        is_active=True
    )


@pytest.fixture
def sample_organizer():
    """Create a sample organizer user for testing."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@test.com',
        password='testpass123'
    )
