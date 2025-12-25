"""
Tests for Tournament ↔ User Profile Integration

Verifies:
1. Feature flag OFF => no integration calls (no DB writes)
2. Feature flag ON => activity/audit events created with correct payloads
3. Idempotency => duplicate calls don't create duplicate records
4. Stats recompute => TournamentStatsService called with correct user_ids

Reference: Documents/UserProfile_CommandCenter_v1/03_Planning/UP_TOURNAMENT_INTEGRATION_CONTRACT.md
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.user_profile.integrations.tournaments import (
    on_registration_status_change,
    on_checkin_toggled,
    on_match_result_submitted,
    on_match_finalized,
    on_tournament_completed,
    on_dispute_opened,
    on_dispute_resolved,
    on_payment_status_change,
)
from apps.user_profile.models import UserActivity, UserAuditEvent

User = get_user_model()


@pytest.mark.django_db
class TestTournamentIntegrationFlagOff(TestCase):
    """Test that integration is disabled when flag is OFF."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='test_player',
            email='player@test.com',
            password='testpass123'
        )
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=False)
    def test_flag_off_no_activity_events(self):
        """Verify no activity events created when flag OFF."""
        initial_count = UserActivity.objects.count()
        
        # Call various integration functions
        on_registration_status_change(
            user_id=self.user.id,
            tournament_id=1,
            registration_id=1,
            status='submitted',
        )
        
        on_match_result_submitted(
            user_id=self.user.id,
            match_id=1,
            tournament_id=1,
            submission_id=1,
            status='pending_opponent',
        )
        
        # Verify no new activity events
        self.assertEqual(UserActivity.objects.count(), initial_count)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=False)
    def test_flag_off_no_audit_events(self):
        """Verify no audit events created when flag OFF."""
        initial_count = UserAuditEvent.objects.count()
        
        # Call integration function that normally creates audit event
        on_registration_status_change(
            user_id=self.user.id,
            tournament_id=1,
            registration_id=1,
            status='approved',
            actor_user_id=self.user.id,
        )
        
        # Verify no new audit events
        self.assertEqual(UserAuditEvent.objects.count(), initial_count)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=False)
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_flag_off_no_stats_recompute(self, mock_recompute):
        """Verify stats recompute not called when flag OFF."""
        on_match_finalized(
            match_id=1,
            tournament_id=1,
            winner_id=1,
            loser_id=2,
            winner_user_ids=[self.user.id],
            loser_user_ids=[],
        )
        
        # Verify recompute never called
        mock_recompute.assert_not_called()


