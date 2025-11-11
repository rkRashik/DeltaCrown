"""
Test Runtime Gates - Phase 8 Hardening

Test-only integration checks for WebSocket and economy operations.
These tests verify that is_sanctioned() can be used as a precondition gate.
NO production code changes - uses existing services with test-only wrappers.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.moderation.services import sanctions_service


@pytest.mark.django_db
class TestWebSocketSanctionGates:
    """Test WebSocket CONNECT should deny banned/suspended users."""
    
    def test_websocket_connect_allowed_for_clean_user(self):
        """Test WebSocket CONNECT allowed when no active sanctions."""
        user_id = 1001
        
        # Check sanction status (test-only wrapper)
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        is_suspended = sanctions_service.is_sanctioned(user_id, type='suspend')
        
        # Should allow connection
        should_deny_connection = is_banned or is_suspended
        assert should_deny_connection is False
    
    def test_websocket_connect_denied_for_banned_user(self):
        """Test WebSocket CONNECT denied when user is banned."""
        user_id = 1002
        
        # Create ban sanction
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        # Check sanction status (test-only wrapper)
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        
        # Should deny connection
        assert is_banned is True
    
    def test_websocket_connect_denied_for_suspended_user(self):
        """Test WebSocket CONNECT denied when user is suspended."""
        user_id = 1003
        
        # Create suspend sanction
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='suspend',
            scope='global',
            reason_code='test',
        )
        
        # Check sanction status (test-only wrapper)
        is_suspended = sanctions_service.is_sanctioned(user_id, type='suspend')
        
        # Should deny connection
        assert is_suspended is True
    
    def test_websocket_connect_allowed_for_muted_user(self):
        """Test WebSocket CONNECT allowed when user is only muted (can connect, not send)."""
        user_id = 1004
        
        # Create mute sanction (doesn't block connection, only messaging)
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='mute',
            scope='global',
            reason_code='test',
        )
        
        # Check connection-blocking sanctions only
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        is_suspended = sanctions_service.is_sanctioned(user_id, type='suspend')
        
        # Should allow connection (mute doesn't block connect)
        should_deny_connection = is_banned or is_suspended
        assert should_deny_connection is False
    
    def test_websocket_connect_allowed_after_revocation(self):
        """Test WebSocket CONNECT allowed after ban is revoked."""
        user_id = 1005
        
        # Create and revoke ban
        result = sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='global',
            reason_code='test',
        )
        sanctions_service.revoke_sanction(sanction_id=result['sanction_id'])
        
        # Check sanction status
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        
        # Should allow connection
        assert is_banned is False
    
    def test_websocket_connect_respects_tournament_scope(self):
        """Test WebSocket CONNECT checks tournament-specific bans."""
        user_id = 1006
        tournament_id = 50
        
        # Create tournament-scoped ban
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='tournament',
            scope_id=tournament_id,
            reason_code='test',
        )
        
        # Check global ban (should be False)
        is_globally_banned = sanctions_service.is_sanctioned(user_id, type='ban', scope='global')
        assert is_globally_banned is False
        
        # Check tournament ban (should be True)
        is_tournament_banned = sanctions_service.is_sanctioned(
            user_id, 
            type='ban', 
            scope='tournament', 
            scope_id=tournament_id
        )
        assert is_tournament_banned is True


@pytest.mark.django_db
class TestEconomySanctionGates:
    """Test economy operations should respect sanctions."""
    
    def test_economy_purchase_allowed_for_clean_user(self):
        """Test economy purchase allowed when no active sanctions."""
        user_id = 2001
        
        # Check sanction status (test-only wrapper)
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        is_muted = sanctions_service.is_sanctioned(user_id, type='mute')
        
        # Should allow purchase
        should_deny_purchase = is_banned or is_muted
        assert should_deny_purchase is False
    
    def test_economy_purchase_denied_for_banned_user(self):
        """Test economy purchase denied when user is banned."""
        user_id = 2002
        
        # Create ban sanction
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        # Check sanction status
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        
        # Should deny purchase
        assert is_banned is True
    
    def test_economy_purchase_denied_for_muted_user(self):
        """Test economy purchase can be denied for muted users (policy-dependent)."""
        user_id = 2003
        
        # Create mute sanction
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='mute',
            scope='global',
            reason_code='test',
        )
        
        # Check sanction status
        is_muted = sanctions_service.is_sanctioned(user_id, type='mute')
        
        # Mute sanction exists (enforcement policy TBD)
        assert is_muted is True
    
    def test_economy_purchase_allowed_for_suspended_user(self):
        """Test economy purchase allowed when user is suspended (can spend, not participate)."""
        user_id = 2004
        
        # Create suspend sanction (blocks tournament participation, not purchases)
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='suspend',
            scope='global',
            reason_code='test',
        )
        
        # Check purchase-blocking sanctions only
        is_banned = sanctions_service.is_sanctioned(user_id, type='ban')
        
        # Should allow purchase (suspend doesn't block economy)
        assert is_banned is False
    
    def test_economy_checks_effective_policies(self):
        """Test economy can check all active sanctions via effective_policies()."""
        user_id = 2005
        
        # Create multiple sanctions
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='global',
            reason_code='test1',
        )
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='mute',
            scope='global',
            reason_code='test2',
        )
        
        # Get all effective policies
        policies = sanctions_service.effective_policies(subject_id=user_id)
        
        # Should have both sanctions
        assert policies['has_sanctions'] is True
        assert len(policies['sanctions']) == 2
        
        # Check if any policy blocks purchases
        sanction_types = {s['type'] for s in policies['sanctions']}
        has_purchase_blocking_sanction = 'ban' in sanction_types or 'mute' in sanction_types
        assert has_purchase_blocking_sanction is True


@pytest.mark.django_db
class TestSanctionGatePerformance:
    """Test that sanction checks are fast enough for runtime gates."""
    
    def test_is_sanctioned_query_fast(self):
        """Test is_sanctioned() is reasonable for hot-path checks."""
        import time
        
        user_id = 3001
        
        # Create sanction
        sanctions_service.create_sanction(
            subject_id=user_id,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        # Time 100 checks
        start = time.time()
        for _ in range(100):
            sanctions_service.is_sanctioned(user_id, type='ban')
        elapsed = time.time() - start
        
        # Should be reasonable (<1s for 100 checks in test DB)
        assert elapsed < 1.0, f"100 is_sanctioned() calls took {elapsed:.3f}s"
    
    def test_effective_policies_query_fast(self):
        """Test effective_policies() is reasonable for comprehensive checks."""
        import time
        
        user_id = 3002
        
        # Create 3 sanctions
        for i in range(3):
            sanctions_service.create_sanction(
                subject_id=user_id,
                type=['ban', 'suspend', 'mute'][i],
                scope='global',
                reason_code=f'test{i}',
            )
        
        # Time 50 checks
        start = time.time()
        for _ in range(50):
            sanctions_service.effective_policies(subject_id=user_id)
        elapsed = time.time() - start
        
        # Should be reasonable (<1s for 50 checks in test DB)
        assert elapsed < 1.0, f"50 effective_policies() calls took {elapsed:.3f}s"
