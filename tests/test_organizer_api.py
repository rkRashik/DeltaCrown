"""
API Tests for Organizer Dashboard (Module 2.5 Step 2)

Tests REST API endpoints for tournament organizer dashboard.

Planning References:
- BACKEND_ONLY_BACKLOG.md lines 250-279 (Module 2.5)
- PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md lines 1366-1418
- 02_TECHNICAL_STANDARDS.md lines 450-600 (Test structure and patterns)

Test Coverage Target: ≥80% (10+ API tests)

Test Categories:
- Permission checks (organizer vs non-organizer vs staff)
- Response schema validation (IDs-only discipline)
- Query parameter filtering and validation
- Pagination and ordering
- Error handling (404, 403, 500)
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models.tournament import Tournament, Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.match import Match
from apps.tournaments.models.bracket import Bracket
from django.contrib.auth import get_user_model

User = get_user_model()


def create_tournament_fixture(**kwargs):
    """Helper to create Tournament instances with all required fields."""
    now = timezone.now()
    defaults = {
        'name': 'Test Tournament',
        'slug': f'test-tournament-{now.timestamp()}',
        'registration_start': now,
        'registration_end': now + timedelta(days=7),
        'tournament_start': now + timedelta(days=10),
        'max_participants': 16,
        'entry_fee_amount': Decimal('0.00'),
        'has_entry_fee': False,
        'participation_type': Tournament.SOLO,
        'status': Tournament.REGISTRATION_OPEN,
        'description': 'Test tournament',
        'prize_pool': Decimal('0.00'),
        'format': Tournament.SINGLE_ELIM,
    }
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


@pytest.mark.django_db
class TestOrganizerStatsAPI:
    """Test GET /api/tournaments/organizer/dashboard/stats/"""
    
    def test_organizer_stats_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        client = APIClient()
        response = client.get('/api/tournaments/organizer/dashboard/stats/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_organizer_stats_authenticated_empty(self):
        """Test stats for organizer with no tournaments"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/tournaments/organizer/dashboard/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['organizer_id'] == user.id
        assert response.data['total_tournaments'] == 0
        assert response.data['total_participants'] == 0
    
    def test_organizer_stats_with_tournaments(self):
        """Test stats calculation with multiple tournaments"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        # Create 3 tournaments
        for i in range(3):
            create_tournament_fixture(
                name=f'Tournament {i}',
                slug=f'tournament-{i}',
                organizer=user,
                game=game
            )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/tournaments/organizer/dashboard/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['organizer_id'] == user.id
        assert response.data['total_tournaments'] == 3
    
    def test_organizer_stats_ids_only_discipline(self):
        """Test that response contains only IDs, no nested objects"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/tournaments/organizer/dashboard/stats/')
        
        assert response.status_code == status.HTTP_200_OK
        # Check IDs-only discipline - organizer_id should be integer
        assert isinstance(response.data['organizer_id'], int)
        # Should not contain nested objects like 'organizer': {...}
        assert 'organizer' not in response.data or isinstance(response.data.get('organizer'), int)