@pytest.mark.django_db
class TestTournamentIntegrationFlagOn(TestCase):
    """Test that integration works correctly when flag is ON."""
    
    def setUp(self):
        """Create test users."""
        self.user1 = User.objects.create_user(
            username='player1',
            email='player1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='testpass123'
        )
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    def test_registration_submitted_creates_activity(self, mock_record):
        """Verify registration submission creates activity event."""
        on_registration_status_change(
            user_id=self.user1.id,
            tournament_id=1,
            registration_id=1,
            status='submitted',
        )
        
        # Verify _record_activity called with correct payload
        mock_record.assert_called_once()
        call_args = mock_record.call_args
        self.assertEqual(call_args.kwargs['user_id'], self.user1.id)
        self.assertEqual(call_args.kwargs['event_type'], 'tournament.registration.submitted')
        self.assertEqual(call_args.kwargs['metadata']['tournament_id'], 1)
        self.assertEqual(call_args.kwargs['metadata']['registration_id'], 1)
        self.assertIn('idempotency_key', call_args.kwargs)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    def test_registration_approved_creates_audit(self, mock_audit, mock_activity):
        """Verify organizer approval creates audit event."""
        with self.captureOnCommitCallbacks(execute=True):
            on_registration_status_change(
                user_id=self.user1.id,
                tournament_id=1,
                registration_id=1,
                status='approved',
                actor_user_id=self.organizer.id,
            )
        
        # Verify both activity (immediate) and audit (deferred) created
        mock_activity.assert_called_once()
        mock_audit.assert_called_once()
        
        # Verify audit event details
        audit_call = mock_audit.call_args
        self.assertEqual(audit_call.kwargs['subject_user_id'], self.user1.id)
        self.assertEqual(audit_call.kwargs['event_type'], 'registration_approved')
        self.assertEqual(audit_call.kwargs['actor_user_id'], self.organizer.id)
        self.assertEqual(audit_call.kwargs['object_type'], 'Registration')
        self.assertEqual(audit_call.kwargs['object_id'], 1)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    def test_checkin_toggled_creates_both_events(self, mock_audit, mock_activity):
        """Verify check-in toggle creates activity + audit events."""
        with self.captureOnCommitCallbacks(execute=True):
            on_checkin_toggled(
                user_id=self.user1.id,
                tournament_id=1,
                registration_id=1,
                checked_in=True,
                actor_user_id=self.organizer.id,
            )
        
        # Verify both events created (activity immediate, audit deferred)
        mock_activity.assert_called_once()
        mock_audit.assert_called_once()
        
        # Verify activity event
        activity_call = mock_activity.call_args
        self.assertEqual(activity_call.kwargs['event_type'], 'tournament.checkin.checked_in')
        
        # Verify audit event
        audit_call = mock_audit.call_args
        self.assertEqual(audit_call.kwargs['event_type'], 'checkin_toggled')
        self.assertEqual(audit_call.kwargs['after_snapshot']['checked_in'], True)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_match_finalized_triggers_stats_recompute(self, mock_recompute, mock_activity):
        """Verify match finalization triggers stats recompute for all participants."""
        with self.captureOnCommitCallbacks(execute=True):
            on_match_finalized(
                match_id=1,
                tournament_id=1,
                winner_id=1,
                loser_id=2,
                winner_user_ids=[self.user1.id],
                loser_user_ids=[self.user2.id],
            )
        
        # Verify activity event for both users (immediate)
        self.assertEqual(mock_activity.call_count, 2)
        
        # Verify stats recompute called for both users (deferred via on_commit)
        self.assertEqual(mock_recompute.call_count, 2)
        recompute_calls = [call.args[0] for call in mock_recompute.call_args_list]
        self.assertIn(self.user1.id, recompute_calls)
        self.assertIn(self.user2.id, recompute_calls)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_tournament_completed_bulk_operations(self, mock_recompute, mock_audit, mock_activity):
        """Verify tournament completion creates events for all participants."""
        participant_ids = [self.user1.id, self.user2.id]
        winner_ids = [self.user1.id]
        
        with self.captureOnCommitCallbacks(execute=True):
            on_tournament_completed(
                tournament_id=1,
                actor_user_id=self.organizer.id,
                participant_user_ids=participant_ids,
                winner_user_ids=winner_ids,
                top3_user_ids=winner_ids,
            )
        
        # Verify activity event for all participants (immediate)
        self.assertEqual(mock_activity.call_count, 2)
        
        # Verify audit event (organizer action, deferred)
        mock_audit.assert_called_once()
        audit_call = mock_audit.call_args
        self.assertEqual(audit_call.kwargs['event_type'], 'tournament_completed')
        self.assertEqual(audit_call.kwargs['actor_user_id'], self.organizer.id)
        
        # Verify stats recompute for all participants (deferred)
        self.assertEqual(mock_recompute.call_count, 2)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    def test_dispute_opened_creates_activity(self, mock_activity):
        """Verify dispute opening creates activity event."""
        on_dispute_opened(
            user_id=self.user1.id,
            match_id=1,
            tournament_id=1,
            dispute_id=1,
            submission_id=1,
            reason_code='incorrect_score',
        )
        
        # Verify activity event
        mock_activity.assert_called_once()
        call_args = mock_activity.call_args
        self.assertEqual(call_args.kwargs['event_type'], 'tournament.dispute.opened')
        self.assertEqual(call_args.kwargs['metadata']['dispute_id'], 1)
        self.assertEqual(call_args.kwargs['metadata']['reason_code'], 'incorrect_score')
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_dispute_resolved_with_finalization(self, mock_recompute, mock_audit):
        """Verify dispute resolution with finalization triggers stats recompute."""
        with self.captureOnCommitCallbacks(execute=True):
            on_dispute_resolved(
                match_id=1,
                tournament_id=1,
                dispute_id=1,
                resolution_type='approve_original',
                actor_user_id=self.organizer.id,
                winner_user_ids=[self.user1.id],
                loser_user_ids=[self.user2.id],
            )
        
        # Verify audit event (deferred)
        mock_audit.assert_called_once()
        audit_call = mock_audit.call_args
        self.assertEqual(audit_call.kwargs['event_type'], 'dispute_resolved')
        self.assertEqual(audit_call.kwargs['after_snapshot']['resolution_type'], 'approve_original')
        
        # Verify stats recompute for both users (deferred)
        self.assertEqual(mock_recompute.call_count, 2)
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_dispute_dismissed_no_stats_recompute(self, mock_recompute, mock_audit):
        """Verify dismissed dispute does NOT trigger stats recompute."""
        with self.captureOnCommitCallbacks(execute=True):
            on_dispute_resolved(
                match_id=1,
                tournament_id=1,
                dispute_id=1,
                resolution_type='dismiss_dispute',
                actor_user_id=self.organizer.id,
            )
        
        # Verify audit event created (deferred)
        mock_audit.assert_called_once()
        
        # Verify NO stats recompute (dispute dismissed)
        mock_recompute.assert_not_called()
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    def test_payment_verified_creates_both_events(self, mock_audit, mock_activity):
        """Verify payment verification creates activity + audit events."""
        with self.captureOnCommitCallbacks(execute=True):
            on_payment_status_change(
                user_id=self.user1.id,
                tournament_id=1,
                transaction_id='TXN123',
                registration_id=1,
                status='verified',
                actor_user_id=self.organizer.id,
                amount=Decimal('50.00'),
            )
        
        # Verify both events (activity immediate, audit deferred)
        mock_activity.assert_called_once()
        mock_audit.assert_called_once()
        
        # Verify activity event
        activity_call = mock_activity.call_args
        self.assertEqual(activity_call.kwargs['event_type'], 'tournament.payment.verified')
        self.assertEqual(activity_call.kwargs['metadata']['transaction_id'], 'TXN123')
        
        # Verify audit event
        audit_call = mock_audit.call_args
        self.assertEqual(audit_call.kwargs['event_type'], 'payment_verified')
        self.assertEqual(audit_call.kwargs['after_snapshot']['amount'], '50.00')


