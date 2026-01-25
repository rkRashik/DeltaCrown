"""
Tests for Dual-Write Sync Service (P5-T3).

Test Coverage:
1. Legacy writes blocked normally (baseline P5-T2)
2. Legacy writes succeed inside bypass context
3. Dual-write creates/updates legacy rows
4. Idempotency (calling same sync twice doesn't duplicate)
5. Failure isolation (legacy sync fails, vNext write succeeds unless strict mode)
6. Query count sanity
"""

import pytest
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.organizations.models import Team as VNextTeam, TeamMembership as VNextMembership, TeamMigrationMap
from apps.teams.models import Team as LegacyTeam, TeamMembership as LegacyMembership
from apps.organizations.services.exceptions import LegacyWriteBlockedException
from apps.organizations.services.dual_write_service import dual_write_service
from apps.teams.mixins import legacy_write_bypass
from apps.user_profile.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestLegacyWriteEnforcementBaseline:
    """Test 1: Verify P5-T2 write blocking still works"""
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=True)
    def test_legacy_write_blocked_normally(self):
        """Legacy model writes should be blocked when enforcement enabled"""
        user = User.objects.create_user(username='test', password='test')
        profile = UserProfile.objects.create(user=user, username='test')
        
        # Attempt to create legacy team (should fail)
        with pytest.raises(LegacyWriteBlockedException) as exc:
            LegacyTeam.objects.create(
                name='Test Team',
                slug='test-team',
                game='valorant'
            )
        
        assert exc.value.error_code == 'LEGACY_WRITE_BLOCKED'
        assert LegacyTeam.objects.count() == 0
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=True)
    def test_legacy_membership_write_blocked(self):
        """Legacy membership writes should be blocked"""
        user = User.objects.create_user(username='test', password='test')
        profile = UserProfile.objects.create(user=user, username='test')
        
        # Create legacy team using bypass (for setup)
        with legacy_write_bypass(reason="test_setup"):
            legacy_team = LegacyTeam.objects.create(name='Test', slug='test', game='valorant')
        
        # Attempt to create membership (should fail)
        with pytest.raises(LegacyWriteBlockedException):
            LegacyMembership.objects.create(
                team=legacy_team,
                profile=profile,
                role='PLAYER'
            )


@pytest.mark.django_db
class TestLegacyWriteBypassContext:
    """Test 2: Verify bypass context manager works"""
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=True)
    def test_bypass_allows_legacy_write(self):
        """Legacy writes should succeed inside bypass context"""
        with legacy_write_bypass(reason="test_bypass"):
            legacy_team = LegacyTeam.objects.create(
                name='Test Team',
                slug='test-team',
                game='valorant'
            )
        
        assert legacy_team.id is not None
        assert LegacyTeam.objects.count() == 1
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=True)
    def test_bypass_auto_resets(self):
        """Bypass should auto-reset after context exit"""
        with legacy_write_bypass(reason="test_reset"):
            legacy_team = LegacyTeam.objects.create(name='Test', slug='test', game='valorant')
        
        # After context exit, writes should be blocked again
        with pytest.raises(LegacyWriteBlockedException):
            LegacyTeam.objects.create(name='Test2', slug='test2', game='valorant')
    
    @override_settings(TEAM_LEGACY_WRITE_BLOCKED=True)
    def test_bypass_handles_exceptions(self):
        """Bypass should reset even when exception occurs"""
        try:
            with legacy_write_bypass(reason="test_exception"):
                LegacyTeam.objects.create(name='Test', slug='test', game='valorant')
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Bypass should be deactivated
        with pytest.raises(LegacyWriteBlockedException):
            LegacyTeam.objects.create(name='Test2', slug='test2', game='valorant')


@pytest.mark.django_db
class TestDualWriteTeamCreation:
    """Test 3: Verify dual-write creates legacy rows"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_team_created_creates_legacy(self):
        """sync_team_created should create legacy team and mapping"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        
        # Create vNext team
        vnext_team = VNextTeam.objects.create(
            name='Delta Squad',
            slug='delta-squad',
            description='Test team',
            owner=user,
            status='ACTIVE',
            game_id=1,
            region='NA'
        )
        
        # Sync to legacy
        result = dual_write_service.sync_team_created(vnext_team.id, actor_user_id=user.id)
        
        assert result['success'] is True
        assert result['created'] is True
        assert 'legacy_team_id' in result
        
        # Verify legacy team created
        legacy_team = LegacyTeam.objects.get(id=result['legacy_team_id'])
        assert legacy_team.name == 'Delta Squad'
        assert legacy_team.slug == 'delta-squad'
        assert legacy_team.game == 'valorant'
        
        # Verify mapping created
        mapping = TeamMigrationMap.objects.get(vnext_team_id=vnext_team.id)
        assert mapping.legacy_team_id == legacy_team.id
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_team_created_idempotent(self):
        """Calling sync_team_created twice should not duplicate"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        
        vnext_team = VNextTeam.objects.create(
            name='Delta Squad',
            slug='delta-squad',
            owner=user,
            status='ACTIVE'
        )
        
        # First sync
        result1 = dual_write_service.sync_team_created(vnext_team.id)
        legacy_id_1 = result1['legacy_team_id']
        
        # Second sync (should be idempotent)
        result2 = dual_write_service.sync_team_created(vnext_team.id)
        
        assert result2['success'] is True
        assert result2['created'] is False
        assert result2['idempotent'] is True
        assert result2['legacy_team_id'] == legacy_id_1
        
        # Should only have one legacy team
        assert LegacyTeam.objects.count() == 1
        assert TeamMigrationMap.objects.count() == 1


@pytest.mark.django_db
class TestDualWriteMembership:
    """Test 3: Verify dual-write syncs memberships"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_member_added_creates_legacy(self):
        """sync_team_member_added should create legacy membership"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        
        # Create vNext team
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        
        # Sync team first
        dual_write_service.sync_team_created(vnext_team.id)
        
        # Create vNext membership
        vnext_membership = VNextMembership.objects.create(
            team=vnext_team,
            user=user,
            role='OWNER'
        )
        
        # Sync membership
        result = dual_write_service.sync_team_member_added(vnext_membership.id)
        
        assert result['success'] is True
        assert result['created'] is True
        
        # Verify legacy membership created
        mapping = TeamMigrationMap.objects.get(vnext_team_id=vnext_team.id)
        legacy_membership = LegacyMembership.objects.get(team_id=mapping.legacy_team_id, profile=profile)
        assert legacy_membership.role == 'OWNER'
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_member_updated_changes_role(self):
        """sync_team_member_updated should update legacy role"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        dual_write_service.sync_team_created(vnext_team.id)
        
        vnext_membership = VNextMembership.objects.create(team=vnext_team, user=user, role='MEMBER')
        dual_write_service.sync_team_member_added(vnext_membership.id)
        
        # Update role
        vnext_membership.role = 'MANAGER'
        vnext_membership.save()
        
        # Sync update
        result = dual_write_service.sync_team_member_updated(vnext_membership.id)
        
        assert result['success'] is True
        
        # Verify legacy role updated
        mapping = TeamMigrationMap.objects.get(vnext_team_id=vnext_team.id)
        legacy_membership = LegacyMembership.objects.get(team_id=mapping.legacy_team_id, profile=profile)
        assert legacy_membership.role == 'MANAGER'


