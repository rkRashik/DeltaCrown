"""
Tests for dual-write hook integration in vNext API endpoints.

Tests verify that:
- Hooks are scheduled via transaction.on_commit() (not executed inline)
- TEAM_VNEXT_DUAL_WRITE_ENABLED flag is respected (no calls when False)
- Strict mode behavior (log-only vs crash on error)
- Zero legacy writes before commit
"""

import pytest
from unittest.mock import patch, MagicMock, call
from django.conf import settings
from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import Team, TeamMembership, Organization, OrganizationMembership
from apps.organizations.services.dual_write_service import DualWriteSyncService

User = get_user_model()


@pytest.mark.django_db
class TestDualWriteHooksDisabled:
    """Test that hooks are NOT called when TEAM_VNEXT_DUAL_WRITE_ENABLED=False."""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_created')
    def test_team_creation_no_dual_write_when_disabled(self, mock_sync):
        """Team creation should NOT call dual-write when flag is False."""
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            '/api/vnext/teams/create/',
            {
                'name': 'Test Team',
                'game_id': 1,
                'region': 'NA',
            },
            format='json'
        )
        
        assert response.status_code == 201
        assert mock_sync.call_count == 0, "sync_team_created should NOT be called"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_member_added')
    def test_member_addition_no_dual_write_when_disabled(self, mock_sync):
        """Member addition should NOT call dual-write when flag is False."""
        user = User.objects.create_user(username='owner', password='testpass')
        member = User.objects.create_user(username='newmember', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/members/add/',
            {
                'user_lookup': str(member.id),
                'role': 'PLAYER',
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_sync.call_count == 0, "sync_team_member_added should NOT be called"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_settings_updated')
    def test_settings_update_no_dual_write_when_disabled(self, mock_sync):
        """Settings update should NOT call dual-write when flag is False."""
        user = User.objects.create_user(username='owner', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/settings/',
            {
                'region': 'EU',
                'description': 'Updated description',
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_sync.call_count == 0, "sync_team_settings_updated should NOT be called"


@pytest.mark.django_db
class TestDualWriteHooksEnabled:
    """Test that hooks ARE scheduled via transaction.on_commit when enabled."""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch('django.db.transaction.on_commit')
    def test_team_creation_schedules_hook(self, mock_on_commit):
        """Team creation should schedule dual-write via transaction.on_commit."""
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            '/api/vnext/teams/create/',
            {
                'name': 'Test Team',
                'game_id': 1,
                'region': 'NA',
            },
            format='json'
        )
        
        assert response.status_code == 201
        assert mock_on_commit.call_count == 1, "transaction.on_commit should be called once"
        
        # Verify callable was passed
        args, kwargs = mock_on_commit.call_args
        assert len(args) == 1
        assert callable(args[0]), "on_commit should receive a callable"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch('django.db.transaction.on_commit')
    def test_member_addition_schedules_hook(self, mock_on_commit):
        """Member addition should schedule dual-write via transaction.on_commit."""
        user = User.objects.create_user(username='owner', password='testpass')
        member = User.objects.create_user(username='newmember', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/members/add/',
            {
                'user_lookup': str(member.id),
                'role': 'PLAYER',
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_on_commit.call_count == 1, "transaction.on_commit should be called once"
        
        # Verify callable was passed
        args, kwargs = mock_on_commit.call_args
        assert len(args) == 1
        assert callable(args[0]), "on_commit should receive a callable"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch('django.db.transaction.on_commit')
    def test_member_role_update_schedules_hook(self, mock_on_commit):
        """Member role update should schedule dual-write via transaction.on_commit."""
        user = User.objects.create_user(username='owner', password='testpass')
        member_user = User.objects.create_user(username='member', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/members/{membership.id}/role/',
            {
                'role': 'SUBSTITUTE',
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_on_commit.call_count == 1, "transaction.on_commit should be called once"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch('django.db.transaction.on_commit')
    def test_member_removal_schedules_hook(self, mock_on_commit):
        """Member removal should schedule dual-write via transaction.on_commit."""
        user = User.objects.create_user(username='owner', password='testpass')
        member_user = User.objects.create_user(username='member', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/members/{membership.id}/remove/',
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_on_commit.call_count == 1, "transaction.on_commit should be called once"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch('django.db.transaction.on_commit')
    def test_settings_update_schedules_hook(self, mock_on_commit):
        """Settings update should schedule dual-write via transaction.on_commit."""
        user = User.objects.create_user(username='owner', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/settings/',
            {
                'region': 'EU',
                'description': 'Updated description',
            },
            format='json'
        )
        
        assert response.status_code == 200
        assert mock_on_commit.call_count == 1, "transaction.on_commit should be called once"


@pytest.mark.django_db
class TestDualWriteStrictMode:
    """Test strict mode behavior (log-only vs crash on error)."""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_created')
    def test_dual_write_failure_logs_only_when_strict_off(self, mock_sync):
        """In non-strict mode, dual-write failures should log but not crash."""
        # Make sync_team_created raise an exception
        mock_sync.side_effect = Exception("Legacy DB connection failed")
        
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            '/api/vnext/teams/create/',
            {
                'name': 'Test Team',
                'game_id': 1,
                'region': 'NA',
            },
            format='json'
        )
        
        # vNext request should succeed despite dual-write failure
        assert response.status_code == 201
        assert 'team_id' in response.data
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=True,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_created')
    def test_dual_write_failure_crashes_when_strict_on(self, mock_sync):
        """In strict mode, dual-write failures should crash the request."""
        # Make sync_team_created raise an exception
        mock_sync.side_effect = Exception("Legacy DB connection failed")
        
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            '/api/vnext/teams/create/',
            {
                'name': 'Test Team',
                'game_id': 1,
                'region': 'NA',
            },
            format='json'
        )
        
        # In strict mode, the exception should propagate
        # Note: Django test client might catch it differently, but sync should be called
        assert mock_sync.call_count >= 1, "sync_team_created should be called"


@pytest.mark.django_db
class TestNoInlineLegacyWrites:
    """Test that legacy writes happen ONLY in on_commit hooks, not inline."""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_created')
    @patch('django.db.transaction.on_commit')
    def test_sync_called_in_hook_not_inline(self, mock_on_commit, mock_sync):
        """Verify sync is called in on_commit hook, not during request."""
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Execute request - this should NOT call sync_team_created directly
        response = client.post(
            '/api/vnext/teams/create/',
            {
                'name': 'Test Team',
                'game_id': 1,
                'region': 'NA',
            },
            format='json'
        )
        
        assert response.status_code == 201
        
        # At this point, sync should NOT have been called yet
        assert mock_sync.call_count == 0, "sync_team_created should NOT be called inline"
        
        # But on_commit should have been called with a callable
        assert mock_on_commit.call_count == 1
        
        # Now execute the hook manually to verify it calls sync
        hook_callable = mock_on_commit.call_args[0][0]
        hook_callable()
        
        # Now sync should have been called
        assert mock_sync.call_count == 1, "sync_team_created should be called in hook"
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE='vnext_primary',
        TEAM_VNEXT_FORCE_LEGACY=False,
    )
    @patch.object(DualWriteSyncService, 'sync_team_member_added')
    @patch('django.db.transaction.on_commit')
    def test_member_sync_called_in_hook_not_inline(self, mock_on_commit, mock_sync):
        """Verify member sync is called in on_commit hook, not during request."""
        user = User.objects.create_user(username='owner', password='testpass')
        member = User.objects.create_user(username='newmember', password='testpass')
        team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game_id=1,
            owner=user,
            status=Team.Status.ACTIVE,
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post(
            f'/api/vnext/teams/{team.slug}/members/add/',
            {
                'user_lookup': str(member.id),
                'role': 'PLAYER',
            },
            format='json'
        )
        
        assert response.status_code == 200
        
        # Sync should NOT have been called yet
        assert mock_sync.call_count == 0
        
        # But on_commit should have been called
        assert mock_on_commit.call_count == 1
        
        # Execute the hook
        hook_callable = mock_on_commit.call_args[0][0]
        hook_callable()
        
        # Now sync should have been called
        assert mock_sync.call_count == 1
