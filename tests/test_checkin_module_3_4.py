"""
Test Suite for Check-in System (Module 3.4)

Tests cover:
- Service layer (CheckinService)
- API endpoints (CheckinViewSet)
- Permissions and authorization
- WebSocket event broadcasting
- Edge cases and error handling

Author: DeltaCrown Development Team
Date: November 8, 2025
"""

import pytest
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import timedelta
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.tournaments.models import Tournament, Registration, Game
from apps.tournaments.services.checkin_service import CheckinService
from django.contrib.auth import get_user_model
from apps.organizations.models import Team, TeamMembership

User = get_user_model()


@pytest.mark.django_db
class TestCheckinService:
    """Test CheckinService business logic"""
    
    @pytest.fixture
    def game(self):
        """Create game instance"""
        return Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def organizer(self):
        """Create tournament organizer"""
        return User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def player(self):
        """Create player user"""
        return User.objects.create_user(
            username='player',
            email='player@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def other_user(self):
        """Create unrelated user"""
        return User.objects.create_user(
            username='other',
            email='other@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def tournament(self, game, organizer):
        """Create tournament with check-in window open"""
        return Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            description='Test tournament for check-in',
            game=game,
            organizer=organizer,
            max_participants=16,
            participation_type='solo',
            status='registration_open',
            # Start in 25 minutes (window opens at -30, now is -25)
            tournament_start=timezone.now() + timedelta(minutes=25),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
        )
    
    @pytest.fixture
    def solo_registration(self, tournament, player):
        """Create confirmed solo registration"""
        return Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed',
        )
    
    @pytest.fixture
    def team(self, player):
        """Create team with player as captain"""
        from apps.user_profile.models import UserProfile
        
        team = Team.objects.create(
            name='Test Team',
            tag='TST',
            description='Test team',
        )
        
        # Ensure player has profile
        profile, _ = UserProfile.objects.get_or_create(user=player)
        
        TeamMembership.objects.create(
            team=team,
            profile=profile,
            role='OWNER',
            status='ACTIVE',
        )
        return team
    
    @pytest.fixture
    def team_registration(self, tournament, team):
        """Create confirmed team registration"""
        # Make tournament team-based
        tournament.participation_type = 'team'
        tournament.save()
        
        return Registration.objects.create(
            tournament=tournament,
            team_id=team.id,
            status='confirmed',
        )
    
    # -------------------------------------------------------------------------
    # Test: Single Check-in - Happy Path
    # -------------------------------------------------------------------------
    
    def test_check_in_solo_by_owner(self, solo_registration, player):
        """Test player can check in their own solo registration"""
        result = CheckinService.check_in(
            registration_id=solo_registration.id,
            actor=player
        )
        
        assert result.checked_in is True
        assert result.checked_in_at is not None
        # Note: checked_in_by field not yet in model
        
        # Verify database
        solo_registration.refresh_from_db()
        assert solo_registration.checked_in is True
    
    def test_check_in_team_by_captain(self, team_registration, player):
        """Test team captain can check in team registration"""
        result = CheckinService.check_in(
            registration_id=team_registration.id,
            actor=player
        )
        
        assert result.checked_in is True
        # Note: checked_in_by field not yet in model
        
        team_registration.refresh_from_db()
        assert team_registration.checked_in is True
    
    def test_check_in_by_organizer(self, solo_registration, organizer):
        """Test organizer can check in any registration"""
        result = CheckinService.check_in(
            registration_id=solo_registration.id,
            actor=organizer
        )
        
        assert result.checked_in is True
        # Note: checked_in_by field not yet in model
    
    # -------------------------------------------------------------------------
    # Test: Check-in Validation
    # -------------------------------------------------------------------------
    
    def test_check_in_requires_confirmed_status(self, tournament, player):
        """Test check-in requires confirmed registration"""
        pending_reg = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='pending',
        )
        
        with pytest.raises(ValidationError, match='must be confirmed'):
            CheckinService.check_in(pending_reg.id, player)
    
    def test_check_in_rejected_for_cancelled(self, solo_registration, player):
        """Test cannot check in cancelled registration"""
        solo_registration.status = 'cancelled'
        solo_registration.save()
        
        with pytest.raises(ValidationError, match='cancelled'):
            CheckinService.check_in(solo_registration.id, player)
    
    def test_check_in_window_not_open(self, tournament, solo_registration, player):
        """Test check-in rejected before window opens"""
        # Set start time far in future (window not open)
        tournament.tournament_start = timezone.now() + timedelta(hours=2)
        tournament.save()
        
        with pytest.raises(ValidationError, match='Check-in opens'):
            CheckinService.check_in(solo_registration.id, player)
    
    def test_check_in_rejected_after_start(self, tournament, solo_registration, player):
        """Test check-in rejected after tournament starts"""
        # Set start time in past
        tournament.tournament_start = timezone.now() - timedelta(minutes=5)
        tournament.save()
        
        with pytest.raises(ValidationError, match='already started'):
            CheckinService.check_in(solo_registration.id, player)
    
    def test_check_in_permission_denied(self, solo_registration, other_user):
        """Test other users cannot check in registration"""
        with pytest.raises(PermissionDenied):
            CheckinService.check_in(solo_registration.id, other_user)
    
    # -------------------------------------------------------------------------
    # Test: Idempotent Check-in
    # -------------------------------------------------------------------------
    
    def test_check_in_idempotent(self, solo_registration, player):
        """Test checking in twice is idempotent"""
        # First check-in
        result1 = CheckinService.check_in(solo_registration.id, player)
        first_timestamp = result1.checked_in_at
        
        # Second check-in (should not error)
        result2 = CheckinService.check_in(solo_registration.id, player)
        
        assert result2.checked_in is True
        assert result2.checked_in_at == first_timestamp  # Timestamp unchanged
    
    # -------------------------------------------------------------------------
    # Test: Undo Check-in
    # -------------------------------------------------------------------------
    
    def test_undo_check_in_by_owner_within_window(self, solo_registration, player):
        """Test owner can undo check-in within time window"""
        # Check in first
        CheckinService.check_in(solo_registration.id, player)
        
        # Undo within window
        result = CheckinService.undo_check_in(solo_registration.id, player)
        
        assert result.checked_in is False
        assert result.checked_in_at is None
        # Note: checked_in_by field not yet in model
    
    def test_undo_check_in_owner_outside_window_fails(self, solo_registration, player):
        """Test owner cannot undo after time window expires"""
        # Check in
        CheckinService.check_in(solo_registration.id, player)
        
        # Manually set checked_in_at to past (simulate expired window)
        solo_registration.refresh_from_db()
        solo_registration.checked_in_at = timezone.now() - timedelta(minutes=20)
        solo_registration.save(update_fields=['checked_in_at'])
        
        with pytest.raises(ValidationError, match='only be undone within'):
            CheckinService.undo_check_in(solo_registration.id, player)
    
    def test_undo_check_in_organizer_anytime(self, solo_registration, player, organizer):
        """Test organizer can undo anytime"""
        # Check in
        CheckinService.check_in(solo_registration.id, player)
        
        # Manually expire window
        solo_registration.refresh_from_db()
        solo_registration.checked_in_at = timezone.now() - timedelta(hours=1)
        solo_registration.save(update_fields=['checked_in_at'])
        
        # Organizer can still undo
        result = CheckinService.undo_check_in(
            solo_registration.id,
            organizer,
            reason='Admin override'
        )
        
        assert result.checked_in is False
    
    def test_undo_check_in_not_checked_in_fails(self, solo_registration, player):
        """Test cannot undo registration that is not checked in"""
        with pytest.raises(ValidationError, match='not checked in'):
            CheckinService.undo_check_in(solo_registration.id, player)
    
    # -------------------------------------------------------------------------
    # Test: Bulk Check-in
    # -------------------------------------------------------------------------
    
    def test_bulk_check_in_success(self, tournament, organizer, player):
        """Test organizer can bulk check in multiple registrations"""
        # Create 3 registrations
        reg1 = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        reg2 = Registration.objects.create(
            tournament=tournament,
            user=player2,
            status='confirmed'
        )
        
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        reg3 = Registration.objects.create(
            tournament=tournament,
            user=player3,
            status='confirmed'
        )
        
        # Bulk check in
        results = CheckinService.bulk_check_in(
            registration_ids=[reg1.id, reg2.id, reg3.id],
            actor=organizer
        )
        
        assert len(results['success']) == 3
        assert len(results['errors']) == 0
        assert len(results['skipped']) == 0
        
        # Verify all checked in
        for reg in [reg1, reg2, reg3]:
            reg.refresh_from_db()
            assert reg.checked_in is True
    
    def test_bulk_check_in_mixed_results(self, tournament, organizer, player):
        """Test bulk check-in handles mixed success/skip/error"""
        # Confirmed registration (success)
        reg1 = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        # Already checked in (skip)
        player2 = User.objects.create_user(username='player2', email='p2@test.com')
        reg2 = Registration.objects.create(
            tournament=tournament,
            user=player2,
            status='confirmed',
            checked_in=True,
        )
        
        # Pending registration (error)
        player3 = User.objects.create_user(username='player3', email='p3@test.com')
        reg3 = Registration.objects.create(
            tournament=tournament,
            user=player3,
            status='pending'
        )
        
        results = CheckinService.bulk_check_in(
            registration_ids=[reg1.id, reg2.id, reg3.id],
            actor=organizer
        )
        
        assert len(results['success']) == 1
        assert results['success'][0]['id'] == reg1.id
        
        assert len(results['skipped']) == 1
        assert results['skipped'][0]['id'] == reg2.id
        
        assert len(results['errors']) == 1
        assert results['errors'][0]['id'] == reg3.id
    
    def test_bulk_check_in_permission_denied(self, tournament, player):
        """Test non-organizer cannot bulk check in"""
        reg = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        other = User.objects.create_user(username='other', email='other@test.com')
        
        with pytest.raises(PermissionDenied):
            CheckinService.bulk_check_in([reg.id], actor=other)
    
    def test_bulk_check_in_max_limit(self, tournament, organizer):
        """Test bulk check-in enforces 200 item limit"""
        with pytest.raises(ValidationError, match='Cannot check in more than 200'):
            CheckinService.bulk_check_in(
                registration_ids=list(range(1, 202)),
                actor=organizer
            )


