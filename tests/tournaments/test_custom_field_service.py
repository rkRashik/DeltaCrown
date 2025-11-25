"""
Tests for CustomFieldService

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (Testing Standards)

Description:
Comprehensive tests for custom field service layer.
Tests cover CRUD operations, field value validation, and permission checks.

Coverage Target: ≥80% for CustomFieldService
Test Count Target: 15+ tests (combined with API tests as per backlog)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tournaments.models.tournament import Tournament, Game, CustomField
from apps.tournaments.services.custom_field_service import CustomFieldService
from apps.tournaments.services.tournament_service import TournamentService

User = get_user_model()


@pytest.fixture
def organizer(db):
    """Create an organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123'
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    user = User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123'
    )
    user.is_staff = True
    user.is_superuser = True  # Bypass group-based is_staff signal
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user."""
    return User.objects.create_user(
        username='regularuser',
        email='user@example.com',
        password='testpass123'
    )


@pytest.fixture
def game(db):
    """Create a game."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='score',
        is_active=True
    )


@pytest.fixture
def draft_tournament(db, game, organizer):
    """Create a DRAFT tournament."""
    now = timezone.now()
    data = {
        'name': 'Test Tournament',
        'description': 'Test tournament for custom fields',
        'game_id': game.id,
        'format': Tournament.SINGLE_ELIM,
        'participation_type': Tournament.TEAM,
        'max_participants': 16,
        'min_participants': 4,
        'registration_start': now + timedelta(days=1),
        'registration_end': now + timedelta(days=7),
        'tournament_start': now + timedelta(days=10),
    }
    return TournamentService.create_tournament(organizer=organizer, data=data)


@pytest.fixture
def published_tournament(db, game, organizer):
    """Create a PUBLISHED tournament."""
    now = timezone.now()
    data = {
        'name': 'Published Tournament',
        'description': 'Published tournament for testing',
        'game_id': game.id,
        'format': Tournament.SINGLE_ELIM,
        'participation_type': Tournament.TEAM,
        'max_participants': 16,
        'min_participants': 4,
        'registration_start': now + timedelta(days=1),
        'registration_end': now + timedelta(days=7),
        'tournament_start': now + timedelta(days=10),
    }
    tournament = TournamentService.create_tournament(organizer=organizer, data=data)
    # Publish the tournament
    TournamentService.publish_tournament(tournament_id=tournament.id, user=organizer)
    tournament.refresh_from_db()
    return tournament


# ============================================================================
# Test: create_field
# ============================================================================