@pytest.mark.django_db
class TestDualWriteFailureIsolation:
    """Test 5: Verify failures don't crash vNext writes (unless strict mode)"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_legacy_sync_failure_logged_not_raised(self):
        """When legacy sync fails, should log but not crash (best-effort mode)"""
        user = User.objects.create_user(username='owner', password='test')
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        
        # Mock LegacyTeam.objects.create to raise error
        with patch('apps.organizations.services.dual_write_service.LegacyTeam.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            result = dual_write_service.sync_team_created(vnext_team.id)
            
            # Should return failure but not raise
            assert result['success'] is False
            assert 'error' in result
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_strict_mode_raises_on_failure(self):
        """In strict mode, legacy sync failures should raise"""
        user = User.objects.create_user(username='owner', password='test')
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        
        with patch('apps.organizations.services.dual_write_service.LegacyTeam.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            with pytest.raises(Exception, match="Database error"):
                dual_write_service.sync_team_created(vnext_team.id)


@pytest.mark.django_db
class TestDualWriteDisabled:
    """Test that dual-write skips when disabled"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=False,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_dual_write_disabled_skips_sync(self):
        """When disabled, sync methods should skip and return success"""
        user = User.objects.create_user(username='owner', password='test')
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        
        result = dual_write_service.sync_team_created(vnext_team.id)
        
        assert result['success'] is True
        assert result['skipped'] is True
        assert result['reason'] == 'disabled'
        
        # No legacy team should be created
        assert LegacyTeam.objects.count() == 0
        assert TeamMigrationMap.objects.count() == 0


@pytest.mark.django_db
class TestDualWriteQueryCount:
    """Test 6: Verify reasonable query counts"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_team_created_query_count(self, django_assert_num_queries):
        """sync_team_created should have reasonable query count"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        vnext_team = VNextTeam.objects.create(
            name='Test',
            slug='test',
            owner=user,
            status='ACTIVE'
        )
        
        # Expected queries:
        # 1. SELECT vNext team
        # 2. SELECT TeamMigrationMap (idempotency check)
        # 3. INSERT LegacyTeam
        # 4. INSERT TeamMigrationMap
        # ~4-6 queries (allowing some overhead for transactions)
        
        with django_assert_num_queries(10):  # Generous budget
            dual_write_service.sync_team_created(vnext_team.id)
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_membership_query_count(self, django_assert_num_queries):
        """sync_team_member_added should have reasonable query count"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        vnext_team = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        dual_write_service.sync_team_created(vnext_team.id)
        
        vnext_membership = VNextMembership.objects.create(team=vnext_team, user=user, role='OWNER')
        
        # Expected queries:
        # 1. SELECT vNext membership
        # 2. SELECT TeamMigrationMap
        # 3. SELECT existing legacy membership (idempotency)
        # 4. INSERT legacy membership
        # ~4-6 queries
        
        with django_assert_num_queries(10):  # Generous budget
            dual_write_service.sync_team_member_added(vnext_membership.id)


@pytest.mark.django_db
class TestDualWriteSettings:
    """Test sync_team_settings_updated"""
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_LEGACY_WRITE_BLOCKED=True
    )
    def test_sync_team_settings_updates_legacy(self):
        """sync_team_settings_updated should update legacy team fields"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        vnext_team = VNextTeam.objects.create(
            name='Original Name',
            slug='original',
            owner=user,
            status='ACTIVE'
        )
        
        # Sync initial
        dual_write_service.sync_team_created(vnext_team.id)
        
        # Update vNext team
        vnext_team.name = 'New Name'
        vnext_team.description = 'New description'
        vnext_team.save()
        
        # Sync settings
        result = dual_write_service.sync_team_settings_updated(vnext_team.id)
        
        assert result['success'] is True
        assert result['updated'] is True
        
        # Verify legacy team updated
        mapping = TeamMigrationMap.objects.get(vnext_team_id=vnext_team.id)
        legacy_team = LegacyTeam.objects.get(id=mapping.legacy_team_id)
        assert legacy_team.name == 'New Name'
        assert legacy_team.description == 'New description'