@pytest.mark.django_db
class TestCheckinAPI:
    """Test Check-in REST API endpoints"""
    
    @pytest.fixture
    def client(self):
        """API client"""
        return APIClient()
    
    @pytest.fixture
    def game(self):
        """Create game instance"""
        return Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def organizer(self):
        """Create organizer"""
        return User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def player(self):
        """Create player"""
        return User.objects.create_user(
            username='player',
            email='player@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def tournament(self, game, organizer):
        """Create tournament"""
        return Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament-api',
            description='Test tournament for API',
            game=game,
            organizer=organizer,
            max_participants=16,
            participation_type='solo',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(minutes=25),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
        )
    
    @pytest.fixture
    def registration(self, tournament, player):
        """Create registration"""
        return Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed',
        )
    
    # -------------------------------------------------------------------------
    # Test: Check-in Endpoint
    # -------------------------------------------------------------------------
    
    @patch('apps.tournaments.api.checkin.views.async_to_sync')
    def test_check_in_endpoint_success(
        self, mock_async, client, registration, player
    ):
        """Test POST /api/tournaments/checkin/{id}/check-in/"""
        client.force_authenticate(user=player)
        
        url = f'/api/tournaments/checkin/{registration.id}/check-in/'
        response = client.post(url)
        
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['message'] == 'Successfully checked in'
        assert response.data['registration']['checked_in'] is True
        
        # Verify WebSocket call
        assert mock_async.called
    
    def test_check_in_requires_authentication(self, client, registration):
        """Test check-in requires authentication"""
        url = f'/api/tournaments/checkin/{registration.id}/check-in/'
        response = client.post(url)
        
        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED
    
    def test_check_in_permission_denied(self, client, registration):
        """Test other users cannot check in"""
        other = User.objects.create_user(username='other', email='other@test.com')
        client.force_authenticate(user=other)
        
        url = f'/api/tournaments/checkin/{registration.id}/check-in/'
        response = client.post(url)
        
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
    
    def test_check_in_not_found(self, client, player):
        """Test check-in with invalid ID"""
        client.force_authenticate(user=player)
        
        url = '/api/tournaments/checkin/99999/check-in/'
        response = client.post(url)
        
        assert response.status_code == http_status.HTTP_404_NOT_FOUND
    
    # -------------------------------------------------------------------------
    # Test: Undo Endpoint
    # -------------------------------------------------------------------------
    
    @patch('apps.tournaments.api.checkin.views.async_to_sync')
    def test_undo_check_in_endpoint(
        self, mock_async, client, registration, player
    ):
        """Test POST /api/tournaments/checkin/{id}/undo/"""
        # Check in first
        CheckinService.check_in(registration.id, player)
        
        client.force_authenticate(user=player)
        
        url = f'/api/tournaments/checkin/{registration.id}/undo/'
        response = client.post(url, {'reason': 'Test undo'})
        
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['registration']['checked_in'] is False
        
        # Verify WebSocket call
        assert mock_async.called
    
    # -------------------------------------------------------------------------
    # Test: Bulk Check-in Endpoint
    # -------------------------------------------------------------------------
    
    @patch('apps.tournaments.api.checkin.views.async_to_sync')
    def test_bulk_check_in_endpoint(
        self, mock_async, client, tournament, organizer, player
    ):
        """Test POST /api/tournaments/checkin/bulk/"""
        # Create registrations
        reg1 = Registration.objects.create(
            tournament=tournament, user=player, status='confirmed'
        )
        player2 = User.objects.create_user(username='p2', email='p2@test.com')
        reg2 = Registration.objects.create(
            tournament=tournament, user=player2, status='confirmed'
        )
        
        client.force_authenticate(user=organizer)
        
        url = '/api/tournaments/checkin/bulk/'
        response = client.post(url, {
            'registration_ids': [reg1.id, reg2.id]
        }, format='json')
        
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['summary']['successful'] == 2
        assert len(response.data['success']) == 2
    
    def test_bulk_check_in_validation_error(self, client, organizer):
        """Test bulk check-in with invalid data"""
        client.force_authenticate(user=organizer)
        
        url = '/api/tournaments/checkin/bulk/'
        response = client.post(url, {
            'registration_ids': []  # Empty list
        }, format='json')
        
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    
    # -------------------------------------------------------------------------
    # Test: Status Endpoint
    # -------------------------------------------------------------------------
    
    def test_check_in_status_endpoint(self, client, registration, player):
        """Test GET /api/tournaments/checkin/{id}/status/"""
        # Check in first
        CheckinService.check_in(registration.id, player)
        
        client.force_authenticate(user=player)
        
        url = f'/api/tournaments/checkin/{registration.id}/status/'
        response = client.get(url)
        
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data['checked_in'] is True
        # Note: checked_in_by not yet in model
        assert 'can_undo' in response.data


