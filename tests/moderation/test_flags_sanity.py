"""
Flags sanity test: Verify default behavior with all flags OFF.

Confirms:
1. WebSocket connects are allowed when flags OFF
2. Purchases are allowed when flags OFF
3. No PII leaks in responses (IDs only)
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta

from apps.moderation.enforcement import (
    check_websocket_access,
    check_purchase_access,
    get_all_active_policies
)
from apps.moderation.services import sanctions_service

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def moderator_user(db):
    return User.objects.create_user(
        username='moderator',
        email='mod@example.com',
        password='modpass123',
        is_staff=True
    )


@pytest.mark.django_db
class TestFlagsSanity:
    """Verify default behavior with all flags OFF."""
    
    def test_flags_off_websocket_allowed_despite_ban(self, test_user, moderator_user):
        """
        Flags OFF (default): Banned user can still connect to WebSocket.
        
        Confirms zero behavior change until flags explicitly enabled.
        """
        # Create active BAN
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        # Flags OFF (default production config)
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=False,
            MODERATION_ENFORCEMENT_WS=False,
            MODERATION_ENFORCEMENT_PURCHASE=False
        ):
            result = check_websocket_access(user_id=test_user.id)
            
            # Allowed despite BAN
            assert result['allowed'] is True
            assert result['reason_code'] is None
            assert result['sanction_id'] is None
            
            # Verify response shape (PII check)
            assert set(result.keys()) == {'allowed', 'reason_code', 'sanction_id'}
            assert isinstance(result['allowed'], bool)
    
    def test_flags_off_purchase_allowed_despite_ban(self, test_user, moderator_user):
        """
        Flags OFF (default): Banned user can still make purchases.
        
        Confirms zero behavior change until flags explicitly enabled.
        """
        # Create active BAN
        sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        
        # Flags OFF (default production config)
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=False,
            MODERATION_ENFORCEMENT_WS=False,
            MODERATION_ENFORCEMENT_PURCHASE=False
        ):
            result = check_purchase_access(user_id=test_user.id)
            
            # Allowed despite BAN
            assert result['allowed'] is True
            assert result['reason_code'] is None
            assert result['sanction_id'] is None
            
            # Verify response shape (PII check)
            assert set(result.keys()) == {'allowed', 'reason_code', 'sanction_id'}
            assert isinstance(result['allowed'], bool)
    
    def test_no_pii_in_enforcement_responses(self, test_user, moderator_user):
        """
        Verify enforcement responses contain NO PII (IDs only).
        
        Checks: No username, no email, no IP addresses in responses.
        """
        # Create active BAN
        result = sanctions_service.create_sanction(
            subject_id=test_user.id,
            type='ban',
            scope='global',
            reason_code='test_violation',
            issued_by=moderator_user.id,
            ends_at=timezone.now() + timedelta(days=7)
        )
        sanction_id = result['sanction_id']
        
        # Flags ON to trigger denial
        with override_settings(
            MODERATION_ENFORCEMENT_ENABLED=True,
            MODERATION_ENFORCEMENT_WS=True,
            MODERATION_ENFORCEMENT_PURCHASE=True
        ):
            # WebSocket check
            ws_result = check_websocket_access(user_id=test_user.id)
            assert ws_result['allowed'] is False
            assert ws_result['reason_code'] == 'BANNED'
            assert ws_result['sanction_id'] == sanction_id
            
            # Verify NO PII in response
            assert 'username' not in ws_result
            assert 'email' not in ws_result
            assert 'user_name' not in ws_result
            assert 'email_address' not in ws_result
            assert test_user.username not in str(ws_result)
            assert test_user.email not in str(ws_result)
            
            # Purchase check
            purchase_result = check_purchase_access(user_id=test_user.id)
            assert purchase_result['allowed'] is False
            assert purchase_result['reason_code'] == 'BANNED'
            assert purchase_result['sanction_id'] == sanction_id
            
            # Verify NO PII in response
            assert 'username' not in purchase_result
            assert 'email' not in purchase_result
            assert test_user.username not in str(purchase_result)
            assert test_user.email not in str(purchase_result)
            
            # Policy check
            policies = get_all_active_policies(user_id=test_user.id)
            assert policies['has_active_sanctions'] is True
            
            # Verify NO PII in policy response
            assert 'username' not in str(policies)
            assert 'email' not in str(policies)
            assert test_user.username not in str(policies)
            assert test_user.email not in str(policies)
            
            # Only IDs present
            for sanction in policies['sanctions']:
                assert 'sanction_id' in sanction
                assert 'username' not in sanction
                assert 'email' not in sanction
    
    def test_flags_off_is_default_production_behavior(self):
        """
        Confirm that default settings (no env vars) result in flags OFF.
        
        This test validates the production default behavior.
        """
        # Simulate clean environment (no override)
        from django.conf import settings
        
        # These should all default to False
        enforcement_enabled = getattr(settings, 'MODERATION_ENFORCEMENT_ENABLED', False)
        ws_enabled = getattr(settings, 'MODERATION_ENFORCEMENT_WS', False)
        purchase_enabled = getattr(settings, 'MODERATION_ENFORCEMENT_PURCHASE', False)
        
        # All should be False by default
        assert enforcement_enabled is False, "MODERATION_ENFORCEMENT_ENABLED should default to False"
        assert ws_enabled is False, "MODERATION_ENFORCEMENT_WS should default to False"
        assert purchase_enabled is False, "MODERATION_ENFORCEMENT_PURCHASE should default to False"
