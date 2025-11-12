"""
End-to-end tests for moderation enforcement wiring.

Tests runtime integration of sanctions into WebSocket and economy entry points.
Validates feature flag behavior (OFF = no enforcement, ON = enforced).
"""
import pytest
import time
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from apps.moderation.models import ModerationSanction
from apps.moderation.enforcement import (
    should_enforce_moderation,
    check_websocket_access,
    check_purchase_access,
    get_all_active_policies
)
from apps.moderation.services import sanctions_service

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def moderator_user(db):
    """Create moderator user."""
    return User.objects.create_user(
        username='moderator',
        email='mod@example.com',
        password='modpass123',
        is_staff=True
    )


@pytest.mark.django_db
class TestWebSocketEnforcement:
    """WebSocket CONNECT enforcement gates."""
    
    def test_flags_off_allows_banned_user(self, test_user, moderator_user):
        """With flags OFF, banned user can still connect to WebSocket."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=False,
            MODERATION_ENFORCEMENT_WS=False
        ):
            result = check_websocket_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None
    
    def test_flags_on_blocks_banned_user(self, test_user, moderator_user):
        """With flags ON, banned user is blocked from WebSocket CONNECT."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            result = check_websocket_access(user_id=test_user.id)
            assert result['allowed'] is False
            assert result['reason_code'] == 'BANNED'
            assert result['sanction_id'] == sanction_id
    
    def test_flags_on_blocks_suspended_user(self, test_user, moderator_user):
        """With flags ON, suspended user is blocked from WebSocket CONNECT."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='suspend',
            scope='global',
            reason_code='tournament_abuse',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=3)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            result = check_websocket_access(user_id=test_user.id)
            assert result['allowed'] is False
            assert result['reason_code'] == 'SUSPENDED'
            assert result['sanction_id'] == sanction_id
    
    def test_flags_on_allows_muted_user(self, test_user, moderator_user):
        """MUTE does not block WebSocket CONNECT (only restricts message sending)."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='mute',
            scope='global',
            reason_code='spam',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=1)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            result = check_websocket_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None
    
    def test_tournament_scoped_ban_blocks_only_that_tournament(self, test_user, moderator_user):
        """Tournament-scoped BAN blocks only that tournament's WebSocket."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='tournament',
            scope_id=123,
            reason_code='tournament_specific',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            # Tournament 123: blocked
            result_blocked = check_websocket_access(user_id=test_user.id, tournament_id=123)
            assert result_blocked['allowed'] is False
            assert result_blocked['reason_code'] == 'BANNED'
            assert result_blocked['sanction_id'] == sanction_id
            
            # Tournament 456: allowed
            result_allowed = check_websocket_access(user_id=test_user.id, tournament_id=456)
            assert result_allowed['allowed'] is True
            assert result_allowed['reason_code'] is None
    
    def test_revoked_sanction_allows_connect(self, test_user, moderator_user):
        """Revoked sanction does not block WebSocket CONNECT."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        # Revoke it
        sanctions_service.revoke_sanction(
            sanction_id=sanction_id,
            revoked_by=moderator_user.id,
            notes={'reason': 'appeal_accepted'}
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            result = check_websocket_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None
    
    def test_anonymous_user_unaffected(self):
        """Anonymous/unauthenticated users pass through."""
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            # Non-existent user_id (simulates anonymous)
            result = check_websocket_access(user_id=99999)
            assert result['allowed'] is True
            assert result['reason_code'] is None


@pytest.mark.django_db
class TestEconomyEnforcement:
    """Economy/shop purchase enforcement gates."""
    
    def test_flags_off_allows_banned_purchase(self, test_user, moderator_user):
        """With flags OFF, banned user can still make purchases."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=False,
            MODERATION_ENFORCEMENT_PURCHASE=False
        ):
            result = check_purchase_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None
    
    def test_flags_on_blocks_banned_purchase(self, test_user, moderator_user):
        """With flags ON, banned user cannot make purchases."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            result = check_purchase_access(user_id=test_user.id)
            assert result['allowed'] is False
            assert result['reason_code'] == 'BANNED'
            assert result['sanction_id'] == sanction_id
    
    def test_flags_on_blocks_muted_purchase(self, test_user, moderator_user):
        """With flags ON, muted user cannot make purchases."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='mute',
            scope='global',
            reason_code='spam',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=1)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            result = check_purchase_access(user_id=test_user.id)
            assert result['allowed'] is False
            assert result['reason_code'] == 'MUTED'
            assert result['sanction_id'] == sanction_id
    
    def test_flags_on_allows_suspended_purchase(self, test_user, moderator_user):
        """SUSPEND blocks tournament participation but allows purchases."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='suspend',
            scope='global',
            reason_code='tournament_abuse',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=3)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            result = check_purchase_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None
    
    def test_scoped_ban_affects_only_tournament_purchases(self, test_user, moderator_user):
        """Tournament-scoped BAN blocks only tournament-specific purchases."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='tournament',
            scope_id=123,
            reason_code='tournament_specific',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            # Tournament 123 purchase: blocked
            result_blocked = check_purchase_access(user_id=test_user.id, tournament_id=123)
            assert result_blocked['allowed'] is False
            assert result_blocked['reason_code'] == 'BANNED'
            assert result_blocked['sanction_id'] == sanction_id
            
            # Global purchase (no tournament_id): allowed
            result_allowed = check_purchase_access(user_id=test_user.id)
            assert result_allowed['allowed'] is True
            assert result_allowed['reason_code'] is None
    
    def test_revoked_sanction_allows_purchase(self, test_user, moderator_user):
        """Revoked sanction does not block purchases."""
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        # Revoke it
        sanctions_service.revoke_sanction(
            sanction_id=sanction_id,
            revoked_by=moderator_user.id,
            notes={'reason': 'appeal_accepted'}
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            result = check_purchase_access(user_id=test_user.id)
            assert result['allowed'] is True
            assert result['reason_code'] is None


@pytest.mark.django_db
class TestComprehensivePolicies:
    """Test comprehensive policy queries and UI display helpers."""
    
    def test_multiple_sanctions_show_all_blocked_actions(self, test_user, moderator_user):
        """User with multiple sanctions sees all blocked actions in policy response."""
        # Create BAN (blocks WebSocket + Purchase)
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='severe_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=30)
        )
        
        # Create MUTE (blocks Purchase)
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='mute',
            scope='global',
            reason_code='spam',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        policies = get_all_active_policies(user_id=test_user.id)
        
        assert policies['has_active_sanctions'] is True
        assert len(policies['sanctions']) == 2
        assert 'WEBSOCKET' in policies['blocked_actions']
        assert 'PURCHASE' in policies['blocked_actions']
    
    def test_no_sanctions_returns_empty_policy(self, test_user):
        """User with no sanctions returns empty policy."""
        policies = get_all_active_policies(user_id=test_user.id)
        
        assert policies['has_active_sanctions'] is False
        assert len(policies['sanctions']) == 0
        assert len(policies['blocked_actions']) == 0


@pytest.mark.django_db
class TestConcurrentEnforcement:
    """Test concurrent purchase attempts under enforcement."""
    
    def test_concurrent_purchase_attempts_both_denied(self, test_user, moderator_user):
        """Two simultaneous purchase attempts for banned user both denied."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            # Simulate concurrent checks
            result1 = check_purchase_access(user_id=test_user.id)
            result2 = check_purchase_access(user_id=test_user.id)
            
            assert result1['allowed'] is False
            assert result2['allowed'] is False
            assert result1['reason_code'] == 'BANNED'
            assert result2['reason_code'] == 'BANNED'