@pytest.mark.django_db
class TestCreateField:
    """Test CustomFieldService.create_field()"""
    
    def test_create_field_success_organizer(self, draft_tournament, organizer):
        """Organizer should be able to create custom field."""
        field_data = {
            'field_name': 'Discord Server',
            'field_type': 'url',
            'is_required': True,
            'help_text': 'Tournament Discord link'
        }
        
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data=field_data
        )
        
        assert field.field_name == 'Discord Server'
        assert field.field_key == 'discord-server'  # Auto-generated
        assert field.field_type == 'url'
        assert field.is_required is True
        assert field.tournament == draft_tournament
    
    def test_create_field_success_staff(self, draft_tournament, staff_user):
        """Staff should be able to create custom field."""
        field_data = {
            'field_name': 'Team Logo',
            'field_type': 'media',
            'is_required': False
        }
        
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=staff_user,
            field_data=field_data
        )
        
        assert field.field_name == 'Team Logo'
        assert field.field_type == 'media'
    
    def test_create_field_permission_denied(self, draft_tournament, regular_user):
        """Regular user should not be able to create custom field."""
        field_data = {
            'field_name': 'Test Field',
            'field_type': 'text'
        }
        
        with pytest.raises(PermissionError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=regular_user,
                field_data=field_data
            )
        
        assert 'organizer or staff' in str(exc_info.value).lower()
    
    def test_create_field_requires_draft_status(self, published_tournament, organizer):
        """Should raise ValidationError for non-DRAFT tournament."""
        field_data = {
            'field_name': 'Test Field',
            'field_type': 'text'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=published_tournament.id,
                user=organizer,
                field_data=field_data
            )
        
        assert 'DRAFT' in str(exc_info.value)
    
    def test_create_field_validates_required_fields(self, draft_tournament, organizer):
        """Should raise ValidationError if field_name or field_type missing."""
        # Missing field_name
        field_data = {'field_type': 'text'}
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=organizer,
                field_data=field_data
            )
        assert 'field_name' in str(exc_info.value)
        
        # Missing field_type
        field_data = {'field_name': 'Test'}
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=organizer,
                field_data=field_data
            )
        assert 'field_type' in str(exc_info.value)
    
    def test_create_field_validates_field_type(self, draft_tournament, organizer):
        """Should raise ValidationError for invalid field_type."""
        field_data = {
            'field_name': 'Test Field',
            'field_type': 'invalid_type'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=organizer,
                field_data=field_data
            )
        
        assert 'Invalid field_type' in str(exc_info.value)
    
    def test_create_field_prevents_duplicate_field_key(self, draft_tournament, organizer):
        """Should raise ValidationError if field_key already exists."""
        field_data = {
            'field_name': 'Discord Server',
            'field_type': 'url'
        }
        
        # Create first field
        CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data=field_data
        )
        
        # Try to create duplicate (same field_name = same field_key)
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=organizer,
                field_data=field_data
            )
        
        assert 'already exists' in str(exc_info.value).lower()
    
    def test_create_field_validates_field_config(self, draft_tournament, organizer):
        """Should validate field_config based on field_type."""
        # Valid dropdown config
        field_data = {
            'field_name': 'Region',
            'field_type': 'dropdown',
            'field_config': {'options': ['NA', 'EU', 'APAC']}
        }
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data=field_data
        )
        assert field.field_config['options'] == ['NA', 'EU', 'APAC']
        
        # Invalid dropdown config (missing options)
        field_data = {
            'field_name': 'Bad Dropdown',
            'field_type': 'dropdown',
            'field_config': {}
        }
        with pytest.raises(ValidationError):
            CustomFieldService.create_field(
                tournament_id=draft_tournament.id,
                user=organizer,
                field_data=field_data
            )


# ============================================================================
# Test: update_field
# ============================================================================

@pytest.mark.django_db
class TestUpdateField:
    """Test CustomFieldService.update_field()"""
    
    def test_update_field_success(self, draft_tournament, organizer):
        """Organizer should be able to update custom field."""
        # Create field
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Discord', 'field_type': 'url', 'is_required': True}
        )
        
        # Update field
        updated = CustomFieldService.update_field(
            field_id=field.id,
            user=organizer,
            update_data={'is_required': False, 'help_text': 'Optional Discord link'}
        )
        
        assert updated.is_required is False
        assert updated.help_text == 'Optional Discord link'
        assert updated.field_name == 'Discord'  # Unchanged
    
    def test_update_field_permission_denied(self, draft_tournament, organizer, regular_user):
        """Regular user should not be able to update custom field."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Test', 'field_type': 'text'}
        )
        
        with pytest.raises(PermissionError):
            CustomFieldService.update_field(
                field_id=field.id,
                user=regular_user,
                update_data={'help_text': 'New help text'}
            )
    
    def test_update_field_requires_draft_status(self, draft_tournament, organizer):
        """Should raise ValidationError for non-DRAFT tournament."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Test', 'field_type': 'text'}
        )
        
        # Change tournament to PUBLISHED
        draft_tournament.status = Tournament.PUBLISHED
        draft_tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.update_field(
                field_id=field.id,
                user=organizer,
                update_data={'help_text': 'New help'}
            )
        
        assert 'DRAFT' in str(exc_info.value)


# ============================================================================
# Test: delete_field
# ============================================================================

