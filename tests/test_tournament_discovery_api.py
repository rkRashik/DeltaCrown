"""
Tests for Tournament Discovery API endpoints.

Module: 2.4 - Tournament Discovery & Filtering (Backend Only)

Test Coverage:
- Query parameter validation (game, status, prizes, fees, dates, ordering)
- Pagination and page_size validation
- Full-text search functionality
- Combined filters
- Visibility and permissions
- Convenience endpoints (upcoming, live, featured, by-game)
- Error handling for invalid parameters
- Edge cases (empty results, invalid IDs, date formats)

Requirements from BACKEND_ONLY_BACKLOG.md (Lines 214-241):
- Tests must cover all query parameters
- Pagination must work correctly
- Visibility rules must be enforced
- Error responses must be consistent

Target: 15+ tests, ≥80% coverage
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models.tournament import Tournament, Game

User = get_user_model()


@pytest.mark.django_db
class TestTournamentDiscoveryEndpoint:
    """Test the main /api/tournaments/tournament-discovery/ endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create games
        self.game1 = Game.objects.create(
            name="Valorant",
            slug="valorant",
            is_active=True
        )
        self.game2 = Game.objects.create(
            name="eFootball",
            slug="efootball",
            is_active=True
        )
        
        # Create users
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True
        )
        
        # Create tournaments with various attributes
        now = timezone.now()
        
        # Published tournament - upcoming
        self.t1 = Tournament.objects.create(
            name="Valorant Champions Cup",
            slug="valorant-champions-cup",
            game=self.game1,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            prize_pool=Decimal('10000.00'),
            entry_fee_amount=Decimal('500.00'),
            has_entry_fee=True,
            tournament_start=now + timedelta(days=10),
            registration_start=now - timedelta(days=5),
            registration_end=now + timedelta(days=9),
            is_official=True
        )
        
        # Registration open tournament - free entry
        self.t2 = Tournament.objects.create(
            name="eFootball Community Cup",
            slug="efootball-community-cup",
            game=self.game2,
            organizer=self.organizer,
            status='registration_open',
            format='double_elimination',
            max_participants=32,
            prize_pool=Decimal('5000.00'),
            entry_fee_amount=Decimal('0.00'),
            has_entry_fee=False,
            tournament_start=now + timedelta(days=7),
            registration_start=now - timedelta(days=2),
            registration_end=now + timedelta(days=6),
            is_official=False
        )
        
        # Live tournament
        self.t3 = Tournament.objects.create(
            name="Valorant Spring Showdown",
            slug="valorant-spring-showdown",
            game=self.game1,
            organizer=self.organizer,
            status='live',
            format='round_robin',
            max_participants=8,
            prize_pool=Decimal('2500.00'),
            entry_fee_amount=Decimal('250.00'),
            has_entry_fee=True,
            tournament_start=now - timedelta(hours=2),
            tournament_end=now + timedelta(hours=6),
            registration_start=now - timedelta(days=14),
            registration_end=now - timedelta(days=1),
            is_official=True
        )
        
        # Completed tournament
        self.t4 = Tournament.objects.create(
            name="eFootball Legacy Cup",
            slug="efootball-legacy-cup",
            game=self.game2,
            organizer=self.organizer,
            status='completed',
            format='single_elimination',
            max_participants=16,
            prize_pool=Decimal('15000.00'),
            entry_fee_amount=Decimal('1000.00'),
            has_entry_fee=True,
            tournament_start=now - timedelta(days=30),
            tournament_end=now - timedelta(days=28),
            registration_start=now - timedelta(days=40),
            registration_end=now - timedelta(days=31),
            is_official=True
        )
        
        # Draft tournament (hidden from regular users)
        self.t5 = Tournament.objects.create(
            name="Valorant Draft Tournament",
            slug="valorant-draft-tournament",
            game=self.game1,
            organizer=self.organizer,
            status='draft',
            format='single_elimination',
            max_participants=16,
            prize_pool=Decimal('1000.00'),
            entry_fee_amount=Decimal('0.00'),
            has_entry_fee=False,
            tournament_start=now + timedelta(days=20),
            registration_start=now + timedelta(days=15),
            registration_end=now + timedelta(days=19),
            is_official=False
        )
    
    def test_discover_without_filters(self):
        """Test discover endpoint returns published tournaments without filters."""
        response = self.client.get('/api/tournaments/tournament-discovery/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check pagination structure
        assert 'count' in data
        assert 'next' in data
        assert 'previous' in data
        assert 'results' in data
        
        # Should return 4 published tournaments (excludes draft)
        assert data['count'] == 4
        assert len(data['results']) == 4
        
        # Verify IDs-only discipline (no nested objects)
        tournament = data['results'][0]
        assert 'id' in tournament
        assert 'game_id' in tournament
        assert 'organizer_id' in tournament
        assert isinstance(tournament['game_id'], int)
        assert isinstance(tournament['organizer_id'], int)
    
    def test_discover_filter_by_game(self):
        """Test filtering tournaments by game."""
        # Filter by Valorant
        response = self.client.get(f'/api/tournaments/tournament-discovery/?game={self.game1.id}')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 Valorant tournaments (t1, t3)
        assert data['count'] == 2
        for tournament in data['results']:
            assert tournament['game_id'] == self.game1.id
    
    def test_discover_filter_by_status(self):
        """Test filtering tournaments by status."""
        response = self.client.get('/api/tournaments/tournament-discovery/?status=live')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 live tournament (t3)
        assert data['count'] == 1
        assert data['results'][0]['status'] == 'live'
    
    def test_discover_filter_by_format(self):
        """Test filtering tournaments by format."""
        response = self.client.get('/api/tournaments/tournament-discovery/?format=single_elimination')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 single elimination tournaments (t1, t4)
        assert data['count'] == 2
        for tournament in data['results']:
            assert tournament['format'] == 'single_elimination'
    
    def test_discover_filter_by_prize_range(self):
        """Test filtering tournaments by prize pool range."""
        # Tournaments with prize pool between 2000 and 6000
        response = self.client.get('/api/tournaments/tournament-discovery/?min_prize=2000&max_prize=6000')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 tournaments (t2: 5000, t3: 2500)
        assert data['count'] == 2
        for tournament in data['results']:
            prize = Decimal(tournament['prize_pool'])
            assert 2000 <= prize <= 6000
    
    def test_discover_filter_by_entry_fee_range(self):
        """Test filtering tournaments by entry fee range."""
        # Tournaments with entry fee between 200 and 600
        response = self.client.get('/api/tournaments/tournament-discovery/?min_fee=200&max_fee=600')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 tournaments (t1: 500, t3: 250)
        assert data['count'] == 2
        for tournament in data['results']:
            fee = Decimal(tournament['entry_fee_amount'])
            assert 200 <= fee <= 600
    
    def test_discover_filter_free_only(self):
        """Test filtering for free tournaments only."""
        response = self.client.get('/api/tournaments/tournament-discovery/?free_only=true')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 free tournament (t2)
        assert data['count'] == 1
        assert data['results'][0]['has_entry_fee'] is False
        assert Decimal(data['results'][0]['entry_fee_amount']) == Decimal('0.00')
    
    def test_discover_filter_by_official(self):
        """Test filtering for official tournaments."""
        response = self.client.get('/api/tournaments/tournament-discovery/?is_official=true')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 3 official tournaments (t1, t3, t4)
        assert data['count'] == 3
        for tournament in data['results']:
            assert tournament['is_official'] is True
    
    def test_discover_filter_by_date_range(self):
        """Test filtering tournaments by start date range."""
        now = timezone.now()
        start_after = (now + timedelta(days=5)).isoformat()
        start_before = (now + timedelta(days=15)).isoformat()
        
        response = self.client.get(
            f'/api/tournaments/tournament-discovery/?start_after={start_after}&start_before={start_before}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 tournaments (t1: +10 days, t2: +7 days)
        assert data['count'] == 2
    
    def test_discover_full_text_search(self):
        """Test full-text search on name, description, game."""
        response = self.client.get('/api/tournaments/tournament-discovery/?search=valorant')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 Valorant tournaments (t1, t3)
        assert data['count'] == 2
        for tournament in data['results']:
            # Either tournament name or game name contains "valorant"
            assert 'valorant' in tournament['name'].lower() or \
                   tournament['game_id'] == self.game1.id
    
    def test_discover_ordering_by_prize_pool(self):
        """Test ordering tournaments by prize pool descending."""
        response = self.client.get('/api/tournaments/tournament-discovery/?ordering=-prize_pool')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check descending order: t4 (15000) > t1 (10000) > t2 (5000) > t3 (2500)
        assert data['count'] == 4
        prizes = [Decimal(t['prize_pool']) for t in data['results']]
        assert prizes == sorted(prizes, reverse=True)
    
    def test_discover_ordering_by_start_date(self):
        """Test ordering tournaments by start date ascending."""
        response = self.client.get('/api/tournaments/tournament-discovery/?ordering=tournament_start')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check ascending order (earliest first)
        assert data['count'] == 4
        dates = [datetime.fromisoformat(t['tournament_start'].replace('Z', '+00:00')) 
                 for t in data['results']]
        assert dates == sorted(dates)
    
    def test_discover_combined_filters(self):
        """Test combining multiple filters."""
        response = self.client.get(
            f'/api/tournaments/tournament-discovery/?game={self.game1.id}&status=published&ordering=-prize_pool'
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 tournament (t1: Valorant + published)
        assert data['count'] == 1
        assert data['results'][0]['game_id'] == self.game1.id
        assert data['results'][0]['status'] == 'published'
    
    def test_discover_pagination(self):
        """Test pagination with custom page size."""
        response = self.client.get('/api/tournaments/tournament-discovery/?page_size=2&page=1')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 tournaments on page 1
        assert data['count'] == 4
        assert len(data['results']) == 2
        assert data['next'] is not None  # There should be a next page
    
    def test_discover_invalid_game_id(self):
        """Test error handling for invalid game ID."""
        response = self.client.get('/api/tournaments/tournament-discovery/?game=invalid')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
        assert 'game ID' in data['error'].lower()
    
    def test_discover_invalid_prize_value(self):
        """Test error handling for invalid prize value."""
        response = self.client.get('/api/tournaments/tournament-discovery/?min_prize=not_a_number')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
        assert 'min_prize' in data['error'].lower()
    
    def test_discover_invalid_date_format(self):
        """Test error handling for invalid date format."""
        response = self.client.get('/api/tournaments/tournament-discovery/?start_after=invalid_date')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
        assert 'start_after' in data['error'].lower()
    
    def test_discover_invalid_ordering_field(self):
        """Test error handling for invalid ordering field."""
        response = self.client.get('/api/tournaments/tournament-discovery/?ordering=invalid_field')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
    
    def test_discover_visibility_draft_tournaments(self):
        """Test that draft tournaments are hidden from regular users."""
        # Anonymous user
        response = self.client.get('/api/tournaments/tournament-discovery/')
        data = response.json()
        assert data['count'] == 4  # Excludes t5 (draft)
        
        # Regular authenticated user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/tournaments/tournament-discovery/')
        data = response.json()
        assert data['count'] == 4  # Still excludes t5
        
        # Organizer sees own draft
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get('/api/tournaments/tournament-discovery/')
        data = response.json()
        assert data['count'] == 5  # Includes t5 (organizer's draft)


@pytest.mark.django_db
class TestUpcomingEndpoint:
    """Test the /api/tournaments/tournament-discovery/upcoming/ convenience endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.game = Game.objects.create(
            name="Valorant",
            slug="valorant",
            is_active=True
        )
        
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        
        now = timezone.now()
        
        # Upcoming in 5 days
        self.t1 = Tournament.objects.create(
            name="Tournament 1",
            slug="tournament-1",
            game=self.game,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=5),
            registration_start=now,
            registration_end=now + timedelta(days=4)
        )
        
        # Upcoming in 15 days
        self.t2 = Tournament.objects.create(
            name="Tournament 2",
            slug="tournament-2",
            game=self.game,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=15),
            registration_start=now + timedelta(days=5),
            registration_end=now + timedelta(days=14)
        )
        
        # Upcoming in 40 days (outside default 30 day window)
        self.t3 = Tournament.objects.create(
            name="Tournament 3",
            slug="tournament-3",
            game=self.game,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=40),
            registration_start=now + timedelta(days=30),
            registration_end=now + timedelta(days=39)
        )
    
    def test_upcoming_default_30_days(self):
        """Test upcoming endpoint returns tournaments within 30 days."""
        response = self.client.get('/api/tournaments/tournament-discovery/upcoming/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 tournaments (t1, t2) - t3 is 40 days away
        assert data['count'] == 2
    
    def test_upcoming_custom_days(self):
        """Test upcoming endpoint with custom days parameter."""
        response = self.client.get('/api/tournaments/tournament-discovery/upcoming/?days=7')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 tournament (t1 only, 5 days away)
        assert data['count'] == 1
    
    def test_upcoming_invalid_days(self):
        """Test error handling for invalid days parameter."""
        response = self.client.get('/api/tournaments/tournament-discovery/upcoming/?days=500')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
        assert 'days' in data['error'].lower()


@pytest.mark.django_db
class TestLiveEndpoint:
    """Test the /api/tournaments/tournament-discovery/live/ convenience endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.game = Game.objects.create(
            name="Valorant",
            slug="valorant",
            is_active=True
        )
        
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        
        now = timezone.now()
        
        # Live tournament
        self.t_live = Tournament.objects.create(
            name="Live Tournament",
            slug="live-tournament",
            game=self.game,
            organizer=self.organizer,
            status='live',
            format='single_elimination',
            max_participants=16,
            tournament_start=now - timedelta(hours=2),
            tournament_end=now + timedelta(hours=6),
            registration_start=now - timedelta(days=10),
            registration_end=now - timedelta(days=1)
        )
        
        # Upcoming tournament
        self.t_upcoming = Tournament.objects.create(
            name="Upcoming Tournament",
            slug="upcoming-tournament",
            game=self.game,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=5),
            registration_start=now,
            registration_end=now + timedelta(days=4)
        )
    
    def test_live_returns_only_live_tournaments(self):
        """Test live endpoint returns only live tournaments."""
        response = self.client.get('/api/tournaments/tournament-discovery/live/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 live tournament
        assert data['count'] == 1
        assert data['results'][0]['status'] == 'live'


@pytest.mark.django_db
class TestFeaturedEndpoint:
    """Test the /api/tournaments/tournament-discovery/featured/ convenience endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.game = Game.objects.create(
            name="Valorant",
            slug="valorant",
            is_active=True
        )
        
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        
        now = timezone.now()
        
        # Create 10 tournaments (featured should limit to 6 by default)
        for i in range(10):
            Tournament.objects.create(
                name=f"Tournament {i}",
                slug=f"tournament-{i}",
                game=self.game,
                organizer=self.organizer,
                status='published',
                format='single_elimination',
                max_participants=16,
                is_official=True,
                prize_pool=Decimal(str((10 - i) * 1000)),  # Descending prize pool
                tournament_start=now + timedelta(days=i+5),
                registration_start=now,
                registration_end=now + timedelta(days=i+4)
            )
    
    def test_featured_default_limit(self):
        """Test featured endpoint returns 6 tournaments by default."""
        response = self.client.get('/api/tournaments/tournament-discovery/featured/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 6 tournaments (no pagination, direct list)
        assert len(data) == 6
        assert isinstance(data, list)  # Not paginated
    
    def test_featured_custom_limit(self):
        """Test featured endpoint with custom limit."""
        response = self.client.get('/api/tournaments/tournament-discovery/featured/?limit=3')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 3 tournaments
        assert len(data) == 3
    
    def test_featured_invalid_limit(self):
        """Test error handling for invalid limit."""
        response = self.client.get('/api/tournaments/tournament-discovery/featured/?limit=50')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data
        assert 'limit' in data['error'].lower()


@pytest.mark.django_db
class TestByGameEndpoint:
    """Test the /api/tournaments/tournament-discovery/by-game/{game_id}/ endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.game1 = Game.objects.create(
            name="Valorant",
            slug="valorant",
            is_active=True
        )
        self.game2 = Game.objects.create(
            name="eFootball",
            slug="efootball",
            is_active=True
        )
        
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@example.com",
            password="testpass123"
        )
        
        now = timezone.now()
        
        # Valorant tournament
        self.t1 = Tournament.objects.create(
            name="Valorant Tournament",
            slug="valorant-tournament",
            game=self.game1,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=5),
            registration_start=now,
            registration_end=now + timedelta(days=4)
        )
        
        # eFootball tournament
        self.t2 = Tournament.objects.create(
            name="eFootball Tournament",
            slug="efootball-tournament",
            game=self.game2,
            organizer=self.organizer,
            status='published',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=7),
            registration_start=now,
            registration_end=now + timedelta(days=6)
        )
        
        # Valorant draft tournament
        self.t3 = Tournament.objects.create(
            name="Valorant Draft",
            slug="valorant-draft",
            game=self.game1,
            organizer=self.organizer,
            status='draft',
            format='single_elimination',
            max_participants=16,
            tournament_start=now + timedelta(days=10),
            registration_start=now + timedelta(days=5),
            registration_end=now + timedelta(days=9)
        )
    
    def test_by_game_returns_game_tournaments(self):
        """Test by-game endpoint returns tournaments for specific game."""
        response = self.client.get(f'/api/tournaments/tournament-discovery/by-game/{self.game1.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 1 Valorant tournament (excludes draft)
        assert data['count'] == 1
        assert data['results'][0]['game_id'] == self.game1.id
    
    def test_by_game_organizer_sees_draft(self):
        """Test organizer sees own draft tournaments in by-game."""
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(f'/api/tournaments/tournament-discovery/by-game/{self.game1.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return 2 Valorant tournaments (includes draft)
        assert data['count'] == 2
    
    def test_by_game_invalid_game_id(self):
        """Test error handling for invalid game ID."""
        response = self.client.get('/api/tournaments/tournament-discovery/by-game/9999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert 'error' in data
        assert 'Game' in data['error']
