"""
Test Audit & Reports Service - Phase 8 Module 8.2

Tests for file_report, triage_report, and list_audit_events.

Coverage:
- File reports (5 tests): basic, idempotency, replay, invalid params, concurrent
- Triage reports (5 tests): valid transitions, invalid transitions, audit trail
- List audit events (5 tests): filters, pagination, empty results
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.moderation.services import reports_service, audit_service, sanctions_service
from apps.moderation.models import AbuseReport, ModerationAudit


@pytest.mark.django_db
class TestFileReport:
    """Test file_report() with idempotency and validation."""
    
    def test_file_basic_report(self):
        """Test basic report filing."""
        result = reports_service.file_report(
            reporter_id=1001,
            category='harassment',
            ref_type='chat_message',
            ref_id=500,
            priority=3,
        )
        
        assert result['created'] is True
        assert result['reporter_profile_id'] == 1001
        assert result['category'] == 'harassment'
        assert result['ref_type'] == 'chat_message'
        assert result['ref_id'] == 500
        assert result['state'] == 'open'
        assert result['priority'] == 3
        
        # Verify database
        report = AbuseReport.objects.get(id=result['report_id'])
        assert report.reporter_profile_id == 1001
        assert report.state == 'open'
        
        # Verify audit trail
        audit = ModerationAudit.objects.filter(
            ref_type='report',
            ref_id=report.id,
            event='report_filed'
        ).first()
        assert audit is not None
        assert audit.actor_id == 1001
    
    def test_file_report_with_idempotency_key(self):
        """Test report filing with idempotency key."""
        result = reports_service.file_report(
            reporter_id=1002,
            category='cheating',
            ref_type='match',
            ref_id=100,
            idempotency_key='report_key_001',
        )
        
        assert result['created'] is True
        
        # Verify key stored
        report = AbuseReport.objects.get(id=result['report_id'])
        assert report.idempotency_key == 'report_key_001'
    
    def test_replay_report_with_idempotency_key(self):
        """Test replaying report with same idempotency key."""
        # First filing
        result1 = reports_service.file_report(
            reporter_id=1003,
            category='spam',
            ref_type='profile',
            ref_id=200,
            priority=2,
            idempotency_key='report_key_002',
        )
        assert result1['created'] is True
        original_id = result1['report_id']
        
        # Replay with same key
        result2 = reports_service.file_report(
            reporter_id=9999,  # Different reporter
            category='different',
            ref_type='different',
            ref_id=999,
            priority=5,
            idempotency_key='report_key_002',  # Same key
        )
        
        assert result2['created'] is False
        assert result2['report_id'] == original_id
        assert result2['reporter_profile_id'] == 1003  # Original
        assert result2['category'] == 'spam'  # Original
        assert result2['priority'] == 2  # Original
        
        # Verify only one report
        assert AbuseReport.objects.filter(idempotency_key='report_key_002').count() == 1
    
    def test_invalid_parameters(self):
        """Test validation of invalid parameters."""
        # Missing reporter_id
        with pytest.raises(ValueError, match="reporter_id is required"):
            reports_service.file_report(
                reporter_id=None,
                category='test',
                ref_type='test',
                ref_id=1,
            )
        
        # Missing category
        with pytest.raises(ValueError, match="category is required"):
            reports_service.file_report(
                reporter_id=1004,
                category=None,
                ref_type='test',
                ref_id=1,
            )
        
        # Missing ref_type
        with pytest.raises(ValueError, match="ref_type is required"):
            reports_service.file_report(
                reporter_id=1004,
                category='test',
                ref_type=None,
                ref_id=1,
            )
        
        # Missing ref_id
        with pytest.raises(ValueError, match="ref_id is required"):
            reports_service.file_report(
                reporter_id=1004,
                category='test',
                ref_type='test',
                ref_id=None,
            )
        
        # Invalid priority (too low)
        with pytest.raises(ValueError, match="priority must be between 0 and 5"):
            reports_service.file_report(
                reporter_id=1004,
                category='test',
                ref_type='test',
                ref_id=1,
                priority=-1,
            )
        
        # Invalid priority (too high)
        with pytest.raises(ValueError, match="priority must be between 0 and 5"):
            reports_service.file_report(
                reporter_id=1004,
                category='test',
                ref_type='test',
                ref_id=1,
                priority=6,
            )
    
    def test_unique_report_idempotency_key_constraint(self):
        """Test database enforces unique report idempotency key constraint."""
        # File first report
        reports_service.file_report(
            reporter_id=1005,
            category='test',
            ref_type='test',
            ref_id=300,
            idempotency_key='unique_report_key',
        )
        
        # Try to file second with different data but same key
        # Should return existing (idempotency)
        result = reports_service.file_report(
            reporter_id=9999,
            category='different',
            ref_type='different',
            ref_id=999,
            idempotency_key='unique_report_key',  # Same key
        )
        
        assert result['created'] is False
        assert result['reporter_profile_id'] == 1005  # Original
        
        # Verify only one report
        assert AbuseReport.objects.filter(idempotency_key='unique_report_key').count() == 1


@pytest.mark.django_db
class TestTriageReport:
    """Test triage_report() state transitions."""
    
    def test_valid_transition_open_to_triaged(self):
        """Test valid transition: open → triaged."""
        # File report
        file_result = reports_service.file_report(
            reporter_id=2001,
            category='test',
            ref_type='test',
            ref_id=1,
        )
        report_id = file_result['report_id']
        
        # Triage: open → triaged
        triage_result = reports_service.triage_report(
            report_id=report_id,
            new_state='triaged',
            actor_id=9000,
        )
        
        assert triage_result['transitioned'] is True
        assert triage_result['old_state'] == 'open'
        assert triage_result['new_state'] == 'triaged'
        
        # Verify database
        report = AbuseReport.objects.get(id=report_id)
        assert report.state == 'triaged'
        
        # Verify audit trail
        audit = ModerationAudit.objects.filter(
            ref_type='report',
            ref_id=report_id,
            event='report_triaged'
        ).last()
        assert audit is not None
        assert audit.actor_id == 9000
        assert audit.meta['old_state'] == 'open'
        assert audit.meta['new_state'] == 'triaged'
    
    def test_valid_transition_triaged_to_resolved(self):
        """Test valid transition: triaged → resolved."""
        # File and triage
        file_result = reports_service.file_report(
            reporter_id=2002,
            category='test',
            ref_type='test',
            ref_id=2,
        )
        report_id = file_result['report_id']
        
        reports_service.triage_report(
            report_id=report_id,
            new_state='triaged',
            actor_id=9000,
        )
        
        # Resolve
        resolve_result = reports_service.triage_report(
            report_id=report_id,
            new_state='resolved',
            actor_id=9001,
        )
        
        assert resolve_result['transitioned'] is True
        assert resolve_result['old_state'] == 'triaged'
        assert resolve_result['new_state'] == 'resolved'
        
        # Verify database
        report = AbuseReport.objects.get(id=report_id)
        assert report.state == 'resolved'
    
    def test_valid_transition_triaged_to_rejected(self):
        """Test valid transition: triaged → rejected."""
        # File and triage
        file_result = reports_service.file_report(
            reporter_id=2003,
            category='test',
            ref_type='test',
            ref_id=3,
        )
        report_id = file_result['report_id']
        
        reports_service.triage_report(
            report_id=report_id,
            new_state='triaged',
            actor_id=9000,
        )
        
        # Reject
        reject_result = reports_service.triage_report(
            report_id=report_id,
            new_state='rejected',
            actor_id=9001,
        )
        
        assert reject_result['transitioned'] is True
        assert reject_result['old_state'] == 'triaged'
        assert reject_result['new_state'] == 'rejected'
        
        # Verify database
        report = AbuseReport.objects.get(id=report_id)
        assert report.state == 'rejected'
    
    def test_invalid_transition_triaged_to_open(self):
        """Test invalid transition: triaged → open (no reverse)."""
        # File and triage
        file_result = reports_service.file_report(
            reporter_id=2004,
            category='test',
            ref_type='test',
            ref_id=4,
        )
        report_id = file_result['report_id']
        
        reports_service.triage_report(
            report_id=report_id,
            new_state='triaged',
            actor_id=9000,
        )
        
        # Try invalid transition back to open
        with pytest.raises(ValueError, match="Invalid transition"):
            reports_service.triage_report(
                report_id=report_id,
                new_state='open',
                actor_id=9001,
            )
        
        # State should remain triaged
        report = AbuseReport.objects.get(id=report_id)
        assert report.state == 'triaged'
    
    def test_invalid_transition_resolved_to_triaged(self):
        """Test invalid transition from terminal state: resolved → triaged."""
        # File, triage, resolve
        file_result = reports_service.file_report(
            reporter_id=2005,
            category='test',
            ref_type='test',
            ref_id=5,
        )
        report_id = file_result['report_id']
        
        reports_service.triage_report(
            report_id=report_id,
            new_state='triaged',
            actor_id=9000,
        )
        reports_service.triage_report(
            report_id=report_id,
            new_state='resolved',
            actor_id=9001,
        )
        
        # Try transition from terminal state
        with pytest.raises(ValueError, match="Invalid transition"):
            reports_service.triage_report(
                report_id=report_id,
                new_state='triaged',
                actor_id=9002,
            )
        
        # State should remain resolved
        report = AbuseReport.objects.get(id=report_id)
        assert report.state == 'resolved'
    
    def test_triage_nonexistent_report(self):
        """Test triaging non-existent report raises error."""
        with pytest.raises(ValueError, match="Report 99999 not found"):
            reports_service.triage_report(
                report_id=99999,
                new_state='triaged',
                actor_id=9000,
            )


@pytest.mark.django_db
class TestListAuditEvents:
    """Test list_audit_events() filtering and pagination."""
    
    def test_list_all_events(self):
        """Test listing all audit events."""
        # Create some sanctions (generates audit events)
        sanctions_service.create_sanction(
            subject_id=3001,
            type='ban',
            scope='global',
            reason_code='test1',
            issued_by=9000,
        )
        sanctions_service.create_sanction(
            subject_id=3002,
            type='mute',
            scope='global',
            reason_code='test2',
            issued_by=9001,
        )
        
        result = audit_service.list_audit_events()
        
        assert result['count'] >= 2
        assert result['limit'] == 100
        assert result['offset'] == 0
        assert len(result['events']) >= 2
        
        # Verify structure
        for event in result['events']:
            assert 'id' in event
            assert 'event' in event
            assert 'ref_type' in event
            assert 'ref_id' in event
            assert 'created_at' in event
    
    def test_filter_by_ref_type(self):
        """Test filtering by ref_type."""
        # Create sanction and report (different ref_types)
        sanctions_service.create_sanction(
            subject_id=3003,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=9000,
        )
        reports_service.file_report(
            reporter_id=3004,
            category='test',
            ref_type='test',
            ref_id=1,
        )
        
        # Filter for sanctions only
        result = audit_service.list_audit_events(ref_type='sanction')
        assert result['count'] >= 1
        assert all(e['ref_type'] == 'sanction' for e in result['events'])
        
        # Filter for reports only
        result = audit_service.list_audit_events(ref_type='report')
        assert result['count'] >= 1
        assert all(e['ref_type'] == 'report' for e in result['events'])
    
    def test_filter_by_ref_id(self):
        """Test filtering by ref_id."""
        # Create sanction
        create_result = sanctions_service.create_sanction(
            subject_id=3005,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=9000,
        )
        sanction_id = create_result['sanction_id']
        
        # Filter by sanction ID
        result = audit_service.list_audit_events(ref_type='sanction', ref_id=sanction_id)
        assert result['count'] == 1
        assert result['events'][0]['ref_id'] == sanction_id
    
    def test_filter_by_actor(self):
        """Test filtering by actor_id."""
        # Create sanctions with different actors
        sanctions_service.create_sanction(
            subject_id=3006,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=8000,
        )
        sanctions_service.create_sanction(
            subject_id=3007,
            type='mute',
            scope='global',
            reason_code='test',
            issued_by=8001,
        )
        
        # Filter by actor 8000
        result = audit_service.list_audit_events(actor_id=8000)
        assert result['count'] >= 1
        assert all(e['actor_id'] == 8000 for e in result['events'])
    
    def test_filter_by_time_window(self):
        """Test filtering by time window (since/until)."""
        now = timezone.now()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)
        
        # Create sanction (creates audit event with current time)
        sanctions_service.create_sanction(
            subject_id=3008,
            type='ban',
            scope='global',
            reason_code='test',
            issued_by=9000,
        )
        
        # Query events since 1 hour ago
        result = audit_service.list_audit_events(since=past)
        assert result['count'] >= 1
        
        # Query events until 1 hour from now (should include current)
        result = audit_service.list_audit_events(until=future)
        assert result['count'] >= 1
        
        # Query events in narrow window around now
        result = audit_service.list_audit_events(since=past, until=future)
        assert result['count'] >= 1
    
    def test_pagination(self):
        """Test pagination with limit and offset."""
        # Create 10 sanctions (10 audit events)
        for i in range(10):
            sanctions_service.create_sanction(
                subject_id=4000 + i,
                type='ban',
                scope='global',
                reason_code=f'test_{i}',
                issued_by=9000,
            )
        
        # First page: limit 3
        page1 = audit_service.list_audit_events(limit=3, offset=0)
        assert page1['limit'] == 3
        assert page1['offset'] == 0
        assert len(page1['events']) == 3
        
        # Second page: limit 3, offset 3
        page2 = audit_service.list_audit_events(limit=3, offset=3)
        assert page2['limit'] == 3
        assert page2['offset'] == 3
        assert len(page2['events']) == 3
        
        # Verify different results
        page1_ids = {e['id'] for e in page1['events']}
        page2_ids = {e['id'] for e in page2['events']}
        assert page1_ids.isdisjoint(page2_ids)  # No overlap
    
    def test_empty_results(self):
        """Test querying with no matching events."""
        result = audit_service.list_audit_events(ref_type='nonexistent_type')
        
        assert result['count'] == 0
        assert result['events'] == []
