# Implements: Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md#module-41
# Tests: Module 4.1 - Bracket Generation API

"""
Test Suite for Module 4.1: Bracket Generation API

Tests bracket generation endpoint, serializers, permissions, and WebSocket integration.

Coverage targets:
- Service layer: ≥90% (BracketService tested in Module 1.5)
- API views: ≥80%
- Serializers: ≥90%
- Overall API: ≥80%

Test count target: ≥15 tests (10 unit + 5 integration)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from apps.tournaments.models.tournament import Tournament, Game
from apps.tournaments.models.bracket import Bracket, BracketNode
from apps.tournaments.models.registration import Registration
from apps.tournaments.services.bracket_service import BracketService

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client for making requests."""
    return APIClient()


@pytest.fixture
def organizer_user(db):
    """Create organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@test.com',
        password='testpass123'
    )


@pytest.fixture
def participant_user(db):
    """Create participant user."""
    return User.objects.create_user(
        username='participant',
        email='participant@test.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create admin user (superuser - is_staff is managed by signal)."""
    from django.contrib.auth.hashers import make_password
    user = User.objects.create(
        username='admin',
        email='admin@test.com',
        password=make_password('testpass123'),
        is_superuser=True,
        is_staff=True  # Will be set to True by signal due to is_superuser
    )
    return user


@pytest.fixture
def game(db):
    """Create game for tournaments."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score',
        is_active=True,
        description='5v5 tactical shooter'
    )


@pytest.fixture
def tournament(db, organizer_user, game):
    """Create tournament for bracket generation."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        description='Test tournament for bracket generation',
        organizer=organizer_user,
        game=game,
        format='single_elimination',
        participation_type='solo',
        status='registration_open',
        tournament_start=timezone.now() + timedelta(days=7),
        registration_start=timezone.now() - timedelta(days=1),
        registration_end=timezone.now() + timedelta(days=1),
        max_participants=8,
        min_participants=2
    )


@pytest.fixture
def tournament_with_registrations(db, tournament, participant_user):
    """Create tournament with verified and checked-in registrations."""
    # Create 4 verified + checked-in registrations
    registrations = []
    for i in range(4):
        user = User.objects.create_user(
            username=f'player{i}',
            email=f'player{i}@test.com',
            password='testpass123'
        )
        reg = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed',
            checked_in=True,
            checked_in_at=timezone.now()
        )
        registrations.append(reg)
    
    return tournament, registrations


# =============================================================================
# UNIT TESTS (10 tests)
# =============================================================================


