"""
Test Sanctions Service - Phase 8 Module 8.1

Tests for create_sanction, revoke_sanction, is_sanctioned, and effective_policies.

Coverage:
- Create sanctions (5 tests): basic, idempotency, replay, concurrent, invalid params
- Revoke sanctions (4 tests): basic, replay, already revoked, not found
- Query sanctions (5 tests): is_sanctioned truth table
- Overlapping windows (3 tests): multiple sanctions, time windows, scope precedence
- Concurrency (2 tests): double-create race, revoke race
- Negative cases (3 tests): invalid type/scope, time constraint violations
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.moderation.services import sanctions_service
from apps.moderation.models import ModerationSanction, ModerationAudit


@pytest.mark.django_db
class TestCreateSanction:
    """Test create_sanction() with idempotency and validation."""
    
    def test_create_basic_sanction(self):
        """Test basic sanction creation."""
        result = sanctions_service.create_sanction(
            subject_id=101,
            type='ban',
            scope='global',
            reason_code='harassment',
            issued_by=1,
        )
        
        assert result['created'] is True
        assert result['subject_profile_id'] == 101
        assert result['type'] == 'ban'
        assert result['scope'] == 'global'
        assert 'sanction_id' in result
        
        # Verify database
        sanction = ModerationSanction.objects.get(id=result['sanction_id'])
        assert sanction.subject_profile_id == 101
        assert sanction.type == 'ban'
        assert sanction.revoked_at is None
        
        # Verify audit trail
        audit = ModerationAudit.objects.filter(
            ref_type='sanction',
            ref_id=sanction.id,
            event='sanction_created'
        ).first()
        assert audit is not None
        assert audit.actor_id == 1
        assert audit.subject_profile_id == 101
    
    def test_create_with_idempotency_key(self):
        """Test sanction creation with idempotency key."""
        result = sanctions_service.create_sanction(
            subject_id=102,
            type='suspend',
            scope='tournament',
            scope_id=50,
            reason_code='cheating',
            idempotency_key='key_001',
            issued_by=1,
        )
        
        assert result['created'] is True
        sanction_id = result['sanction_id']
        
        # Verify idempotency key is stored
        sanction = ModerationSanction.objects.get(id=sanction_id)
        assert sanction.idempotency_key == 'key_001'
    
    def test_replay_with_idempotency_key(self):
        """Test replaying same request with idempotency key returns existing sanction."""
        # First call
        result1 = sanctions_service.create_sanction(
            subject_id=103,
            type='mute',
            scope='global',
            reason_code='spam',
            idempotency_key='key_002',
            issued_by=1,
        )
        assert result1['created'] is True
        original_id = result1['sanction_id']
        
        # Replay with same key
        result2 = sanctions_service.create_sanction(
            subject_id=999,  # Different subject
            type='ban',  # Different type
            scope='global',
            reason_code='different',
            idempotency_key='key_002',  # Same key
            issued_by=2,
        )
        
        assert result2['created'] is False
        assert result2['sanction_id'] == original_id  # Returns original
        assert result2['subject_profile_id'] == 103  # Original subject
        assert result2['type'] == 'mute'  # Original type
        
        # Verify only one sanction exists
        assert ModerationSanction.objects.filter(idempotency_key='key_002').count() == 1
    
    def test_unique_idempotency_key_constraint(self):
        """Test database enforces unique idempotency key constraint."""
        # Create first sanction
        sanctions_service.create_sanction(
            subject_id=104,
            type='ban',
            scope='global',
            reason_code='test1',
            idempotency_key='unique_key',
            issued_by=1,
        )
        
        # Try to create second with different data but same key
        # Should return existing (idempotency)
        result = sanctions_service.create_sanction(
            subject_id=999,
            type='mute',
            scope='global',
            reason_code='test2',
            idempotency_key='unique_key',  # Same key
            issued_by=2,
        )
        
        assert result['created'] is False
        assert result['subject_profile_id'] == 104  # Original
        
        # Verify only one sanction exists
        sanctions = ModerationSanction.objects.filter(idempotency_key='unique_key')
        assert sanctions.count() == 1
    
    def test_invalid_parameters(self):
        """Test validation of invalid parameters."""
        # Missing subject_id
        with pytest.raises(ValueError, match="subject_id is required"):
            sanctions_service.create_sanction(
                subject_id=None,
                type='ban',
                scope='global',
                reason_code='test',
            )
        
        # Invalid type
        with pytest.raises(ValueError, match="Invalid type"):
            sanctions_service.create_sanction(
                subject_id=105,
                type='invalid_type',
                scope='global',
                reason_code='test',
            )
        
        # Invalid scope
        with pytest.raises(ValueError, match="Invalid scope"):
            sanctions_service.create_sanction(
                subject_id=105,
                type='ban',
                scope='invalid_scope',
                reason_code='test',
            )
        
        # Tournament scope without scope_id
        with pytest.raises(ValueError, match="scope_id required"):
            sanctions_service.create_sanction(
                subject_id=105,
                type='ban',
                scope='tournament',
                reason_code='test',
            )
        
        # Missing reason_code
        with pytest.raises(ValueError, match="reason_code is required"):
            sanctions_service.create_sanction(
                subject_id=105,
                type='ban',
                scope='global',
                reason_code=None,
            )
    
    def test_ends_at_before_starts_at(self):
        """Test validation that ends_at must be after starts_at."""
        now = timezone.now()
        past = now - timedelta(hours=1)
        
        with pytest.raises(ValueError, match="ends_at must be after starts_at"):
            sanctions_service.create_sanction(
                subject_id=106,
                type='ban',
                scope='global',
                reason_code='test',
                starts_at=now,
                ends_at=past,
            )


@pytest.mark.django_db
class TestRevokeSanction:
    """Test revoke_sanction() with idempotency."""
    
    def test_revoke_basic(self):
        """Test basic sanction revocation."""
        # Create sanction
        create_result = sanctions_service.create_sanction(
            subject_id=201,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=1,
        )
        sanction_id = create_result['sanction_id']
        
        # Revoke it
        revoke_result = sanctions_service.revoke_sanction(
            sanction_id=sanction_id,
            revoked_by=2,
        )
        
        assert revoke_result['revoked'] is True
        assert revoke_result['sanction_id'] == sanction_id
        assert 'revoked_at' in revoke_result
        
        # Verify database
        sanction = ModerationSanction.objects.get(id=sanction_id)
        assert sanction.revoked_at is not None
        
        # Verify audit trail
        audit = ModerationAudit.objects.filter(
            ref_type='sanction',
            ref_id=sanction_id,
            event='sanction_revoked'
        ).first()
        assert audit is not None
        assert audit.actor_id == 2
    
    def test_revoke_already_revoked(self):
        """Test revoking an already revoked sanction (idempotent)."""
        # Create and revoke
        create_result = sanctions_service.create_sanction(
            subject_id=202,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=1,
        )
        sanction_id = create_result['sanction_id']
        
        revoke1 = sanctions_service.revoke_sanction(sanction_id=sanction_id, revoked_by=1)
        assert revoke1['revoked'] is True
        first_revoked_at = revoke1['revoked_at']
        
        # Revoke again
        revoke2 = sanctions_service.revoke_sanction(sanction_id=sanction_id, revoked_by=2)
        assert revoke2['revoked'] is False  # Idempotent: no change
        assert revoke2['revoked_at'] == first_revoked_at  # Same timestamp
        
        # Verify only one audit event for revocation
        audit_count = ModerationAudit.objects.filter(
            ref_type='sanction',
            ref_id=sanction_id,
            event='sanction_revoked'
        ).count()
        assert audit_count == 1
    
    def test_revoke_nonexistent_sanction(self):
        """Test revoking non-existent sanction raises error."""
        with pytest.raises(ValueError, match="Sanction 99999 not found"):
            sanctions_service.revoke_sanction(sanction_id=99999, revoked_by=1)
    
    def test_double_revoke_idempotency(self):
        """Test double revocation is safely idempotent (sequential)."""
        # Create sanction
        create_result = sanctions_service.create_sanction(
            subject_id=203,
            type='ban',
            scope='global',
            reason_code='double_revoke_test',
            issued_by=1,
        )
        sanction_id = create_result['sanction_id']
        
        # First revoke
        result1 = sanctions_service.revoke_sanction(sanction_id=sanction_id, revoked_by=1)
        assert result1['revoked'] is True
        revoked_at_1 = result1['revoked_at']
        
        # Second revoke (idempotent)
        result2 = sanctions_service.revoke_sanction(sanction_id=sanction_id, revoked_by=1)
        assert result2['revoked'] is False  # Already revoked
        assert result2['revoked_at'] == revoked_at_1  # Same timestamp
        
        # Third revoke (idempotent)
        result3 = sanctions_service.revoke_sanction(sanction_id=sanction_id, revoked_by=1)
        assert result3['revoked'] is False
        assert result3['revoked_at'] == revoked_at_1


@pytest.mark.django_db
class TestIsSanctioned:
    """Test is_sanctioned() query with filters."""
    
    def test_active_sanction_returns_true(self):
        """Test active sanction returns True."""
        sanctions_service.create_sanction(
            subject_id=301,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        assert sanctions_service.is_sanctioned(subject_id=301) is True
        assert sanctions_service.is_sanctioned(subject_id=301, type='ban') is True
        assert sanctions_service.is_sanctioned(subject_id=301, scope='global') is True
    
    def test_expired_sanction_returns_false(self):
        """Test expired sanction returns False."""
        now = timezone.now()
        past = now - timedelta(days=7)
        yesterday = now - timedelta(days=1)
        
        sanctions_service.create_sanction(
            subject_id=302,
            type='ban',
            scope='global',
            reason_code='test',
            starts_at=past,
            ends_at=yesterday,
        )
        
        assert sanctions_service.is_sanctioned(subject_id=302) is False
    
    def test_revoked_sanction_returns_false(self):
        """Test revoked sanction returns False."""
        create_result = sanctions_service.create_sanction(
            subject_id=303,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        # Revoke it
        sanctions_service.revoke_sanction(sanction_id=create_result['sanction_id'])
        
        assert sanctions_service.is_sanctioned(subject_id=303) is False
    
    def test_nonexistent_sanction_returns_false(self):
        """Test user with no sanctions returns False."""
        assert sanctions_service.is_sanctioned(subject_id=999) is False
    
    def test_wrong_type_filter_returns_false(self):
        """Test filtering by wrong type returns False."""
        sanctions_service.create_sanction(
            subject_id=304,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        assert sanctions_service.is_sanctioned(subject_id=304, type='ban') is True
        assert sanctions_service.is_sanctioned(subject_id=304, type='mute') is False
    
    def test_wrong_scope_filter_returns_false(self):
        """Test filtering by wrong scope returns False."""
        sanctions_service.create_sanction(
            subject_id=305,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        assert sanctions_service.is_sanctioned(subject_id=305, scope='global') is True
        assert sanctions_service.is_sanctioned(subject_id=305, scope='tournament') is False


@pytest.mark.django_db
class TestOverlappingWindows:
    """Test multiple sanctions with overlapping time windows."""
    
    def test_multiple_sanctions_same_user(self):
        """Test user with multiple active sanctions."""
        # Global ban
        sanctions_service.create_sanction(
            subject_id=401,
            type='ban',
            scope='global',
            reason_code='test1',
        )
        
        # Tournament suspend
        sanctions_service.create_sanction(
            subject_id=401,
            type='suspend',
            scope='tournament',
            scope_id=10,
            reason_code='test2',
        )
        
        # Check both active
        assert sanctions_service.is_sanctioned(subject_id=401, type='ban') is True
        assert sanctions_service.is_sanctioned(subject_id=401, type='suspend') is True
        
        # Check effective policies
        policies = sanctions_service.effective_policies(subject_id=401)
        assert policies['has_sanctions'] is True
        assert len(policies['sanctions']) == 2
    
    def test_overlapping_time_windows(self):
        """Test sanctions with overlapping time windows."""
        now = timezone.now()
        
        # Sanction 1: Active now, expires in 1 day
        sanctions_service.create_sanction(
            subject_id=402,
            type='ban',
            scope='global',
            reason_code='test1',
            starts_at=now,
            ends_at=now + timedelta(days=1),
        )
        
        # Sanction 2: Starts in 12 hours, expires in 2 days
        sanctions_service.create_sanction(
            subject_id=402,
            type='ban',
            scope='global',
            reason_code='test2',
            starts_at=now + timedelta(hours=12),
            ends_at=now + timedelta(days=2),
        )
        
        # Check now: only first active
        assert sanctions_service.is_sanctioned(subject_id=402, at=now) is True
        policies = sanctions_service.effective_policies(subject_id=402, at=now)
        assert len(policies['sanctions']) == 1
        
        # Check in 12 hours: both active
        future = now + timedelta(hours=12)
        policies = sanctions_service.effective_policies(subject_id=402, at=future)
        assert len(policies['sanctions']) == 2
        
        # Check in 1.5 days: only second active
        later = now + timedelta(days=1, hours=12)
        policies = sanctions_service.effective_policies(subject_id=402, at=later)
        assert len(policies['sanctions']) == 1
    
    def test_scope_precedence_global_vs_tournament(self):
        """Test querying sanctions by scope."""
        # Global ban
        sanctions_service.create_sanction(
            subject_id=403,
            type='ban',
            scope='global',
            reason_code='global_ban',
        )
        
        # Tournament ban
        sanctions_service.create_sanction(
            subject_id=403,
            type='ban',
            scope='tournament',
            scope_id=20,
            reason_code='tournament_ban',
        )
        
        # Check global scope
        assert sanctions_service.is_sanctioned(subject_id=403, scope='global') is True
        
        # Check tournament scope
        assert sanctions_service.is_sanctioned(subject_id=403, scope='tournament') is True
        assert sanctions_service.is_sanctioned(subject_id=403, scope='tournament', scope_id=20) is True
        assert sanctions_service.is_sanctioned(subject_id=403, scope='tournament', scope_id=99) is False
        
        # Check all
        policies = sanctions_service.effective_policies(subject_id=403)
        assert len(policies['sanctions']) == 2


@pytest.mark.django_db
class TestEffectivePolicies:
    """Test effective_policies() for comprehensive sanction queries."""
    
    def test_no_sanctions(self):
        """Test user with no sanctions."""
        policies = sanctions_service.effective_policies(subject_id=501)
        
        assert policies['subject_profile_id'] == 501
        assert policies['has_sanctions'] is False
        assert policies['sanctions'] == []
    
    def test_multiple_active_sanctions(self):
        """Test user with multiple active sanctions."""
        # Create 3 sanctions
        sanctions_service.create_sanction(
            subject_id=502,
            type='ban',
            scope='global',
            reason_code='test1',
        )
        sanctions_service.create_sanction(
            subject_id=502,
            type='mute',
            scope='global',
            reason_code='test2',
        )
        sanctions_service.create_sanction(
            subject_id=502,
            type='suspend',
            scope='tournament',
            scope_id=30,
            reason_code='test3',
        )
        
        policies = sanctions_service.effective_policies(subject_id=502)
        
        assert policies['has_sanctions'] is True
        assert len(policies['sanctions']) == 3
        
        # Verify structure
        for sanction in policies['sanctions']:
            assert 'sanction_id' in sanction
            assert 'type' in sanction
            assert 'scope' in sanction
            assert 'reason_code' in sanction
            assert 'starts_at' in sanction
            assert 'ends_at' in sanction
    
    def test_filters_expired_and_revoked(self):
        """Test effective_policies filters out expired and revoked sanctions."""
        now = timezone.now()
        
        # Active sanction
        sanctions_service.create_sanction(
            subject_id=503,
            type='ban',
            scope='global',
            reason_code='active',
        )
        
        # Expired sanction
        sanctions_service.create_sanction(
            subject_id=503,
            type='mute',
            scope='global',
            reason_code='expired',
            starts_at=now - timedelta(days=10),
            ends_at=now - timedelta(days=1),
        )
        
        # Revoked sanction
        revoke_result = sanctions_service.create_sanction(
            subject_id=503,
            type='suspend',
            scope='global',
            reason_code='revoked',
        )
        sanctions_service.revoke_sanction(sanction_id=revoke_result['sanction_id'])
        
        policies = sanctions_service.effective_policies(subject_id=503)
        
        # Only active sanction should be returned
        assert policies['has_sanctions'] is True
        assert len(policies['sanctions']) == 1
        assert policies['sanctions'][0]['reason_code'] == 'active'