@pytest.mark.django_db
class TestDeleteField:
    """Test CustomFieldService.delete_field()"""
    
    def test_delete_field_success(self, draft_tournament, organizer):
        """Organizer should be able to delete custom field."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Test', 'field_type': 'text'}
        )
        
        CustomFieldService.delete_field(field_id=field.id, user=organizer)
        
        # Field should be deleted
        assert not CustomField.objects.filter(id=field.id).exists()
    
    def test_delete_field_permission_denied(self, draft_tournament, organizer, regular_user):
        """Regular user should not be able to delete custom field."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Test', 'field_type': 'text'}
        )
        
        with pytest.raises(PermissionError):
            CustomFieldService.delete_field(field_id=field.id, user=regular_user)
    
    def test_delete_field_requires_draft_status(self, draft_tournament, organizer):
        """Should raise ValidationError for non-DRAFT tournament."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={'field_name': 'Test', 'field_type': 'text'}
        )
        
        draft_tournament.status = Tournament.PUBLISHED
        draft_tournament.save()
        
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.delete_field(field_id=field.id, user=organizer)
        
        assert 'DRAFT' in str(exc_info.value)


# ============================================================================
# Test: validate_field_value
# ============================================================================

@pytest.mark.django_db
class TestValidateFieldValue:
    """Test CustomFieldService.validate_field_value()"""
    
    def test_validate_text_field(self, draft_tournament, organizer):
        """Should validate text field with min/max length and pattern."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Team Name',
                'field_type': 'text',
                'field_config': {'min_length': 3, 'max_length': 20}
            }
        )
        
        # Valid
        result = CustomFieldService.validate_field_value(field, 'Team Alpha')
        assert result == 'Team Alpha'
        
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.validate_field_value(field, 'AB')
        assert 'at least 3' in str(exc_info.value)
        
        # Too long
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 'A' * 25)
    
    def test_validate_number_field(self, draft_tournament, organizer):
        """Should validate number field with min/max value."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Player Count',
                'field_type': 'number',
                'field_config': {'min_value': 1, 'max_value': 10}
            }
        )
        
        # Valid
        result = CustomFieldService.validate_field_value(field, 5)
        assert result == 5.0
        
        # Too small
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 0)
        
        # Too large
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 15)
        
        # Invalid type
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 'not a number')
    
    def test_validate_dropdown_field(self, draft_tournament, organizer):
        """Should validate dropdown field against options."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Region',
                'field_type': 'dropdown',
                'field_config': {'options': ['NA', 'EU', 'APAC']}
            }
        )
        
        # Valid
        result = CustomFieldService.validate_field_value(field, 'NA')
        assert result == 'NA'
        
        # Invalid option
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.validate_field_value(field, 'SA')
        assert 'one of' in str(exc_info.value).lower()
    
    def test_validate_url_field(self, draft_tournament, organizer):
        """Should validate URL field format."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Website',
                'field_type': 'url'
            }
        )
        
        # Valid
        result = CustomFieldService.validate_field_value(field, 'https://example.com')
        assert result == 'https://example.com'
        
        # Invalid URL
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 'not-a-url')
    
    def test_validate_toggle_field(self, draft_tournament, organizer):
        """Should validate toggle field as boolean."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Accept Terms',
                'field_type': 'toggle'
            }
        )
        
        # Valid
        assert CustomFieldService.validate_field_value(field, True) is True
        assert CustomFieldService.validate_field_value(field, False) is False
        assert CustomFieldService.validate_field_value(field, 'true') is True
        assert CustomFieldService.validate_field_value(field, 'false') is False
        
        # Invalid
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, 'maybe')
    
    def test_validate_required_field(self, draft_tournament, organizer):
        """Should raise ValidationError if required field is empty."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Required Field',
                'field_type': 'text',
                'is_required': True
            }
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldService.validate_field_value(field, None)
        assert 'required' in str(exc_info.value).lower()
        
        with pytest.raises(ValidationError):
            CustomFieldService.validate_field_value(field, '')
    
    def test_validate_optional_field_allows_empty(self, draft_tournament, organizer):
        """Should allow None/empty for optional fields."""
        field = CustomFieldService.create_field(
            tournament_id=draft_tournament.id,
            user=organizer,
            field_data={
                'field_name': 'Optional Field',
                'field_type': 'text',
                'is_required': False
            }
        )
        
        result = CustomFieldService.validate_field_value(field, None)
        assert result is None
        
        result = CustomFieldService.validate_field_value(field, '')
        assert result == ''
