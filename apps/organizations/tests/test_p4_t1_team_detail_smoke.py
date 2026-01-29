"""
Smoke Tests for P4-T1: Team Detail Page (Foundation)

Tests basic functionality of public team detail page:
- View imports work
- Template loads
- URL routing works
- Permission checks (public vs private teams)
- Anonymous access for public teams
- Member-only access for private teams
"""

import pytest
from django.urls import reverse, resolve
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

from apps.organizations.models import Team, TeamMembership, Organization
from apps.organizations.views import team_detail
from apps.organizations.services.team_detail_service import TeamDetailService
from apps.organizations.choices import MembershipStatus


@pytest.mark.django_db
class TestTeamDetailViewImport:
    """Test that team_detail view can be imported and is callable."""
    
    def test_view_import_works(self):
        """team_detail view should be importable from views module."""
        from apps.organizations.views import team_detail
        assert callable(team_detail)
    
    def test_service_import_works(self):
        """TeamDetailService should be importable."""
        from apps.organizations.services.team_detail_service import TeamDetailService
        assert TeamDetailService is not None


@pytest.mark.django_db
class TestTeamDetailURLRouting:
    """Test URL routing for team detail page."""
    
    def test_url_reverse_works(self):
        """URL reverse should work for team_detail."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        assert url == '/teams/test-team/'
    
    def test_url_resolves_to_view(self):
        """URL should resolve to team_detail view function."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        resolved = resolve(url)
        assert resolved.view_name == 'organizations:team_detail'
        # Note: resolved.func is the actual view function
        # We check the module path to verify it's the right view
        assert 'team' in resolved.func.__module__


@pytest.mark.django_db
class TestTeamDetailTemplateLoad:
    """Test that team_detail.html template exists and loads."""
    
    def test_template_exists(self):
        """Template file should exist at correct path."""
        from django.template.loader import get_template
        template = get_template('organizations/team/team_detail.html')
        assert template is not None
    
    def test_template_renders_with_context(self):
        """Template should render with minimal context."""
        from django.template.loader import render_to_string
        context = {
            'team': {
                'name': 'Test Team',
                'slug': 'test-team',
                'tag': 'TEST',
                'is_public': True,
                'avatar': None,
                'banner': None,
                'organization': None,
                'description': 'Test description'
            },
            'member_count': 5,
            'public_members': [],
            'stats': {'tournament_count': 0, 'match_count': 0, 'win_rate': 0},
            'can_view_details': True,
            'can_view_hub': False,
            'can_manage_team': False,
        }
        html = render_to_string('organizations/team/team_detail.html', context)
        assert 'Test Team' in html
        assert 'TEST' in html


@pytest.mark.django_db
class TestTeamDetailPublicAccess:
    """Test that anonymous users can view public teams."""
    
    def test_public_team_accessible_to_anonymous(self, django_user_model):
        """Public teams should be viewable by anonymous users."""
        # Create public team
        owner = django_user_model.objects.create_user(username='owner', password='pass')
        team = Team.objects.create(
            name='Public Team',
            slug='public-team',
            is_public=True,
            owner=owner
        )
        
        # Get service data as anonymous user
        result = TeamDetailService.get_public_team_display(
            team_slug='public-team',
            viewer_user=AnonymousUser()
        )
        
        assert result['can_view_details'] is True
        assert result['team']['name'] == 'Public Team'
    
    def test_private_team_hidden_from_anonymous(self, django_user_model):
        """Private teams should NOT be viewable by anonymous users."""
        # Create private team
        owner = django_user_model.objects.create_user(username='owner', password='pass')
        team = Team.objects.create(
            name='Private Team',
            slug='private-team',
            is_public=False,
            owner=owner
        )
        
        # Get service data as anonymous user
        result = TeamDetailService.get_public_team_display(
            team_slug='private-team',
            viewer_user=AnonymousUser()
        )
        
        assert result['can_view_details'] is False
        assert result['team']['description'] is None  # Hidden


@pytest.mark.django_db
class TestTeamDetailPrivateAccess:
    """Test that members can view private teams."""
    
    def test_private_team_visible_to_member(self, django_user_model):
        """Private teams should be viewable by members."""
        # Create private team
        owner = django_user_model.objects.create_user(username='owner', password='pass')
        member = django_user_model.objects.create_user(username='member', password='pass')
        
        team = Team.objects.create(
            name='Private Team',
            slug='private-team',
            is_public=False,
            owner=owner
        )
        
        # Add member
        TeamMembership.objects.create(
            team=team,
            user=member,
            role='PLAYER',
            status=MembershipStatus.ACTIVE
        )
        
        # Get service data as member
        result = TeamDetailService.get_public_team_display(
            team_slug='private-team',
            viewer_user=member
        )
        
        assert result['can_view_details'] is True
        assert result['can_view_hub'] is True
        assert result['team']['description'] is not None  # Visible to member


@pytest.mark.django_db
class TestTeamDetailServiceQueries:
    """Test that service layer respects query budget."""
    
    def test_service_query_count_within_budget(self, django_user_model, django_assert_num_queries):
        """Service should use ≤5 queries per P4-T1 spec."""
        owner = django_user_model.objects.create_user(username='owner', password='pass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            is_public=True,
            owner=owner
        )
        
        # Add some members
        for i in range(3):
            user = django_user_model.objects.create_user(username=f'member{i}', password='pass')
            TeamMembership.objects.create(
                team=team,
                user=user,
                role='PLAYER',
                status=MembershipStatus.ACTIVE
            )
        
        # Test query count (should be ≤5)
        with django_assert_num_queries(5):  # 1=team, 1=check_member, 1=count, 1=roster, 1=stats(placeholder)
            result = TeamDetailService.get_public_team_display(
                team_slug='test-team',
                viewer_user=AnonymousUser()
            )
        
        assert result['member_count'] == 4  # 3 members + 1 owner


@pytest.mark.django_db
class TestTeamManageURLSeparation:
    """Test that team_manage URL is separate from team_detail."""
    
    def test_manage_url_distinct_from_detail(self):
        """team_manage should have its own URL route."""
        detail_url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        manage_url = reverse('organizations:team_manage', kwargs={'team_slug': 'test-team'})
        
        assert detail_url == '/teams/test-team/'
        assert manage_url == '/teams/test-team/manage/'
        assert detail_url != manage_url
    
    def test_manage_view_import_works(self):
        """team_manage view should be importable."""
        from apps.organizations.views import team_manage
        assert callable(team_manage)
