"""
Tests for Journey 9 — Admin stability smoke tests

Purpose: Verify admin interface loads without FieldError for vNext models.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAdminNoFieldErrors:
    """Test admin interface loads without FieldError crashes"""
    
    def test_team_admin_changelist_loads_without_error(self, client, admin_user):
        """Verify Team admin changelist loads successfully"""
        client.force_login(admin_user)
        
        # Get Team admin changelist URL
        url = reverse('admin:organizations_team_changelist')
        response = client.get(url)
        
        # Verify no crash
        assert response.status_code == 200, f"Team admin changelist failed with status {response.status_code}"
        
        # Verify no FieldError in response
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "FieldError found in Team admin changelist"
        assert 'Cannot resolve keyword' not in content, "Field resolution error in Team admin"
    
    def test_team_admin_change_view_loads_without_error(self, client, admin_user):
        """Verify Team admin change view loads successfully"""
        from apps.organizations.models import Team
        from tests.factories import create_independent_team
        
        # Create a team
        creator = User.objects.create_user(username='creator', email='creator@example.com', password='pass')
        team, _ = create_independent_team('Admin Test Team', creator, game_id=1)
        
        client.force_login(admin_user)
        
        # Get Team admin change URL
        url = reverse('admin:organizations_team_change', args=[team.id])
        response = client.get(url)
        
        # Verify no crash
        assert response.status_code == 200, f"Team admin change view failed with status {response.status_code}"
        
        # Verify no FieldError
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "FieldError found in Team admin change view"
        assert 'Cannot resolve keyword' not in content, "Field resolution error in Team admin"
    
    def test_organization_admin_changelist_loads_without_error(self, client, admin_user):
        """Verify Organization admin changelist loads successfully"""
        client.force_login(admin_user)
        
        # Get Organization admin changelist URL
        url = reverse('admin:organizations_organization_changelist')
        response = client.get(url)
        
        # Verify no crash
        assert response.status_code == 200, f"Organization admin changelist failed with status {response.status_code}"
        
        # Verify no FieldError
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "FieldError found in Organization admin changelist"
        assert 'Cannot resolve keyword' not in content, "Field resolution error in Organization admin"
    
    def test_organization_admin_change_view_loads_without_error(self, client, admin_user):
        """Verify Organization admin change view loads successfully"""
        from apps.organizations.models import Organization
        
        # Create an organization
        creator = User.objects.create_user(username='org_creator', email='org_creator@example.com', password='pass')
        org = Organization.objects.create(
            name='Admin Test Org',
            slug='admin-test-org',
            badge='ATO',
            ceo=creator
        )
        
        client.force_login(admin_user)
        
        # Get Organization admin change URL
        url = reverse('admin:organizations_organization_change', args=[org.id])
        response = client.get(url)
        
        # Verify no crash
        assert response.status_code == 200, f"Organization admin change view failed with status {response.status_code}"
        
        # Verify no FieldError
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "FieldError found in Organization admin change view"
        assert 'Cannot resolve keyword' not in content, "Field resolution error in Organization admin"
    
    def test_team_membership_admin_changelist_loads_without_error(self, client, admin_user):
        """Verify TeamMembership admin changelist loads successfully"""
        client.force_login(admin_user)
        
        # Get TeamMembership admin changelist URL
        url = reverse('admin:organizations_teammembership_changelist')
        response = client.get(url)
        
        # Verify no crash
        assert response.status_code == 200, f"TeamMembership admin changelist failed with status {response.status_code}"
        
        # Verify no FieldError
        content = response.content.decode('utf-8')
        assert 'FieldError' not in content, "FieldError found in TeamMembership admin changelist"
        assert 'Cannot resolve keyword' not in content, "Field resolution error in TeamMembership admin"


@pytest.fixture
def admin_user():
    """Create admin user for tests"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )
