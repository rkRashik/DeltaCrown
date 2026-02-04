"""
Phase 14: Test team manage page renders without crashes.

Test Objectives:
1. Team manage page loads successfully with HQ template
2. Page renders with minimal context (no KeyError crashes)
3. Safe defaults prevent template errors
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus

User = get_user_model()


@pytest.mark.django_db
class TestTeamManageRenders(TestCase):
    """Test that team manage page renders with HQ template."""
    
    def setUp(self):
        """Set up test user and team."""
        self.client = Client()
        self.user = User.objects.create_user(username='team_owner', password='pass123')
        
        # Create team
        self.team = Team.objects.create(
            name='Echo Team',
            slug='echo-team',
            created_by=self.user,
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            game_id='1',  # String
        )
    
    def test_team_manage_renders_without_error(self):
        """Test team manage page renders successfully."""
        # Login as team creator
        self.client.login(username='team_owner', password='pass123')
        
        # Make request to team manage page
        response = self.client.get(f'/teams/{self.team.slug}/manage/')
        
        # Should render successfully
        assert response.status_code == 200, f"Team manage page returned {response.status_code}"
        
        # Check template rendered (HQ template)
        content = response.content.decode('utf-8')
        assert 'Echo Team' in content or 'Team HQ' in content, "Team name or HQ title not in page"
    
    def test_team_manage_no_crashes_with_minimal_context(self):
        """Test team manage doesn't crash with empty stats/matches."""
        # Login as team creator
        self.client.login(username='team_owner', password='pass123')
        
        # Make request
        response = self.client.get(f'/teams/{self.team.slug}/manage/')
        
        # Should not raise any exceptions
        assert response.status_code == 200
        
        # Should not have KeyError in response (would show Django error page)
        assert 'KeyError' not in response.content.decode('utf-8')
        assert 'TemplateSyntaxError' not in response.content.decode('utf-8')
