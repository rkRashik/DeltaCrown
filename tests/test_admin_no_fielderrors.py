"""
Admin Regression Tests - Prevent FieldError crashes from removed fields

Tests ensure admin views don't reference removed fields:
- team.owner (replaced with ownership system)
- team.is_public (replaced with visibility)
- team.is_verified (removed)
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.organizations.models import Team
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestAdminNoFieldErrors:
    """Ensure admin views don't crash with FieldError on removed fields"""

    @pytest.fixture
    def superuser(self):
        """Create superuser for admin access"""
        return User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpass123'
        )

    @pytest.fixture
    def test_team(self):
        """Create test team for admin display"""
        game = Game.objects.create(
            name='Test Game',
            display_name='TEST GAME',
            slug='test-game',
            short_code='TEST',
            category='FPS'
        )
        return Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=game.id,
            region='Bangladesh',
            status='ACTIVE',
            visibility='PUBLIC'
        )

    def test_admin_team_list_view_200(self, admin_client, test_team):
        """Admin team list view returns 200 without FieldError"""
        url = reverse('admin:organizations_teamadminproxy_changelist')
        response = admin_client.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Ensure no FieldError in response content
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "Admin list view contains FieldError"
        assert test_team.name in content, "Test team not displayed in list"

    def test_admin_team_change_view_200(self, admin_client, test_team):
        """Admin team change view returns 200 without FieldError"""
        url = reverse('admin:organizations_teamadminproxy_change', args=[test_team.pk])
        response = admin_client.get(url)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Ensure no FieldError in response content
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "Admin change view contains FieldError"

    def test_admin_team_add_view_200(self, admin_client):
        """Admin team add view returns 200 or 403 (permissions) without FieldError"""
        url = reverse('admin:organizations_teamadminproxy_add')
        response = admin_client.get(url)
        
        # Accept 200 (works) or 403 (permissions issue) - just ensure no FieldError
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        
        # Ensure no FieldError in response content
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "Admin add view contains FieldError"

    def test_no_owner_field_references(self, admin_client, test_team):
        """FUTURE: Ensure no team.owner references in admin after full migration"""
        # This test documents the future state - once vNext is complete, 
        # no admin code should reference team.owner
        
        # For now, just ensure the admin views work
        # In vNext, add assertions that scan TeamAdmin source for .owner references
        url = reverse('admin:organizations_teamadminproxy_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