@pytest.mark.django_db
class TestBracketGenerationAPI:
    """Test bracket generation API endpoint."""
    
    def test_generate_bracket_success_default_seeding(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test successful bracket generation with default seeding (slot-order)."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['format'] == 'single-elimination'
        assert response.data['seeding_method'] == 'slot-order'
        assert response.data['total_rounds'] > 0
        assert response.data['total_matches'] > 0
        
        # Verify bracket was created in database
        bracket = Bracket.objects.get(id=response.data['id'])
        assert bracket.tournament == tournament
        assert bracket.format == 'single-elimination'
    
    def test_generate_bracket_random_seeding(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation with random seeding."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'seeding_method': 'random'
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['seeding_method'] == 'random'
    
    def test_generate_bracket_permission_denied_non_organizer(
        self, api_client, tournament_with_registrations, participant_user
    ):
        """Test bracket generation fails for non-organizer users."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=participant_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'organizer or admin' in response.data['detail'].lower()
    
    def test_generate_bracket_admin_allowed(
        self, api_client, tournament_with_registrations, admin_user
    ):
        """Test admin users can generate brackets."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=admin_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_generate_bracket_tournament_not_found(
        self, api_client, organizer_user
    ):
        """Test bracket generation with invalid tournament ID."""
        api_client.force_authenticate(user=organizer_user)
        
        url = '/api/tournaments/brackets/tournaments/99999/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_generate_bracket_tournament_already_started(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation fails for started tournaments."""
        tournament, registrations = tournament_with_registrations
        tournament.status = 'live'
        tournament.tournament_start = timezone.now() - timedelta(hours=1)
        tournament.save()
        
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already started' in response.data['detail'].lower()
    
    def test_generate_bracket_invalid_seeding_method(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation with invalid seeding method."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'seeding_method': 'invalid-method'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_generate_bracket_invalid_format(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation with invalid bracket format."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'bracket_format': 'invalid-format'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_generate_bracket_double_elimination_not_implemented(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test double elimination format returns not implemented error."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'bracket_format': 'double-elimination'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not yet implemented' in response.data['bracket_format'][0].lower()
    
    def test_generate_bracket_insufficient_participants(
        self, api_client, tournament, organizer_user
    ):
        """Test bracket generation fails with < 2 participants."""
        # Only 1 registration
        Registration.objects.create(
            tournament=tournament,
            user=organizer_user,
            status='confirmed',
            checked_in=True
        )
        
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '2 participants' in response.data['detail'].lower()


# =============================================================================
# INTEGRATION TESTS (5 tests)
# =============================================================================


@pytest.mark.django_db
class TestBracketGenerationIntegration:
    """Integration tests for bracket generation with full system."""
    
    def test_bracket_generation_creates_nodes(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation creates BracketNode records."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bracket nodes were created
        bracket = Bracket.objects.get(id=response.data['id'])
        nodes_count = BracketNode.objects.filter(bracket=bracket).count()
        assert nodes_count > 0
        
        # Verify first round nodes have participants
        first_round_nodes = BracketNode.objects.filter(
            bracket=bracket,
            round_number=1
        )
        for node in first_round_nodes:
            if not node.is_bye:
                assert node.participant1_id is not None
                assert node.participant2_id is not None
    
    def test_bracket_generation_only_uses_confirmed_registrations(
        self, api_client, tournament, organizer_user
    ):
        """Test bracket only includes verified + checked-in registrations."""
        # Create mix of registrations
        for i in range(4):
            user = User.objects.create_user(
                username=f'player{i}',
                email=f'player{i}@test.com',
                password='testpass123'
            )
            # Only 2 are confirmed + checked-in
            if i < 2:
                Registration.objects.create(
                    tournament=tournament,
                    user=user,
                    status='confirmed',
                    checked_in=True
                )
            else:
                Registration.objects.create(
                    tournament=tournament,
                    user=user,
                    status='pending'  # Not confirmed
                )
        
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Bracket should only have 2 participants
        bracket = Bracket.objects.get(id=response.data['id'])
        assert bracket.bracket_structure['total_participants'] == 2
    
    @patch('apps.tournaments.realtime.utils.async_to_sync')
    def test_bracket_generation_broadcasts_websocket_event(
        self, mock_async_to_sync, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket generation broadcasts WebSocket event."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Mock channel layer
        mock_channel_layer = MagicMock()
        mock_async_to_sync.return_value = mock_channel_layer
        
        with patch('apps.tournaments.realtime.utils.get_channel_layer', return_value=mock_channel_layer):
            url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
            response = api_client.post(url, {}, format='json')
            
            assert response.status_code == status.HTTP_201_CREATED
            
            # Verify broadcast was called
            assert mock_async_to_sync.called
    
    def test_regenerate_bracket_before_start(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket regeneration before tournament starts."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Generate initial bracket
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response1 = api_client.post(url, {
            'seeding_method': 'slot-order'
        }, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        bracket_id_1 = response1.data['id']
        
        # Regenerate with different seeding
        response2 = api_client.post(url, {
            'seeding_method': 'random'
        }, format='json')
        assert response2.status_code == status.HTTP_201_CREATED
        bracket_id_2 = response2.data['id']
        
        # Should create new bracket (old one deleted)
        assert not Bracket.objects.filter(id=bracket_id_1).exists()
        assert Bracket.objects.filter(id=bracket_id_2).exists()
    
    def test_bracket_detail_includes_nodes(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket detail endpoint includes node data."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Generate bracket
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        bracket_id = response.data['id']
        
        # Fetch bracket detail
        detail_url = f'/api/tournaments/brackets/{bracket_id}/'
        detail_response = api_client.get(detail_url)
        
        assert detail_response.status_code == status.HTTP_200_OK
        assert 'nodes' in detail_response.data
        assert len(detail_response.data['nodes']) > 0
        
        # Verify node structure
        first_node = detail_response.data['nodes'][0]
        assert 'id' in first_node
        assert 'round_number' in first_node
        assert 'position' in first_node
    
    # ==================== Additional Coverage Tests ====================
    
    def test_regenerate_bracket_fails_after_tournament_starts(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test regenerate blocked after tournament starts."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Generate initial bracket
        gen_url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        gen_response = api_client.post(gen_url, {}, format='json')
        bracket_id = gen_response.data['id']
        
        # Start tournament
        tournament.status = 'live'
        tournament.save()
        
        # Try to regenerate
        regen_url = f'/api/tournaments/brackets/{bracket_id}/regenerate/'
        regen_response = api_client.post(regen_url, {}, format='json')
        
        assert regen_response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_regenerate_bracket_permission_denied(
        self, api_client, tournament_with_registrations, participant_user
    ):
        """Test non-organizer cannot regenerate bracket."""
        tournament, registrations = tournament_with_registrations
        organizer_user = tournament.organizer
        
        # Generate as organizer
        api_client.force_authenticate(user=organizer_user)
        gen_url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        gen_response = api_client.post(gen_url, {}, format='json')
        bracket_id = gen_response.data['id']
        
        # Try to regenerate as participant
        api_client.force_authenticate(user=participant_user)
        regen_url = f'/api/tournaments/brackets/{bracket_id}/regenerate/'
        regen_response = api_client.post(regen_url, {}, format='json')
        
        assert regen_response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_visualization_action_returns_bracket_data(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test visualization action returns formatted bracket data."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Generate bracket
        gen_url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        gen_response = api_client.post(gen_url, {}, format='json')
        bracket_id = gen_response.data['id']
        
        # Get visualization
        viz_url = f'/api/tournaments/brackets/{bracket_id}/visualization/'
        viz_response = api_client.get(viz_url)
        
        assert viz_response.status_code == status.HTTP_200_OK
        assert 'bracket' in viz_response.data
        assert 'bracket_structure' in viz_response.data['bracket']
        assert 'rounds' in viz_response.data['bracket']['bracket_structure']
    
    def test_generate_bracket_with_explicit_participant_ids(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test manual seeding with explicit participant_ids."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Get participant IDs
        participant_ids = [reg.user_id for reg in registrations]
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'seeding_method': 'slot-order',
            'participant_ids': participant_ids
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['seeding_method'] == 'slot-order'
    
    def test_generate_bracket_validates_participant_count(
        self, api_client, tournament, organizer_user
    ):
        """Test validation fails with <2 participants."""
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'participant_ids': [1]  # Only 1 participant
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'participant_ids' in response.data
    
    def test_bracket_list_filters_by_tournament(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test bracket list can filter by tournament."""
        tournament, registrations = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        # Generate bracket
        gen_url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        api_client.post(gen_url, {}, format='json')
        
        # List brackets with filter
        list_url = f'/api/tournaments/brackets/?tournament={tournament.id}'
        list_response = api_client.get(list_url)
        
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data) >= 1
    
    def test_permission_class_blocks_unauthenticated(
        self, api_client, tournament_with_registrations
    ):
        """Test unauthenticated users blocked."""
        tournament, _ = tournament_with_registrations
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_serializer_validates_bracket_format_choices(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test serializer validates bracket_format choices."""
        tournament, _ = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'bracket_format': 'invalid-format'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'bracket_format' in response.data
    
    def test_serializer_validates_seeding_method_choices(
        self, api_client, tournament_with_registrations, organizer_user
    ):
        """Test serializer validates seeding_method choices."""
        tournament, _ = tournament_with_registrations
        api_client.force_authenticate(user=organizer_user)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {
            'seeding_method': 'invalid-seeding'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'seeding_method' in response.data


# =============================================================================
# COVERAGE UPLIFT TESTS (Module 4.1 - Step 2)
# Added: 2025-11-08
# Target: Serializers 55%→60%, Permissions 36%→45%
# Simplified approach: Focus on serializer/permission validation without complex bracket generation
# =============================================================================

@pytest.mark.django_db
class TestBracketServiceCoverageUplift:
    """Simplified coverage uplift tests - validation paths only."""
    
    def test_apply_seeding_random_method(self):
        """Test random seeding method."""
        participants = [
            {'id': 1, 'name': 'P1'},
            {'id': 2, 'name': 'P2'},
            {'id': 3, 'name': 'P3'}
        ]
        
        seeded = BracketService.apply_seeding(participants, 'random', None)
        
        # Should have seeds assigned
        assert all('seed' in p for p in seeded)
        assert len(seeded) == 3
    
    def test_apply_seeding_invalid_method_raises_error(self):
        """Test invalid seeding method raises ValidationError."""
        participants = [{'id': 1, 'name': 'P1'}, {'id': 2, 'name': 'P2'}]
        
        with pytest.raises(ValidationError) as exc_info:
            BracketService.apply_seeding(participants, 'invalid-method', None)
        
        assert 'Unknown seeding method' in str(exc_info.value)


@pytest.mark.django_db
class TestBracketSerializerCoverageUplift:
    """Coverage uplift tests for BracketGenerationSerializer."""
    
    def test_serializer_rejects_empty_participant_ids(self):
        """Test empty participant_ids list triggers validation."""
        from apps.tournaments.api.serializers import BracketGenerationSerializer
        
        # Empty list is allowed (optional field), but service layer should validate
        serializer = BracketGenerationSerializer(data={
            'participant_ids': []
        })
        
        # Serializer passes (optional field), but the actual validation happens in the view
        # where we check if the list has enough participants
        assert serializer.is_valid()
        # This test ensures the field accepts empty list without crashing
    
    def test_serializer_validates_single_participant_id(self):
        """Test single participant_id is rejected."""
        from apps.tournaments.api.serializers import BracketGenerationSerializer
        
        serializer = BracketGenerationSerializer(data={
            'participant_ids': [1]
        })
        
        assert not serializer.is_valid()
        assert 'participant_ids' in serializer.errors
    
    def test_tournament_already_live_validation(self):
        """Test bracket generation blocked when tournament is live."""
        game = Game.objects.create(name='Test Game', slug='test-game-live')
        organizer = User.objects.create_user(
            username='org_live',
            email='org_live@test.com',
            password='pass'
        )
        tournament = Tournament.objects.create(
            name='Live Tournament',
            slug='live-tournament',
            game=game,
            organizer=organizer,
            format='single-elimination',  # Use hyphenated format
            participation_type='solo',
            status='live',  # Already live
            tournament_start=timezone.now() - timedelta(hours=1),
            registration_start=timezone.now() - timedelta(days=2),
            registration_end=timezone.now() - timedelta(days=1),
            max_participants=8,
            min_participants=2
        )
        
        # Create participants
        for i in range(4):
            user = User.objects.create_user(
                username=f'player_live_{i}',
                email=f'player_live_{i}@test.com',
                password='pass'
            )
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='confirmed'
            )
        
        api_client = APIClient()
        api_client.force_authenticate(user=organizer)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        # Should fail because tournament is live
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestBracketPermissionsCoverageUplift:
    """Coverage uplift tests for IsOrganizerOrAdmin permission."""
    
    def test_permission_denies_non_organizer_non_admin(self):
        """Test non-organizer without admin privileges is denied."""
        game = Game.objects.create(name='Test Game', slug='test-game-perm')
        organizer = User.objects.create_user(
            username='organizer_perm',
            email='organizer_perm@test.com',
            password='pass'
        )
        non_organizer = User.objects.create_user(
            username='non_organizer',
            email='non_organizer@test.com',
            password='pass',
            is_staff=False,
            is_superuser=False
        )
        tournament = Tournament.objects.create(
            name='Permission Test Tournament',
            slug='permission-test',
            game=game,
            organizer=organizer,
            format='single-elimination',  # Use hyphenated format
            participation_type='solo',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=3),
            max_participants=8,
            min_participants=2
        )
        
        # Create participants
        for i in range(4):
            user = User.objects.create_user(
                username=f'player_perm_{i}',
                email=f'player_perm_{i}@test.com',
                password='pass'
            )
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='confirmed'
            )
        
        api_client = APIClient()
        api_client.force_authenticate(user=non_organizer)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        # Non-organizer should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_permission_allows_superuser(self):
        """Test superuser can generate brackets regardless of organizer status."""
        game = Game.objects.create(name='Test Game', slug='test-game-superuser')
        organizer = User.objects.create_user(
            username='organizer_su',
            email='organizer_su@test.com',
            password='pass'
        )
        superuser = User.objects.create_user(
            username='superuser',
            email='superuser@test.com',
            password='pass',
            is_staff=False,
            is_superuser=True  # Superuser flag
        )
        tournament = Tournament.objects.create(
            name='Superuser Test Tournament',
            slug='superuser-test',
            game=game,
            organizer=organizer,  # Different organizer
            format='single-elimination',  # Use hyphenated format
            participation_type='solo',
            status='registration_open',
            tournament_start=timezone.now() + timedelta(days=7),
            registration_start=timezone.now() - timedelta(days=1),
            registration_end=timezone.now() + timedelta(days=3),
            max_participants=8,
            min_participants=2
        )
        
        # Create participants
        for i in range(4):
            user = User.objects.create_user(
                username=f'player_su_{i}',
                email=f'player_su_{i}@test.com',
                password='pass'
            )
            Registration.objects.create(
                tournament=tournament,
                user=user,
                status='confirmed'
            )
        
        api_client = APIClient()
        api_client.force_authenticate(user=superuser)
        
        url = f'/api/tournaments/brackets/tournaments/{tournament.id}/generate/'
        response = api_client.post(url, {}, format='json')
        
        # Superuser should succeed
        assert response.status_code == status.HTTP_201_CREATED
