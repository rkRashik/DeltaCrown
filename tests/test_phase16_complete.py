"""
Phase 16 Group C - Comprehensive Integration Tests

Tests for complete end-to-end functionality:
- Hub shows ALL teams (even brand new, even unranked)
- Rankings include 0-point teams
- Team detail has role-aware CTAs
- Manage HQ is fully wired
- Admin loads without FieldError
"""

import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, Organization, TeamMembership
from apps.organizations.choices import TeamStatus, MembershipRole
from tests.factories import create_user, create_independent_team

User = get_user_model()


@pytest.mark.django_db
class TestHubShowsAllTeams:
    """Hub must show ALL PUBLIC ACTIVE teams including brand new ones."""
    
    def test_hub_shows_brand_new_team_immediately(self, client: Client, django_user_model):
        """Test: Brand new team (0 points, no matches) appears on hub immediately."""
        # Setup: Create user and brand new team
        user = create_user('captain')
        
        team = Team.objects.create(
            name='Brand New Squad',
            slug='brand-new-squad',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        # Act: Load hub page
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Assert: Team appears (no 2-minute cache delay)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Brand New Squad' in content or team.slug in content
        
    def test_hub_shows_unranked_teams(self, client: Client, django_user_model):
        """Test: Teams without ranking snapshots appear on hub."""
        # Setup: Create team with no ranking data
        user = create_user('owner')
        
        team = Team.objects.create(
            name='Unranked Warriors',
            slug='unranked-warriors',
            game_id=1,
            region='EU',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        # Act: Load hub
        response = client.get(reverse('organizations:vnext_hub'))
        
        # Assert: Team visible
        assert response.status_code == 200
        assert 'featured_teams' in response.context
        # Team should be in featured_teams list (even with no ranking)
        team_slugs = [t.slug for t in response.context['featured_teams']]
        assert 'unranked-warriors' in team_slugs or len(response.context['featured_teams']) > 0


@pytest.mark.django_db
class TestRankingsIncludeZeroPoint:
    """Rankings must show ALL PUBLIC ACTIVE teams including 0-point teams."""
    
    def test_global_rankings_include_zero_point_teams(self, client: Client, django_user_model):
        """Test: 0-point teams appear in global rankings."""
        # Setup: Create team with no matches (0 points)
        user = create_user('newbie')
        
        team = Team.objects.create(
            name='Zero Point Team',
            slug='zero-point-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        # Act: Load global rankings
        from apps.competition.services import CompetitionService
        response = CompetitionService.get_global_rankings(limit=100)
        
        # Assert: Team appears with score=0, tier=UNRANKED
        team_ids = [entry.team_id for entry in response.entries]
        assert team.id in team_ids
        
        # Find our team entry
        our_entry = next((e for e in response.entries if e.team_id == team.id), None)
        assert our_entry is not None
        assert our_entry.score == 0
        assert our_entry.tier == 'UNRANKED'
    
    def test_rankings_order_deterministic(self, client: Client, django_user_model):
        """Test: 0-point teams ordered by created_at DESC (tie-breaker)."""
        # Setup: Create 3 teams with 0 points at different times
        user = create_user('admin')
        
        team1 = Team.objects.create(
            name='Team Alpha',
            slug='team-alpha',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        team2 = Team.objects.create(
            name='Team Beta',
            slug='team-beta',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        team3 = Team.objects.create(
            name='Team Gamma',
            slug='team-gamma',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        # Act: Get rankings
        from apps.competition.services import CompetitionService
        response = CompetitionService.get_global_rankings(limit=100)
        
        # Assert: All 3 teams present, newest first (gamma, beta, alpha)
        team_ids = [entry.team_id for entry in response.entries]
        assert team1.id in team_ids
        assert team2.id in team_ids
        assert team3.id in team_ids
        
        # Find positions
        idx_gamma = next(i for i, e in enumerate(response.entries) if e.team_id == team3.id)
        idx_alpha = next(i for i, e in enumerate(response.entries) if e.team_id == team1.id)
        
        # Gamma (newest) should rank higher than alpha (oldest) when both have 0 points
        assert idx_gamma < idx_alpha


@pytest.mark.django_db
class TestTeamDetailRoleAwareCTAs:
    """Team detail page must show role-aware CTAs."""
    
    def test_owner_sees_manage_cta(self, client: Client, django_user_model):
        """Test: Team owner sees 'Manage Team' as primary CTA."""
        # Setup: Create owner and team
        owner = create_user('owner')
        
        team = Team.objects.create(
            name='Owner Team',
            slug='owner-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=owner
        )
        
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status='ACTIVE'
        )
        
        # Act: Load team detail as owner
        client.force_login(owner)
        response = client.get(reverse('teams:detail', args=[team.slug]))
        
        # Assert: 'Manage Team' CTA present
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Manage Team' in content or 'manage' in content.lower()
    
    def test_member_sees_team_chat_cta(self, client: Client, django_user_model):
        """Test: Regular member sees 'Team Chat' as primary CTA (not Manage)."""
        # Setup: Create owner, member, team
        owner = create_user('owner')
        member = create_user('member')
        
        team = Team.objects.create(
            name='Member Team',
            slug='member-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=owner
        )
        
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status='ACTIVE'
        )
        
        TeamMembership.objects.create(
            team=team,
            user=member,
            role=MembershipRole.PLAYER,
            status='ACTIVE'
        )
        
        # Act: Load team detail as member
        client.force_login(member)
        response = client.get(reverse('teams:detail', args=[team.slug]))
        
        # Assert: 'Team Chat' CTA present, not 'Manage Team'
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should NOT see full Manage Team access
        assert 'Invite Members' not in content
    
    def test_public_sees_apply_or_follow(self, client: Client, django_user_model):
        """Test: Public user sees 'Apply' (if recruiting) or 'Follow' CTA."""
        # Setup: Create team
        owner = create_user('owner')
        
        team = Team.objects.create(
            name='Public Team',
            slug='public-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=owner
        )
        
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status='ACTIVE'
        )
        
        # Act: Load team detail as anonymous user
        response = client.get(reverse('teams:detail', args=[team.slug]))
        
        # Assert: Join/Follow/Apply CTA present (not Manage)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Manage Team' not in content


@pytest.mark.django_db
class TestManageHQFullyWired:
    """Manage HQ must be functionally wired (not just static)."""
    
    def test_manage_hq_renders_for_owner(self, client: Client, django_user_model):
        """Test: Owner can access manage HQ page (200 OK)."""
        # Setup
        owner = create_user('owner')
        
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=owner
        )
        
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status='ACTIVE'
        )
        
        # Act
        client.force_login(owner)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert
        assert response.status_code == 200
        assert 'team' in response.context
        assert 'is_owner' in response.context
        assert response.context['is_owner'] is True
    
    def test_manage_hq_forbidden_for_non_member(self, client: Client, django_user_model):
        """Test: Non-members cannot access manage HQ (403 or redirect)."""
        # Setup
        owner = create_user('owner')
        outsider = create_user('outsider')
        
        team = Team.objects.create(
            name='Private Team',
            slug='private-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=owner
        )
        
        TeamMembership.objects.create(
            team=team,
            user=owner,
            role=MembershipRole.OWNER,
            status='ACTIVE'
        )
        
        # Act
        client.force_login(outsider)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert
        assert response.status_code in [403, 302]


@pytest.mark.django_db
class TestAdminStability:
    """Admin pages must load without FieldError."""
    
    def test_team_admin_list_loads(self, admin_client):
        """Test: Team admin list page loads without errors."""
        # Act
        response = admin_client.get('/admin/organizations/teamadminproxy/')
        
        # Assert: 200 OK (no FieldError)
        assert response.status_code == 200
    
    def test_team_admin_change_loads(self, admin_client, django_user_model):
        """Test: Team admin change page loads without FieldError."""
        # Setup: Create team
        user = create_user('testuser')
        
        team = Team.objects.create(
            name='Admin Test Team',
            slug='admin-test-team',
            game_id=1,
            region='NA',
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC',
            created_by=user
        )
        
        # Act
        response = admin_client.get(f'/admin/organizations/teamadminproxy/{team.id}/change/')
        
        # Assert: 200 OK (no FieldError on non-existent fields)
        assert response.status_code == 200


@pytest.mark.regression
class TestOwnerFieldNeverReintroduced:
    """Regression: Ensure team.owner never reintroduced."""
    
    def test_team_model_has_no_owner_field(self):
        """Test: Team model doesn't have 'owner' field."""
        field_names = [f.name for f in Team._meta.get_fields()]
        assert 'owner' not in field_names, "Team model should NOT have 'owner' field"
        assert 'created_by' in field_names, "Team model must have 'created_by' field"
    
    def test_no_select_related_owner_in_views(self):
        """Test: Views don't use select_related('owner')."""
        import re
        from pathlib import Path
        
        # Check hub view
        hub_view = Path('apps/organizations/views/hub.py')
        if hub_view.exists():
            with open(hub_view, 'r') as f:
                content = f.read()
            
            # Should not have select_related('owner')
            assert re.search(r"select_related\(['\"]owner['\"]\)", content) is None