@pytest.mark.django_db
class TestCheckinWebSocket:
    """Test WebSocket event broadcasting for check-ins"""
    
    @patch('apps.tournaments.api.checkin.views.get_channel_layer')
    @patch('apps.tournaments.api.checkin.views.async_to_sync')
    def test_check_in_broadcasts_websocket_event(
        self, mock_async, mock_get_layer
    ):
        """Test check-in broadcasts WebSocket event"""
        # Setup mocks
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send
        
        # Create game
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )
        
        # Create organizer
        organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='pass123'
        )
        
        # Create tournament and registration
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament-ws',
            description='Test tournament for WebSocket',
            game=game,
            organizer=organizer,
            max_participants=16,
            participation_type='solo',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(minutes=25),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
        )
        
        player = User.objects.create_user(username='player', email='player@test.com')
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        # Perform check-in via API
        from apps.tournaments.api.checkin.views import CheckinViewSet
        
        viewset = CheckinViewSet()
        viewset._broadcast_checkin_event(registration, checked_in=True)
        
        # Verify channel layer was called
        assert mock_get_layer.called
        assert mock_async.called
        
        # Verify group_send wrapper was called
        # async_to_sync(channel_layer.group_send) returns mock_group_send
        # Then mock_group_send(group_name, payload) is called
        assert mock_group_send.called
        call_args, call_kwargs = mock_group_send.call_args
        
        group_name = call_args[0]
        payload = call_args[1]
        
        assert group_name == f'tournament_{tournament.id}'
        assert payload['type'] == 'registration_checked_in'
        assert payload['registration_id'] == registration.id
        assert payload['checked_in'] is True