@pytest.mark.django_db
class TestIntegrationIdempotency(TestCase):
    """Test idempotency of integration calls."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='test_player',
            email='player@test.com',
            password='testpass123'
        )
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    def test_idempotency_key_generated(self, mock_activity):
        """Verify idempotency key is generated for activity events."""
        on_registration_status_change(
            user_id=self.user.id,
            tournament_id=1,
            registration_id=1,
            status='submitted',
        )
        
        # Verify idempotency_key was passed
        call_args = mock_activity.call_args
        self.assertIn('idempotency_key', call_args.kwargs)
        idempotency_key = call_args.kwargs['idempotency_key']
        
        # Verify format: registration_status:1:submitted (deterministic, no timestamp)
        self.assertEqual(idempotency_key, 'registration_status:1:submitted')
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    @patch('apps.user_profile.integrations.tournaments.AuditService.record_event')
    def test_audit_idempotency_key_matches_activity(self, mock_audit, mock_activity):
        """Verify audit and activity use same idempotency key."""
        with self.captureOnCommitCallbacks(execute=True):
            on_registration_status_change(
                user_id=self.user.id,
                tournament_id=1,
                registration_id=1,
                status='approved',
                actor_user_id=self.user.id,
            )
        
        # Get idempotency keys from both calls (audit deferred via on_commit)
        activity_key = mock_activity.call_args.kwargs['idempotency_key']
        audit_key = mock_audit.call_args.kwargs['idempotency_key']
        
        # Verify they match (same event, same deduplication)
        self.assertEqual(activity_key, audit_key)


@pytest.mark.django_db
class TestIntegrationErrorHandling(TestCase):
    """Test that integration errors don't break tournament operations."""
    
    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='test_player',
            email='player@test.com',
            password='testpass123'
        )
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments._record_activity')
    def test_activity_error_caught_and_logged(self, mock_activity):
        """Verify activity service errors are caught (don't propagate)."""
        # Make ActivityService raise exception
        mock_activity.side_effect = Exception('Database error')
        
        # Call integration function - should NOT raise
        try:
            on_registration_status_change(
                user_id=self.user.id,
                tournament_id=1,
                registration_id=1,
                status='submitted',
            )
        except Exception:
            self.fail("Integration error should be caught, not propagated")
    
    @override_settings(USER_PROFILE_INTEGRATION_ENABLED=True)
    @patch('apps.user_profile.integrations.tournaments.TournamentStatsService.recompute_user_stats')
    def test_stats_recompute_error_caught(self, mock_recompute):
        """Verify stats recompute errors are caught per-user."""
        # Make recompute fail for one user
        def recompute_side_effect(user_id):
            if user_id == self.user.id:
                raise Exception('Stats computation error')
        
        mock_recompute.side_effect = recompute_side_effect
        
        # Call with multiple users - should not raise (deferred execution)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                on_match_finalized(
                    match_id=1,
                    tournament_id=1,
                    winner_id=1,
                    loser_id=2,
                    winner_user_ids=[self.user.id, 999],  # 999 doesn't exist
                    loser_user_ids=[],
                )
        except Exception:
            self.fail("Stats recompute error should be caught per-user")
        
        # Verify recompute was attempted for both users (via on_commit)
        self.assertEqual(mock_recompute.call_count, 2)
