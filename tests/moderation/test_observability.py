"""
Tests for moderation observability hooks.

Validates:
- Event emission when enabled
- Disabled by default (zero overhead in production)
- PII validation (reject username/email/IP)
- Payload schema correctness
"""
import pytest
from django.test import TestCase, override_settings
from apps.moderation.observability import (
    emit_gate_check,
    emit_sanction_created,
    emit_sanction_revoked,
    emit_report_triaged,
    get_emitter
)


class TestObservabilityDisabledByDefault(TestCase):
    """Verify observability is OFF by default (zero production overhead)."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_disabled_by_default_no_events(self):
        """With flag OFF (default), emit() should be no-op."""
        emit_gate_check(
            gate_type='websocket',
            user_id=123,
            allowed=False,
            reason_code='BAN',
            sanction_id=456,
            duration_ms=12.34
        )
        
        events = get_emitter().get_events()
        self.assertEqual(len(events), 0, "Events should NOT be stored when disabled")


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestGateCheckEvents(TestCase):
    """Test gate check event emission."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_emit_websocket_gate_blocked(self):
        """Emit WebSocket gate denial event."""
        emit_gate_check(
            gate_type='websocket',
            user_id=100,
            allowed=False,
            reason_code='BAN',
            sanction_id=200,
            duration_ms=15.67,
            scope='global',
            scope_id=None
        )
        
        events = get_emitter().get_events('sanction.gate_check')
        self.assertEqual(len(events), 1)
        
        payload = events[0]['payload']
        self.assertEqual(payload['gate_type'], 'websocket')
        self.assertEqual(payload['user_id'], 100)
        self.assertFalse(payload['allowed'])
        self.assertEqual(payload['reason_code'], 'BAN')
        self.assertEqual(payload['sanction_id'], 200)
        self.assertEqual(payload['duration_ms'], 15.67)
        self.assertEqual(payload['scope'], 'global')
        self.assertIsNone(payload['scope_id'])
    
    def test_emit_purchase_gate_allowed(self):
        """Emit purchase gate allowed event."""
        emit_gate_check(
            gate_type='purchase',
            user_id=300,
            allowed=True,
            reason_code=None,
            sanction_id=None,
            duration_ms=8.12,
            scope='tournament',
            scope_id=999
        )
        
        events = get_emitter().get_events('sanction.gate_check')
        self.assertEqual(len(events), 1)
        
        payload = events[0]['payload']
        self.assertEqual(payload['gate_type'], 'purchase')
        self.assertTrue(payload['allowed'])
        self.assertIsNone(payload['reason_code'])
        self.assertEqual(payload['scope'], 'tournament')
        self.assertEqual(payload['scope_id'], 999)


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestSanctionLifecycleEvents(TestCase):
    """Test sanction creation/revocation events."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_emit_sanction_created(self):
        """Emit sanction creation event."""
        emit_sanction_created(
            sanction_id=500,
            subject_profile_id=600,
            type='BAN',
            scope='global',
            scope_id=None
        )
        
        events = get_emitter().get_events('sanction.created')
        self.assertEqual(len(events), 1)
        
        payload = events[0]['payload']
        self.assertEqual(payload['sanction_id'], 500)
        self.assertEqual(payload['subject_profile_id'], 600)
        self.assertEqual(payload['type'], 'BAN')
        self.assertEqual(payload['scope'], 'global')
    
    def test_emit_sanction_revoked(self):
        """Emit sanction revocation event."""
        emit_sanction_revoked(
            sanction_id=700,
            subject_profile_id=800,
            revoked_by_id=900
        )
        
        events = get_emitter().get_events('sanction.revoked')
        self.assertEqual(len(events), 1)
        
        payload = events[0]['payload']
        self.assertEqual(payload['sanction_id'], 700)
        self.assertEqual(payload['subject_profile_id'], 800)
        self.assertEqual(payload['revoked_by_id'], 900)


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestReportTriageEvents(TestCase):
    """Test report triage event emission."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_emit_report_triaged(self):
        """Emit report triage event."""
        emit_report_triaged(
            report_id=1000,
            reporter_id=1100,
            subject_profile_id=1200,
            action_taken='BAN_APPLIED'
        )
        
        events = get_emitter().get_events('report.triaged')
        self.assertEqual(len(events), 1)
        
        payload = events[0]['payload']
        self.assertEqual(payload['report_id'], 1000)
        self.assertEqual(payload['reporter_id'], 1100)
        self.assertEqual(payload['subject_profile_id'], 1200)
        self.assertEqual(payload['action_taken'], 'BAN_APPLIED')


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestPIIValidation(TestCase):
    """Validate PII rejection in event payloads."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_reject_username_in_payload(self):
        """Emitter should reject payloads containing 'username'."""
        emitter = get_emitter()
        
        with self.assertRaises(ValueError) as ctx:
            emitter.emit('test.event', {'user_id': 123, 'username': 'badactor'})
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('username', str(ctx.exception))
    
    def test_reject_email_in_payload(self):
        """Emitter should reject payloads containing 'email'."""
        emitter = get_emitter()
        
        with self.assertRaises(ValueError) as ctx:
            emitter.emit('test.event', {'user_id': 456, 'email': 'test@example.com'})
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('email', str(ctx.exception))
    
    def test_reject_ip_in_payload(self):
        """Emitter should reject payloads containing 'ip' or 'ip_address'."""
        emitter = get_emitter()
        
        with self.assertRaises(ValueError) as ctx:
            emitter.emit('test.event', {'user_id': 789, 'ip': '192.168.1.1'})
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('ip', str(ctx.exception))
    
    def test_allow_ids_only(self):
        """Emitter should allow payloads with IDs only."""
        emitter = get_emitter()
        
        # Should NOT raise
        emitter.emit('test.event', {
            'user_id': 999,
            'sanction_id': 888,
            'reporter_id': 777,
            'type': 'BAN'
        })
        
        events = emitter.get_events('test.event')
        self.assertEqual(len(events), 1)


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestEventFiltering(TestCase):
    """Test event retrieval and filtering."""
    
    def setUp(self):
        get_emitter().clear()
    
    def test_filter_events_by_name(self):
        """Retrieve events filtered by name."""
        emit_gate_check('websocket', 1, True, None, None, 10.0)
        emit_gate_check('purchase', 2, False, 'BAN', 100, 20.0)
        emit_sanction_created(200, 3, 'MUTE', 'global', None)
        
        gate_events = get_emitter().get_events('sanction.gate_check')
        self.assertEqual(len(gate_events), 2)
        
        sanction_events = get_emitter().get_events('sanction.created')
        self.assertEqual(len(sanction_events), 1)
    
    def test_get_all_events(self):
        """Retrieve all events (no filter)."""
        emit_gate_check('websocket', 1, True, None, None, 5.0)
        emit_sanction_revoked(300, 4, 5)
        
        all_events = get_emitter().get_events()
        self.assertEqual(len(all_events), 2)


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True)
class TestSamplingRates(TestCase):
    """Test sampling rate behavior."""
    
    def setUp(self):
        get_emitter().clear()
    
    @override_settings(MODERATION_OBSERVABILITY_SAMPLE_RATE=0.0)
    def test_sampling_rate_zero_emits_none(self):
        """With rate 0.0, no events should be emitted."""
        # Attempt to emit 100 events
        for i in range(100):
            emit_gate_check('websocket', i, True, None, None, 10.0)
        
        events = get_emitter().get_events()
        self.assertEqual(len(events), 0, "Rate 0.0 should emit no events")
    
    @override_settings(MODERATION_OBSERVABILITY_SAMPLE_RATE=1.0)
    def test_sampling_rate_one_emits_all(self):
        """With rate 1.0, all events should be emitted."""
        # Emit 20 events
        for i in range(20):
            emit_gate_check('websocket', i, True, None, None, 10.0)
        
        events = get_emitter().get_events()
        self.assertEqual(len(events), 20, "Rate 1.0 should emit all events")
    
    @override_settings(MODERATION_OBSERVABILITY_SAMPLE_RATE=0.25)
    def test_sampling_rate_quarter_statistical(self):
        """With rate 0.25, ~25% of events should be emitted (±10% tolerance)."""
        # Emit 200 events for statistical significance
        total_attempts = 200
        for i in range(total_attempts):
            emit_gate_check('websocket', i, True, None, None, 10.0)
        
        events = get_emitter().get_events()
        actual_rate = len(events) / total_attempts
        
        # Expected: 0.25 ± 0.10 (i.e., 15%-35% range)
        expected = 0.25
        tolerance = 0.10
        
        self.assertGreaterEqual(
            actual_rate, expected - tolerance,
            f"Rate {actual_rate:.2f} below expected {expected - tolerance:.2f}"
        )
        self.assertLessEqual(
            actual_rate, expected + tolerance,
            f"Rate {actual_rate:.2f} above expected {expected + tolerance:.2f}"
        )


@override_settings(MODERATION_OBSERVABILITY_ENABLED=True, MODERATION_OBSERVABILITY_SAMPLE_RATE=1.0)
class TestEmitterProtocol(TestCase):
    """Test emitter protocol and test sink."""
    
    def test_test_sink_buffers_events(self):
        """TestSink should buffer events in memory."""
        from apps.moderation.observability import TestSink
        
        sink = TestSink()
        
        # Emit events
        sink.emit('test.event', {'user_id': 123, 'action': 'test'})
        sink.emit('test.event', {'user_id': 456, 'action': 'test2'})
        
        # Retrieve
        events = sink.get_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['payload']['user_id'], 123)
        self.assertEqual(events[1]['payload']['user_id'], 456)
    
    def test_test_sink_clear(self):
        """TestSink.clear() should empty buffer."""
        from apps.moderation.observability import TestSink
        
        sink = TestSink()
        sink.emit('test.event', {'user_id': 789})
        
        # Verify buffered
        self.assertEqual(len(sink.get_events()), 1)
        
        # Clear
        sink.clear()
        
        # Verify empty
        self.assertEqual(len(sink.get_events()), 0)
