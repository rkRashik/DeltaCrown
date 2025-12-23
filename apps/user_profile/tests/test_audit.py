"""
Tests for Audit Service (UP-M5)

Coverage:
- Immutability (cannot update/delete audit records)
- PII redaction (forbidden fields rejected)
- Event recording (all field types)
- Diff computation
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.user_profile.models_main import UserProfile
from apps.user_profile.models.audit import UserAuditEvent
from apps.user_profile.services.audit import AuditService

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestAuditEventImmutability:
    """Test that audit events are immutable (append-only)."""
    
    def test_cannot_update_audit_event(self):
        """Cannot update audit event after creation."""
        user = User.objects.create_user(username='testuser', email='test@test.com', password='pass123')
        
        event = AuditService.record_event(
            subject_user_id=user.id,
            event_type=UserAuditEvent.EventType.PROFILE_CREATED,
            source_app='user_profile',
            object_type='UserProfile',
            object_id=1
        )
        
        with pytest.raises(ValidationError, match="immutable"):
            event.event_type = UserAuditEvent.EventType.PROFILE_UPDATED
            event.save()
    
    def test_cannot_delete_audit_event(self):
        """Cannot delete audit events."""
        user = User.objects.create_user(username='testuser2', email='test2@test.com', password='pass123')
        
        event = AuditService.record_event(
            subject_user_id=user.id,
            event_type=UserAuditEvent.EventType.PROFILE_CREATED,
            source_app='user_profile',
            object_type='UserProfile',
            object_id=1
        )
        
        with pytest.raises(ValidationError, match="immutable"):
            event.delete()


@pytest.mark.django_db(transaction=True)
class TestPIIRedaction:
    """Test PII/secret redaction in snapshots."""
    
    def test_forbids_email_in_snapshot(self):
        """Email cannot be stored in snapshots."""
        user = User.objects.create_user(username='redacttest', email='redact@test.com', password='pass123')
        
        with pytest.raises(ValueError, match="Forbidden fields.*email"):
            AuditService.record_event(
                subject_user_id=user.id,
                event_type=UserAuditEvent.EventType.PROFILE_UPDATED,
                source_app='user_profile',
                object_type='UserProfile',
                object_id=1,
                after_snapshot={'email': 'test@example.com', 'public_id': 'DC-25-000001'}
            )
    
    def test_forbids_password_in_snapshot(self):
        """Password cannot be stored in snapshots."""
        user = User.objects.create_user(username='pwtest', email='pw@test.com', password='pass123')
        
        with pytest.raises(ValueError, match="Forbidden fields.*password"):
            AuditService.record_event(
                subject_user_id=user.id,
                event_type=UserAuditEvent.EventType.PROFILE_UPDATED,
                source_app='user_profile',
                object_type='UserProfile',
                object_id=1,
                after_snapshot={'password': 'secret123', 'public_id': 'DC-25-000001'}
            )
    
    def test_forbids_oauth_token_in_snapshot(self):
        """OAuth tokens cannot be stored in snapshots."""
        user = User.objects.create_user(username='oauth', email='oauth@test.com', password='pass123')
        
        with pytest.raises(ValueError, match="Forbidden fields.*oauth_token"):
            AuditService.record_event(
                subject_user_id=user.id,
                event_type=UserAuditEvent.EventType.PROFILE_UPDATED,
                source_app='user_profile',
                object_type='UserProfile',
                object_id=1,
                after_snapshot={'oauth_token': 'secret_token', 'public_id': 'DC-25-000001'}
            )
    
    def test_allows_safe_fields(self):
        """Safe fields (public_id, stats, etc.) are allowed."""
        user = User.objects.create_user(username='safetest', email='safe@test.com', password='pass123')
        
        event = AuditService.record_event(
            subject_user_id=user.id,
            event_type=UserAuditEvent.EventType.PUBLIC_ID_ASSIGNED,
            source_app='user_profile',
            object_type='UserProfile',
            object_id=1,
            after_snapshot={
                'public_id': 'DC-25-000042',
                'deltacoin_balance': '100.00',
                'tournaments_won': 5
            }
        )
        
        assert event.after_snapshot['public_id'] == 'DC-25-000042'
        assert event.after_snapshot['deltacoin_balance'] == '100.00'


@pytest.mark.django_db(transaction=True)
class TestAuditEventRecording:
    """Test audit event recording."""
    
    def test_record_system_event(self):
        """System events have no actor_user."""
        user = User.objects.create_user(username='sysuser', email='sys@test.com', password='pass123')
        
        event = AuditService.record_event(
            subject_user_id=user.id,
            event_type=UserAuditEvent.EventType.SYSTEM_RECONCILE,
            source_app='user_profile',
            object_type='UserProfileStats',
            object_id=1,
            metadata={'command': 'recompute_user_stats'}
        )
        
        assert event.actor_user is None
        assert event.subject_user_id == user.id
        assert event.event_type == UserAuditEvent.EventType.SYSTEM_RECONCILE
    
    def test_record_user_action(self):
        """User actions have actor_user set."""
        actor = User.objects.create_user(username='actor', email='actor@test.com', password='pass123')
        subject = User.objects.create_user(username='subject', email='subject@test.com', password='pass123')
        
        event = AuditService.record_event(
            actor_user_id=actor.id,
            subject_user_id=subject.id,
            event_type=UserAuditEvent.EventType.ADMIN_OVERRIDE,
            source_app='user_profile',
            object_type='UserProfile',
            object_id=1,
            metadata={'reason': 'manual correction'}
        )
        
        assert event.actor_user_id == actor.id
        assert event.subject_user_id == subject.id
    
    def test_record_with_snapshots(self):
        """Events can have before/after snapshots."""
        user = User.objects.create_user(username='snapuser', email='snap@test.com', password='pass123')
        
        event = AuditService.record_event(
            subject_user_id=user.id,
            event_type=UserAuditEvent.EventType.ECONOMY_DRIFT_CORRECTED,
            source_app='economy',
            object_type='UserProfile',
            object_id=1,
            before_snapshot={'deltacoin_balance': '100.00'},
            after_snapshot={'deltacoin_balance': '250.00'},
            metadata={'drift_amount': '150.00'}
        )
        
        assert event.before_snapshot['deltacoin_balance'] == '100.00'
        assert event.after_snapshot['deltacoin_balance'] == '250.00'


@pytest.mark.django_db(transaction=True)
class TestDiffComputation:
    """Test snapshot diff computation."""
    
    def test_diff_with_changes(self):
        """Compute diff when fields changed."""
        before = {'balance': 100, 'tournaments': 5}
        after = {'balance': 250, 'tournaments': 6}
        
        diff = AuditService.compute_diff(before, after)
        
        assert diff['added'] == {}
        assert diff['removed'] == {}
        assert diff['changed'] == {
            'balance': (100, 250),
            'tournaments': (5, 6)
        }
    
    def test_diff_with_additions(self):
        """Compute diff when fields added."""
        before = {'balance': 100}
        after = {'balance': 100, 'public_id': 'DC-25-000001'}
        
        diff = AuditService.compute_diff(before, after)
        
        assert diff['added'] == {'public_id': 'DC-25-000001'}
        assert diff['changed'] == {}
    
    def test_diff_with_removals(self):
        """Compute diff when fields removed."""
        before = {'balance': 100, 'old_field': 'value'}
        after = {'balance': 100}
        
        diff = AuditService.compute_diff(before, after)
        
        assert diff['removed'] == {'old_field': 'value'}
        assert diff['changed'] == {}