@pytest.mark.django_db
class TestCheckinAPIEdgeCases:
    """Test API edge cases and error handling for coverage polish"""
    
    @pytest.fixture
    def client(self):
        """API client"""
        return APIClient()
    
    @pytest.fixture
    def game(self):
        """Create game"""
        return Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def organizer(self):
        """Create organizer"""
        return User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='pass123'
        )
    
    @pytest.fixture
    def tournament(self, game, organizer):
        """Create tournament"""
        return Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament-edge',
            description='Test tournament',
            game=game,
            organizer=organizer,
            max_participants=16,
            participation_type='solo',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(minutes=25),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=1),
        )
    
    def test_check_in_validation_error_returns_400(self, client, tournament):
        """Test ValidationError in check-in returns 400"""
        player = User.objects.create_user(username='player', email='player@test.com')
        
        # Create pending (not confirmed) registration
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='pending'  # Not confirmed - will trigger ValidationError
        )
        
        client.force_authenticate(user=player)
        url = f'/api/tournaments/checkin/{registration.id}/check-in/'
        response = client.post(url)
        
        assert response.status_code == 400
        assert 'error' in response.data
        assert 'confirmed' in response.data['error'].lower()
    
    def test_check_in_permission_error_returns_403(self, client, tournament):
        """Test PermissionDenied in check-in returns 403"""
        player = User.objects.create_user(username='player', email='player@test.com')
        other = User.objects.create_user(username='other', email='other@test.com')
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        # Try to check in as non-owner
        client.force_authenticate(user=other)
        url = f'/api/tournaments/checkin/{registration.id}/check-in/'
        response = client.post(url)
        
        assert response.status_code == 403
        assert 'error' in response.data
    
    def test_check_in_not_found_returns_404(self, client, tournament):
        """Test non-existent registration returns 404"""
        player = User.objects.create_user(username='player', email='player@test.com')
        
        client.force_authenticate(user=player)
        url = '/api/tournaments/checkin/99999/check-in/'
        response = client.post(url)
        
        assert response.status_code == 404
    
    def test_undo_validation_error_returns_400(self, client, tournament):
        """Test ValidationError in undo returns 400"""
        player = User.objects.create_user(username='player', email='player@test.com')
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        # Not checked in yet - will trigger ValidationError
        
        client.force_authenticate(user=player)
        url = f'/api/tournaments/checkin/{registration.id}/undo/'
        response = client.post(url, {'reason': 'Test'})
        
        assert response.status_code == 400
        assert 'error' in response.data
        assert 'not checked in' in response.data['error'].lower()
    
    def test_undo_permission_error_returns_403(self, client, tournament):
        """Test PermissionDenied in undo returns 403"""
        player = User.objects.create_user(username='player', email='player@test.com')
        other = User.objects.create_user(username='other', email='other@test.com')
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        # Check in first
        CheckinService.check_in(registration.id, player)
        
        # Try to undo as non-owner
        client.force_authenticate(user=other)
        url = f'/api/tournaments/checkin/{registration.id}/undo/'
        response = client.post(url, {'reason': 'Test'})
        
        assert response.status_code == 403
    
    def test_bulk_validation_error_returns_400(self, client, tournament, organizer):
        """Test ValidationError in bulk returns 400"""
        client.force_authenticate(user=organizer)
        
        # Empty list will trigger ValidationError
        url = '/api/tournaments/checkin/bulk/'
        response = client.post(url, {'registration_ids': []}, format='json')
        
        assert response.status_code == 400
        # Serializer validation error has field-specific errors
        assert 'registration_ids' in response.data
    
    def test_bulk_permission_error_returns_403(self, client, tournament):
        """Test PermissionDenied in bulk returns 403"""
        player = User.objects.create_user(username='player', email='player@test.com')
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        # Try bulk as non-organizer
        client.force_authenticate(user=player)
        url = '/api/tournaments/checkin/bulk/'
        response = client.post(url, {'registration_ids': [registration.id]}, format='json')
        
        assert response.status_code == 403
    
    def test_status_endpoint_not_found_returns_404(self, client):
        """Test status endpoint with non-existent registration returns 404"""
        player = User.objects.create_user(username='player', email='player@test.com')
        
        client.force_authenticate(user=player)
        url = '/api/tournaments/checkin/99999/status/'
        response = client.get(url)
        
        assert response.status_code == 404
    
    @patch('apps.tournaments.api.checkin.views.get_channel_layer')
    def test_websocket_broadcast_handles_missing_channel_layer(
        self, mock_get_layer, tournament
    ):
        """Test WebSocket broadcast gracefully handles missing channel layer"""
        # Simulate missing channel layer
        mock_get_layer.return_value = None
        
        player = User.objects.create_user(username='player', email='player@test.com')
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        from apps.tournaments.api.checkin.views import CheckinViewSet
        
        viewset = CheckinViewSet()
        # Should not raise exception even with no channel layer
        viewset._broadcast_checkin_event(registration, checked_in=True)
        
        assert mock_get_layer.called
    
    @patch('apps.tournaments.api.checkin.views.get_channel_layer')
    @patch('apps.tournaments.api.checkin.views.async_to_sync')
    def test_websocket_broadcast_handles_exception(
        self, mock_async, mock_get_layer, tournament
    ):
        """Test WebSocket broadcast handles exceptions gracefully"""
        # Setup mocks to raise exception
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        mock_group_send = MagicMock(side_effect=Exception("Channel error"))
        mock_async.return_value = mock_group_send
        
        player = User.objects.create_user(username='player', email='player@test.com')
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='confirmed'
        )
        
        from apps.tournaments.api.checkin.views import CheckinViewSet
        
        viewset = CheckinViewSet()
        # Should not propagate exception
        viewset._broadcast_checkin_event(registration, checked_in=True)
        
        # Exception should be caught and logged (not raised)
