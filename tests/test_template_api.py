"""
Tournament Template API Integration Tests

Tests REST API endpoints for tournament template management:
- List templates with filters
- Create template (authentication required)
- Retrieve template (visibility checks)
- Update template (owner/staff only)
- Delete template (soft delete)
- Apply template (merge configuration)

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
Target: ≥10 integration tests, ≥80% API coverage
"""

import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.tournaments.models import TournamentTemplate


@pytest.mark.django_db
class TestTemplateListAPI:
    """Tests for GET /api/tournament-templates/"""
    
    def test_list_templates_unauthenticated(self, client, template_global):
        """Unauthenticated users can list GLOBAL templates."""
        url = reverse('tournaments_api:tournament-template-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == "Global Template"
    
    def test_list_templates_authenticated_sees_own_private(self, client, user, template_private, template_global):
        """Authenticated users see GLOBAL + own PRIVATE templates."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        names = {t['name'] for t in response.data['results']}
        assert names == {"Private Template", "Global Template"}
    
    def test_list_templates_filter_by_game(self, client, user, template_with_config, game_valorant):
        """Filter templates by game."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-list')
        response = client.get(url, {'game': game_valorant.id})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['game'] == game_valorant.id
        assert response.data['results'][0]['game_name'] == 'Valorant'
    
    def test_list_templates_filter_by_visibility(self, client, template_private, template_global):
        """Filter templates by visibility."""
        url = reverse('tournaments_api:tournament-template-list')
        response = client.get(url, {'visibility': TournamentTemplate.GLOBAL})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['visibility'] == TournamentTemplate.GLOBAL


@pytest.mark.django_db
class TestTemplateCreateAPI:
    """Tests for POST /api/tournament-templates/"""
    
    def test_create_template_unauthenticated_denied(self, client, game_valorant):
        """Unauthenticated users cannot create templates."""
        url = reverse('tournaments_api:tournament-template-list')
        data = {
            'name': 'Test Template',
            'game_id': game_valorant.id,
            'template_config': {
                'format': 'single_elimination',
                'max_participants': 16
            },
            'visibility': TournamentTemplate.PRIVATE
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_private_template_success(self, client, user, game_valorant):
        """Authenticated users can create PRIVATE templates."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-list')
        data = {
            'name': '5v5 Tournament',
            'game_id': game_valorant.id,
            'template_config': {
                'format': 'single_elimination',
                'max_participants': 16,
                'entry_fee_amount': '500.00'
            },
            'visibility': TournamentTemplate.PRIVATE,
            'description': 'Standard 5v5 competitive tournament'
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == '5v5 Tournament'
        assert response.data['visibility'] == TournamentTemplate.PRIVATE
        assert response.data['is_active'] is True
        
        # Verify in database
        template = TournamentTemplate.objects.get(id=response.data['id'])
        assert template.created_by == user
        assert template.template_config['format'] == 'single_elimination'
    
    def test_create_global_template_non_staff_denied(self, client, user, game_valorant):
        """Non-staff users cannot create GLOBAL templates."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-list')
        data = {
            'name': 'Global Template',
            'game_id': game_valorant.id,
            'template_config': {'format': 'round_robin'},
            'visibility': TournamentTemplate.GLOBAL
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'staff' in response.data['detail'].lower()
    
    def test_create_template_invalid_game(self, client, user):
        """Invalid game_id returns 400 error."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-list')
        data = {
            'name': 'Test Template',
            'game_id': 99999,
            'template_config': {'format': 'single_elimination'},
            'visibility': TournamentTemplate.PRIVATE
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTemplateRetrieveAPI:
    """Tests for GET /api/tournament-templates/{id}/"""
    
    def test_retrieve_global_template(self, client, template_global):
        """Anyone can retrieve GLOBAL templates."""
        url = reverse('tournaments_api:tournament-template-detail', args=[template_global.id])
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Global Template'
        assert 'template_config' in response.data
    
    def test_retrieve_private_template_owner(self, client, user, template_private):
        """Owner can retrieve PRIVATE template."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Private Template'
    
    def test_retrieve_private_template_non_owner_denied(self, client, other_user, template_private):
        """Non-owner cannot retrieve PRIVATE template."""
        client.force_authenticate(user=other_user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        response = client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTemplateUpdateAPI:
    """Tests for PATCH /api/tournament-templates/{id}/"""
    
    def test_update_template_owner_success(self, client, user, template_private):
        """Owner can update template."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        data = {
            'name': 'Updated Template Name',
            'description': 'New description'
        }
        response = client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Template Name'
        
        # Verify in database
        template_private.refresh_from_db()
        assert template_private.name == 'Updated Template Name'
        assert template_private.description == 'New description'
    
    def test_update_template_non_owner_denied(self, client, other_user, template_private):
        """Non-owner cannot update template."""
        client.force_authenticate(user=other_user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        data = {'name': 'Hacked'}
        response = client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_template_config(self, client, user, template_private):
        """Can update template_config."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        data = {
            'template_config': {
                'format': 'double_elimination',
                'max_participants': 32
            }
        }
        response = client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        template_private.refresh_from_db()
        assert template_private.template_config['format'] == 'double_elimination'
        assert template_private.template_config['max_participants'] == 32


@pytest.mark.django_db
class TestTemplateDeleteAPI:
    """Tests for DELETE /api/tournament-templates/{id}/"""
    
    def test_delete_template_owner_success(self, client, user, template_private):
        """Owner can soft-delete template."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify soft delete
        template_private.refresh_from_db()
        assert template_private.is_deleted is True
        assert template_private.deleted_by == user
    
    def test_delete_template_non_owner_denied(self, client, other_user, template_private):
        """Non-owner cannot delete template."""
        client.force_authenticate(user=other_user)
        url = reverse('tournaments_api:tournament-template-detail', args=[template_private.id])
        response = client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        template_private.refresh_from_db()
        assert template_private.is_deleted is False


@pytest.mark.django_db
class TestTemplateApplyAPI:
    """Tests for POST /api/tournament-templates/{id}/apply/"""
    
    def test_apply_template_success(self, client, user, template_with_config):
        """Apply template returns merged configuration."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-apply-template', args=[template_with_config.id])
        data = {
            'tournament_payload': {
                'name': 'My Tournament',
                'entry_fee_amount': '1000.00'  # Override template value
            }
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'merged_config' in response.data
        
        merged = response.data['merged_config']
        assert merged['format'] == 'single_elimination'  # From template
        assert merged['max_participants'] == 16  # From template
        assert merged['entry_fee_amount'] == '1000.00'  # From payload (override)
        assert merged['name'] == 'My Tournament'  # From payload
        
        # Verify usage tracking
        template_with_config.refresh_from_db()
        assert template_with_config.usage_count == 1
        assert template_with_config.last_used_at is not None
    
    def test_apply_inactive_template_denied(self, client, user, template_inactive):
        """Cannot apply inactive templates."""
        client.force_authenticate(user=user)
        url = reverse('tournaments_api:tournament-template-apply-template', args=[template_inactive.id])
        data = {
            'tournament_payload': {'name': 'Test'}
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'inactive' in response.data['detail'].lower()
    
    def test_apply_template_unauthenticated_denied(self, client, template_with_config):
        """Unauthenticated users cannot apply templates."""
        url = reverse('tournaments_api:tournament-template-apply-template', args=[template_with_config.id])
        data = {
            'tournament_payload': {'name': 'Test'}
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_apply_private_template_non_owner_denied(self, client, other_user, template_private):
        """Non-owner cannot apply PRIVATE template."""
        client.force_authenticate(user=other_user)
        url = reverse('tournaments_api:tournament-template-apply-template', args=[template_private.id])
        data = {
            'tournament_payload': {'name': 'Test'}
        }
        response = client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