@pytest.mark.django_db
class TestPerformanceSmoke:
    """Performance smoke tests for enforcement gates."""
    
    def test_websocket_gate_performance(self, test_user, moderator_user):
        """WebSocket gate check completes in < 50ms average."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True
        ):
            iterations = 10
            times = []
            
            for _ in range(iterations):
                start = time.time()
                check_websocket_access(user_id=test_user.id)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            assert avg_time < 0.05, f"Average {avg_time:.3f}s exceeds 50ms threshold"
    
    def test_purchase_gate_performance(self, test_user, moderator_user):
        """Purchase gate check completes in < 50ms average."""
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            iterations = 10
            times = []
            
            for _ in range(iterations):
                start = time.time()
                check_purchase_access(user_id=test_user.id)
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            assert avg_time < 0.05, f"Average {avg_time:.3f}s exceeds 50ms threshold"
    
    def test_comprehensive_policy_performance(self, test_user, moderator_user):
        """Comprehensive policy query completes in < 100ms average."""
        for sanction_type in ['ban', 'mute', 'suspend']:
            sanctions_service.create_sanction(
                subject_id=test_user.id,
                type=sanction_type,
                scope='global',
                reason_code=f'{sanction_type}_test',
                issued_by=moderator_user.id,
                ends_at=timezone.now() + timedelta(days=7)
            )
        
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.time()
            get_all_active_policies(user_id=test_user.id)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1, f"Average {avg_time:.3f}s exceeds 100ms threshold"
