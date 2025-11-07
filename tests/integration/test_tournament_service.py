"""
Integration tests for TournamentService.

Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 2: Service Layer)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (Testing standards)

Tests the full create, publish, and cancel workflow for tournaments.

Note: These tests will work once database migrations are fully resolved.
Currently blocked by legacy app references to tournaments.match/registration.
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.tournaments.services import TournamentService
from apps.tournaments.models.tournament import Game, Tournament


@pytest.mark.django_db
class TestTournamentServiceCreate:
    """Test tournament creation through service layer"""
    
    @pytest.fixture
    def game(self):
        """Create a test game"""
        return Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
            is_active=True
        )
    
    @pytest.fixture
    def user(self, django_user_model):
        """Create a test user"""
        return django_user_model.objects.create_user(
            username='test_organizer',
            email='organizer@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def tournament_data(self, game):
        """Valid tournament creation data"""
        now = timezone.now()
        return {
            'name': 'Test Tournament',
            'game_id': game.id,
            'format': 'single_elimination',
            'max_participants': 16,
            'min_participants': 4,
            'registration_start': now + timedelta(days=1),
            'registration_end': now + timedelta(days=7),
            'tournament_start': now + timedelta(days=8),
            'description': 'Test tournament description',
            'prize_pool': Decimal('5000.00'),
            'has_entry_fee': True,
            'entry_fee_amount': Decimal('500.00'),
            'payment_methods': ['bkash', 'nagad'],
        }
    
    def test_create_tournament_success(self, user, tournament_data):
        """Should create tournament with valid data"""
        tournament = TournamentService.create_tournament(
            organizer=user,
            data=tournament_data
        )
        
        assert tournament.id is not None
        assert tournament.name == 'Test Tournament'
        assert tournament.status == Tournament.DRAFT
        assert tournament.organizer == user
        assert tournament.max_participants == 16
        
        # Check version was created
        assert tournament.versions.count() == 1
        version = tournament.versions.first()
        assert version.version_number == 1
        assert version.change_summary == "Tournament created"
    
    def test_create_tournament_missing_required_fields(self, user):
        """Should raise ValidationError when required fields missing"""
        incomplete_data = {
            'name': 'Test Tournament',
            # Missing game_id, format, etc.
        }
        
        with pytest.raises(ValidationError, match="Missing required fields"):
            TournamentService.create_tournament(
                organizer=user,
                data=incomplete_data
            )
    
    def test_create_tournament_invalid_game(self, user, tournament_data):
        """Should raise ValidationError when game doesn't exist"""
        tournament_data['game_id'] = 99999
        
        with pytest.raises(ValidationError, match="Game with ID 99999 not found"):
            TournamentService.create_tournament(
                organizer=user,
                data=tournament_data
            )
    
    def test_create_tournament_invalid_dates(self, user, tournament_data):
        """Should raise ValidationError when dates are invalid"""
        # Make registration end before start
        tournament_data['registration_end'] = tournament_data['registration_start'] - timedelta(days=1)
        
        with pytest.raises(ValidationError, match="Registration start must be before registration end"):
            TournamentService.create_tournament(
                organizer=user,
                data=tournament_data
            )


@pytest.mark.django_db
class TestTournamentServicePublish:
    """Test tournament publishing through service layer"""
    
    @pytest.fixture
    def tournament(self, user, tournament_data):
        """Create a draft tournament"""
        return TournamentService.create_tournament(
            organizer=user,
            data=tournament_data
        )
    
    def test_publish_tournament_success(self, user, tournament):
        """Should publish tournament from DRAFT status"""
        published_tournament = TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=user
        )
        
        assert published_tournament.status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]
        assert published_tournament.published_at is not None
        
        # Check version was created
        assert published_tournament.versions.count() == 2  # Create + Publish
        latest_version = published_tournament.versions.first()
        assert "published" in latest_version.change_summary.lower()
    
    def test_publish_tournament_invalid_status(self, user, tournament):
        """Should raise ValidationError when tournament not in DRAFT"""
        # First publish
        tournament = TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=user
        )
        
        # Try to publish again
        with pytest.raises(ValidationError, match="Cannot publish tournament"):
            TournamentService.publish_tournament(
                tournament_id=tournament.id,
                user=user
            )


@pytest.mark.django_db
class TestTournamentServiceCancel:
    """Test tournament cancellation through service layer"""
    
    @pytest.fixture
    def tournament(self, user, tournament_data):
        """Create and publish a tournament"""
        tournament = TournamentService.create_tournament(
            organizer=user,
            data=tournament_data
        )
        return TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=user
        )
    
    def test_cancel_tournament_success(self, user, tournament):
        """Should cancel tournament and soft delete"""
        cancelled_tournament = TournamentService.cancel_tournament(
            tournament_id=tournament.id,
            user=user,
            reason='Insufficient registrations'
        )
        
        assert cancelled_tournament.status == Tournament.CANCELLED
        assert cancelled_tournament.is_deleted is True
        assert cancelled_tournament.deleted_by == user
        
        # Check version was created
        latest_version = cancelled_tournament.versions.first()
        assert "cancelled" in latest_version.change_summary.lower()
        assert "Insufficient registrations" in latest_version.change_summary
    
    def test_cancel_completed_tournament_fails(self, user, tournament):
        """Should not allow cancelling completed tournaments"""
        # Manually set to completed
        tournament.status = Tournament.COMPLETED
        tournament.save()
        
        with pytest.raises(ValidationError, match="Cannot cancel tournament"):
            TournamentService.cancel_tournament(
                tournament_id=tournament.id,
                user=user
            )


@pytest.mark.django_db
class TestTournamentServiceVersion:
    """Test version management in service layer"""
    
    @pytest.fixture
    def tournament(self, user, tournament_data):
        """Create a tournament"""
        return TournamentService.create_tournament(
            organizer=user,
            data=tournament_data
        )
    
    def test_version_created_on_create(self, tournament):
        """Version should be created when tournament is created"""
        assert tournament.versions.count() == 1
        version = tournament.versions.first()
        assert version.version_number == 1
        assert version.version_data['name'] == tournament.name
    
    def test_version_created_on_publish(self, user, tournament):
        """Version should be created when tournament is published"""
        TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=user
        )
        
        assert tournament.versions.count() == 2
        versions = list(tournament.versions.all())
        assert versions[0].version_number == 2  # Latest first (order by -version_number)
        assert versions[1].version_number == 1
    
    def test_rollback_to_version(self, user, tournament):
        """Should rollback tournament to previous version"""
        # Get original name
        original_name = tournament.name
        
        # Modify tournament directly (simulating a change)
        tournament.name = "Modified Name"
        tournament.save()
        TournamentService._create_version(
            tournament=tournament,
            changed_by=user,
            change_summary="Name changed"
        )
        
        # Rollback to version 1
        rolled_back = TournamentService.rollback_to_version(
            tournament_id=tournament.id,
            version_number=1,
            user=user
        )
        
        assert rolled_back.name == original_name
        
        # Check rollback was recorded
        version_1 = tournament.versions.get(version_number=1)
        assert version_1.rolled_back_at is not None
        assert version_1.rolled_back_by == user