@pytest.mark.django_db
class TestTournamentHealthAPI:
    """Test GET /api/tournaments/organizer/tournaments/{id}/health/"""
    
    def test_tournament_health_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        client = APIClient()
        response = client.get('/api/tournaments/organizer/tournaments/1/health/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_tournament_health_not_found(self):
        """Test 404 for non-existent tournament"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/tournaments/organizer/tournaments/99999/health/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_tournament_health_permission_denied(self):
        """Test 403 for non-organizer user"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        other_user = User.objects.create_user(username='other', email='other@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game
        )
        
        client = APIClient()
        client.force_authenticate(user=other_user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/health/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
    
    def test_tournament_health_organizer_access(self):
        """Test organizer can access their tournament health"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['tournament_id'] == tournament.id
        assert 'payments' in response.data
        assert 'disputes' in response.data
        assert 'completion_rate' in response.data
        assert 'registration_progress' in response.data
    
    def test_tournament_health_staff_access(self):
        """Test staff can access any tournament health"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        # Create staff user properly
        staff_user = User.objects.create(
            username='staff',
            email='staff@test.com'
        )
        staff_user.set_password('testpass123')
        staff_user.save()
        # Set is_staff after save
        User.objects.filter(id=staff_user.id).update(is_staff=True)
        staff_user.refresh_from_db()
        
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game
        )
        
        client = APIClient()
        client.force_authenticate(user=staff_user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['tournament_id'] == tournament.id


@pytest.mark.django_db
class TestParticipantBreakdownAPI:
    """Test GET /api/tournaments/organizer/tournaments/{id}/participants/"""
    
    def test_participant_breakdown_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        client = APIClient()
        response = client.get('/api/tournaments/organizer/tournaments/1/participants/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_participant_breakdown_not_found(self):
        """Test 404 for non-existent tournament"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/tournaments/organizer/tournaments/99999/participants/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_participant_breakdown_permission_denied(self):
        """Test 403 for non-organizer user"""
        organizer = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        other_user = User.objects.create_user(username='other', email='other@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=organizer,
            game=game
        )
        
        client = APIClient()
        client.force_authenticate(user=other_user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
    
    def test_participant_breakdown_basic(self):
        """Test basic participant breakdown response"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game
        )
        
        # Create 2 participants
        player1 = User.objects.create_user(username='player1', email='p1@test.com', password='pass')
        player2 = User.objects.create_user(username='player2', email='p2@test.com', password='pass')
        
        Registration.objects.create(
            tournament=tournament,
            user=player1,
            status=Registration.CONFIRMED
        )
        Registration.objects.create(
            tournament=tournament,
            user=player2,
            status=Registration.CONFIRMED
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert len(response.data['results']) == 2
    
    def test_participant_breakdown_pagination(self):
        """Test pagination query parameters"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            max_participants=32
        )
        
        # Create 15 participants
        for i in range(15):
            player = User.objects.create_user(
                username=f'player{i}',
                email=f'p{i}@test.com',
                password='pass'
            )
            Registration.objects.create(
                tournament=tournament,
                user=player,
                status=Registration.CONFIRMED
            )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Test page size
        response = client.get(
            f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/?page_size=5'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 15
        assert len(response.data['results']) == 5
    
    def test_participant_breakdown_ordering(self):
        """Test ordering query parameter"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Test ordering parameter
        response = client.get(
            f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/?ordering=-registration_date'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_participant_breakdown_filtering(self):
        """Test filtering query parameters"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500')
        )
        
        # Create participants with different payment statuses
        player1 = User.objects.create_user(username='player1', email='p1@test.com', password='pass')
        player2 = User.objects.create_user(username='player2', email='p2@test.com', password='pass')
        
        reg1 = Registration.objects.create(tournament=tournament, user=player1)
        reg2 = Registration.objects.create(tournament=tournament, user=player2)
        
        # Add verified payment for player1
        Payment.objects.create(
            registration=reg1,
            amount=Decimal('500'),
            payment_method='bkash',
            transaction_id='TXN001',
            status=Payment.VERIFIED,
            verified_by=user,
            verified_at=timezone.now()
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Test payment status filter
        response = client.get(
            f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/?payment_status={Payment.VERIFIED}'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_participant_breakdown_ids_only(self):
        """Test IDs-only discipline in response"""
        user = User.objects.create_user(username='organizer1', email='org1@test.com', password='pass')
        game = Game.objects.create(name='VALORANT', slug='valorant', profile_id_field='riot_id')
        
        tournament = create_tournament_fixture(
            name='Tournament 1',
            slug='tournament-1',
            organizer=user,
            game=game
        )
        
        player = User.objects.create_user(username='player1', email='p1@test.com', password='pass')
        Registration.objects.create(
            tournament=tournament,
            user=player,
            status=Registration.CONFIRMED
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get(f'/api/tournaments/organizer/tournaments/{tournament.id}/participants/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
        
        # Check IDs-only discipline
        participant = response.data['results'][0]
        assert 'participant_id' in participant
        assert isinstance(participant['participant_id'], int)
        assert 'registration_id' in participant
        assert isinstance(participant['registration_id'], int)
        # Should not contain nested user/team objects
        assert 'user' not in participant or isinstance(participant.get('user'), int)
        assert 'team' not in participant or isinstance(participant.get('team'), int)
