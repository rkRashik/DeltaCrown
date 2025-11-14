"""
Tests for Game Config and Custom Field APIs

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md (Module 2.2)
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (Testing Standards)

Description:
API integration tests for game config and custom field endpoints.
Tests cover authentication, permissions, validation, and CRUD operations.

Coverage Target: ≥80% for API views
Test Count Target: 20+ tests
"""

import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournaments.models.tournament import Tournament, Game, CustomField

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    user = User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )
    return user


@pytest.fixture
def organizer(db):
    """Create an organizer user."""
    return User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123'
    )


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
    """Create a game with empty config."""
    return Game.objects.create(
        name='Valorant',
        slug='valorant',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='score',
        is_active=True,
        game_config={}
    )


@pytest.fixture
def game_with_config(db):
    """Create a game with existing config."""
    return Game.objects.create(
        name='CS2',
        slug='cs2',
        default_team_size=5,
        profile_id_field='steam_id',
        default_result_type='score',
        is_active=True,
        game_config={
            "schema_version": "1.0",
            "allowed_formats": ["single_elimination", "double_elimination"],
            "team_size_range": [5, 5],
            "custom_field_schemas": [],
            "match_settings": {"default_best_of": 3}
        }
    )


@pytest.fixture
def draft_tournament(db, game, organizer):
    """Create a DRAFT tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game=game,
        organizer=organizer,
        status=Tournament.DRAFT,
        format=Tournament.SINGLE_ELIMINATION,
        max_teams=16,
        registration_start_date=date(2025, 1, 1),
        registration_end_date=date(2025, 1, 15),
        start_date=date(2025, 1, 20),
        end_date=date(2025, 1, 25)
    )


# ============================================================================
# Test: GameConfig API - Retrieve
# ============================================================================

@pytest.mark.django_db
class TestGameConfigRetrieveAPI:
    """Test GET /api/games/{id}/config/"""
    
    def test_retrieve_config_public_access(self, api_client, game):
        """Should allow public access to game config."""
        url = f'/api/tournaments/games/{game.id}/config/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'schema_version' in response.data
        assert 'allowed_formats' in response.data
    
    def test_retrieve_config_returns_existing_config(self, api_client, game_with_config):
        """Should return existing config from database."""
        url = f'/api/tournaments/games/{game_with_config.id}/config/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['allowed_formats'] == ['single_elimination', 'double_elimination']
        assert response.data['team_size_range'] == [5, 5]
    
    def test_retrieve_config_returns_default_for_empty(self, api_client, game):
        """Should return default schema if game_config is empty."""
        url = f'/api/tournaments/games/{game.id}/config/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['schema_version'] == '1.0'
        assert 'single_elimination' in response.data['allowed_formats']


# ============================================================================
# Test: GameConfig API - Update
# ============================================================================

@pytest.mark.django_db
class TestGameConfigUpdateAPI:
    """Test PATCH /api/games/{id}/config/"""
    
    def test_update_config_staff_success(self, api_client, game, staff_user):
        """Staff should be able to update game config."""
        api_client.force_authenticate(user=staff_user)
        url = f'/api/tournaments/games/{game.id}/config/'
        
        data = {
            "allowed_formats": ["single_elimination"],
            "team_size_range": [5, 5]
        }
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['allowed_formats'] == ['single_elimination']
        assert response.data['team_size_range'] == [5, 5]
    
    def test_update_config_non_staff_denied(self, api_client, game, regular_user):
        """Non-staff should not be able to update game config."""
        api_client.force_authenticate(user=regular_user)
        url = f'/api/tournaments/games/{game.id}/config/'
        
        data = {"allowed_formats": ["single_elimination"]}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_config_unauthenticated_denied(self, api_client, game):
        """Unauthenticated users should not be able to update game config."""
        url = f'/api/tournaments/games/{game.id}/config/'
        
        data = {"allowed_formats": ["single_elimination"]}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_config_partial_update(self, api_client, game_with_config, staff_user):
        """Should deep merge partial updates."""
        api_client.force_authenticate(user=staff_user)
        url = f'/api/tournaments/games/{game_with_config.id}/config/'
        
        data = {"match_settings": {"default_best_of": 5}}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['match_settings']['default_best_of'] == 5
        # Other fields preserved
        assert response.data['allowed_formats'] == ['single_elimination', 'double_elimination']
    
    def test_update_config_validation_errors(self, api_client, game, staff_user):
        """Should return 400 for invalid config."""
        api_client.force_authenticate(user=staff_user)
        url = f'/api/tournaments/games/{game.id}/config/'
        
        # Invalid format
        data = {"allowed_formats": ["invalid_format"]}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data


# ============================================================================
# Test: GameConfig API - Schema
# ============================================================================

@pytest.mark.django_db
class TestGameConfigSchemaAPI:
    """Test GET /api/games/{id}/config-schema/"""
    
    def test_config_schema_public_access(self, api_client, game):
        """Should allow public access to config schema."""
        url = f'/api/tournaments/games/{game.id}/config-schema/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['$schema'] == 'http://json-schema.org/draft-07/schema#'
    
    def test_config_schema_valid_json_schema(self, api_client, game):
        """Should return valid JSON Schema structure."""
        url = f'/api/tournaments/games/{game.id}/config-schema/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'object'
        assert 'properties' in response.data
        assert 'required' in response.data
        assert 'schema_version' in response.data['properties']


# ============================================================================
# Test: CustomField API - Create
# ============================================================================

@pytest.mark.django_db
class TestCustomFieldCreateAPI:
    """Test POST /api/tournaments/{tournament_id}/custom-fields/"""
    
    def test_create_custom_field_organizer_success(self, api_client, draft_tournament, organizer):
        """Organizer should be able to create custom field."""
        api_client.force_authenticate(user=organizer)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        
        data = {
            "field_name": "Discord Server",
            "field_type": "url",
            "is_required": True,
            "help_text": "Tournament Discord link"
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['field_name'] == 'Discord Server'
        assert response.data['field_key'] == 'discord-server'
        assert response.data['field_type'] == 'url'
    
    def test_create_custom_field_staff_success(self, api_client, draft_tournament, staff_user):
        """Staff should be able to create custom field."""
        api_client.force_authenticate(user=staff_user)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        
        data = {
            "field_name": "Team Logo",
            "field_type": "media"
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_create_custom_field_non_organizer_denied(self, api_client, draft_tournament, regular_user):
        """Non-organizer should not be able to create custom field."""
        api_client.force_authenticate(user=regular_user)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        
        data = {
            "field_name": "Test Field",
            "field_type": "text"
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_custom_field_validation_errors(self, api_client, draft_tournament, organizer):
        """Should return 400 for invalid field data."""
        api_client.force_authenticate(user=organizer)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        
        # Invalid field_type
        data = {
            "field_name": "Test",
            "field_type": "invalid_type"
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Test: CustomField API - List
# ============================================================================

@pytest.mark.django_db
class TestCustomFieldListAPI:
    """Test GET /api/tournaments/{tournament_id}/custom-fields/"""
    
    def test_list_custom_fields_public_access(self, api_client, draft_tournament, organizer):
        """Should allow public access to list custom fields."""
        # Create some fields
        CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Field 1',
            field_key='field-1',
            field_type='text',
            order=0
        )
        CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Field 2',
            field_key='field-2',
            field_type='number',
            order=1
        )
        
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['field_name'] == 'Field 1'
    
    def test_list_custom_fields_ordered(self, api_client, draft_tournament):
        """Should return custom fields ordered by order and field_name."""
        CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Z Field',
            field_key='z-field',
            field_type='text',
            order=2
        )
        CustomField.objects.create(
            tournament=draft_tournament,
            field_name='A Field',
            field_key='a-field',
            field_type='text',
            order=0
        )
        
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['field_name'] == 'A Field'
        assert response.data[1]['field_name'] == 'Z Field'


# ============================================================================
# Test: CustomField API - Update
# ============================================================================

@pytest.mark.django_db
class TestCustomFieldUpdateAPI:
    """Test PATCH /api/tournaments/{tournament_id}/custom-fields/{id}/"""
    
    def test_update_custom_field_organizer_success(self, api_client, draft_tournament, organizer):
        """Organizer should be able to update custom field."""
        field = CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Test Field',
            field_key='test-field',
            field_type='text',
            is_required=True
        )
        
        api_client.force_authenticate(user=organizer)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/{field.id}/'
        
        data = {"is_required": False, "help_text": "Optional field"}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_required'] is False
        assert response.data['help_text'] == "Optional field"
    
    def test_update_custom_field_non_organizer_denied(self, api_client, draft_tournament, organizer, regular_user):
        """Non-organizer should not be able to update custom field."""
        field = CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Test Field',
            field_key='test-field',
            field_type='text'
        )
        
        api_client.force_authenticate(user=regular_user)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/{field.id}/'
        
        data = {"help_text": "New help"}
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test: CustomField API - Delete
# ============================================================================

@pytest.mark.django_db
class TestCustomFieldDeleteAPI:
    """Test DELETE /api/tournaments/{tournament_id}/custom-fields/{id}/"""
    
    def test_delete_custom_field_organizer_success(self, api_client, draft_tournament, organizer):
        """Organizer should be able to delete custom field."""
        field = CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Test Field',
            field_key='test-field',
            field_type='text'
        )
        
        api_client.force_authenticate(user=organizer)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/{field.id}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CustomField.objects.filter(id=field.id).exists()
    
    def test_delete_custom_field_non_organizer_denied(self, api_client, draft_tournament, organizer, regular_user):
        """Non-organizer should not be able to delete custom field."""
        field = CustomField.objects.create(
            tournament=draft_tournament,
            field_name='Test Field',
            field_key='test-field',
            field_type='text'
        )
        
        api_client.force_authenticate(user=regular_user)
        url = f'/api/tournaments/tournaments/{draft_tournament.id}/custom-fields/{field.id}/'
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CustomField.objects.filter(id=field.id).exists()
