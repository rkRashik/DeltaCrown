"""
Profile Dashboard Smoke Test (UP-PHASE-2.1)

Tests the Phase 2 dashboard implementation after hotfix:
- Dashboard summary builds without ImportError
- Tab validation works (valid/invalid/owner-only)
- Privacy flags work correctly
- Page renders without crashes
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class ProfileDashboardSmokeTest(TestCase):
    """Smoke test for Phase 2 dashboard after hotfix"""
    
    def setUp(self):
        """Create test users and profiles"""
        self.owner = User.objects.create_user(
            username='dashowner',
            email='dashowner@test.com',
            password='test123'
        )
        self.visitor = User.objects.create_user(
            username='dashvisitor',
            email='dashvisitor@test.com',
            password='test123'
        )
        
        self.owner_profile = UserProfile.objects.get(user=self.owner)
        self.visitor_profile = UserProfile.objects.get(user=self.visitor)
        
        self.client = Client()
    
    def test_profile_page_loads_without_importerror(self):
        """Test that profile page renders without ImportError (PRIMARY TEST)"""
        # Login as owner
        self.client.login(username='dashowner', password='test123')
        
        # Request own profile (this triggered ImportError before hotfix)
        response = self.client.get(f'/@{self.owner.username}/')
        
        # Should return 200 OK (not 500 Internal Server Error)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'dashboard_summary' in response.context, "Missing dashboard_summary in context"
    
    def test_dashboard_summary_has_all_sections(self):
        """Test that dashboard summary contains all expected sections"""
        self.client.login(username='dashowner', password='test123')
        
        response = self.client.get(f'/@{self.owner.username}/')
        
        assert response.status_code == 200
        summary = response.context.get('dashboard_summary', {})
        
        # Assert all sections are present
        expected_sections = ['posts', 'media', 'loadout', 'career', 'stats', 'highlights', 'bounties', 'inventory', 'economy']
        for section in expected_sections:
            assert section in summary, f"Missing section: {section}"
    
    def test_economy_section_hidden_from_non_owner(self):
        """Test that economy section is private for non-owner"""
        # Login as visitor
        self.client.login(username='dashvisitor', password='test123')
        
        # View owner's profile
        response = self.client.get(f'/@{self.owner.username}/')
        
        if response.status_code == 200:
            summary = response.context.get('dashboard_summary', {})
            
            # Economy should be private for non-owner
            if 'economy' in summary and summary['economy']:
                assert summary['economy'].get('is_private') is True, "Economy should be private for non-owner"
    
    def test_invalid_tab_redirects_to_overview(self):
        """Test that invalid tab parameter redirects to overview"""
        self.client.login(username='dashowner', password='test123')
        
        # Request profile with invalid tab
        response = self.client.get(f'/@{self.owner.username}/?tab=invalid_tab_name')
        
        # Should redirect to overview
        assert response.status_code == 302, "Invalid tab should redirect"
        assert '?tab=overview' in response.url, "Should redirect to overview tab"
    
    def test_owner_only_tab_blocked_for_non_owner(self):
        """Test that economy tab is blocked for non-owner"""
        self.client.login(username='dashvisitor', password='test123')
        
        # Request owner's profile with economy tab
        response = self.client.get(f'/@{self.owner.username}/?tab=economy')
        
        # Should redirect to overview
        assert response.status_code == 302, "Owner-only tab should redirect"
        assert '?tab=overview' in response.url, "Should redirect to overview tab"
    
    def test_valid_tabs_work_correctly(self):
        """Test that all valid tabs are accepted"""
        self.client.login(username='dashowner', password='test123')
        
        valid_tabs = ['overview', 'career', 'stats', 'media', 'loadout', 'highlights', 'bounties', 'inventory', 'economy']
        
        for tab in valid_tabs:
            response = self.client.get(f'/@{self.owner.username}/?tab={tab}')
            # Should NOT redirect (200 OK)
            assert response.status_code == 200, f"Tab '{tab}' should be valid but got {response.status_code}"
    
    def test_anonymous_user_cannot_see_economy(self):
        """Test that anonymous users cannot see economy section"""
        # Don't login - anonymous request
        response = self.client.get(f'/@{self.owner.username}/')
        
        # Should render (unless profile is private)
        if response.status_code == 200:
            summary = response.context.get('dashboard_summary', {})
            # Economy should be private for anonymous
            if 'economy' in summary and summary['economy']:
                assert summary['economy'].get('is_private') is True, "Economy should be private for anonymous user"


@pytest.mark.django_db
class ProfileDashboardIntegrationTest(TestCase):
    """Integration test for dashboard with real page rendering"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='integtest',
            email='integtest@test.com',
            password='test123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client = Client()
    
    def test_full_page_render_cycle(self):
        """Test complete page render cycle (view → context → template)"""
        self.client.login(username='integtest', password='test123')
        
        # Request profile
        response = self.client.get(f'/@{self.user.username}/')
        
        # Should render successfully
        assert response.status_code == 200
        assert 'dashboard_summary' in response.context
        
        # Dashboard summary should have all sections
        summary = response.context['dashboard_summary']
        assert all(key in summary for key in ['posts', 'media', 'loadout', 'career', 'stats', 'highlights', 'bounties', 'inventory', 'economy'])
    
    def test_page_contains_tab_navigation(self):
        """Test that page contains JavaScript tab navigation"""
        self.client.login(username='integtest', password='test123')
        
        response = self.client.get(f'/@{self.user.username}/')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Check for tab validation in JavaScript
        assert 'function switchTab' in content, "Missing switchTab function"
        assert 'validTabs' in content or 'overview' in content, "Missing tab validation"

