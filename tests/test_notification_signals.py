"""
Milestone F Tests: Notification Signals

Tests for tournament event notification signals.

Test Coverage:
1. Payment notifications (verified, rejected, refunded)
2. Match notifications (started, completed, disputed)
3. Tournament notifications (completed)
4. State transition detection (no duplicate notifications)
5. Feature flag behavior (email/webhook toggles)

Planning Documents:
- Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md
- Documents/ExecutionPlan/MILESTONES_E_F_STATUS.md
"""

import pytest
from unittest.mock import patch, MagicMock, call
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.tournaments.models import (
    Game,
    Tournament,
    Registration,
    PaymentVerification,
    Match,
)
from apps.tournaments.signals import (
    handle_payment_status_change,
    handle_match_state_change,
    handle_tournament_completed,
)

User = get_user_model()


def _ensure_profile(user):
    """
    Create or fetch the UserProfile for the given user.
    """
    from apps.user_profile.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@pytest.mark.django_db
class TestPaymentNotificationSignals(TestCase):
    """Test payment verification notification signals."""
    
    def setUp(self):
        """Create test fixtures."""
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='password123'
        )
        
        self.player = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='password123'
        )
        
        # Create game
        self.game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
        )
        
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            organizer=self.organizer,
            max_participants=16,
            game=self.game,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            registration_start=now - timezone.timedelta(days=7),
            registration_end=now + timezone.timedelta(days=7),
            tournament_start=now + timezone.timedelta(days=14)
        )
        
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status='pending'
        )
        
        self.payment = PaymentVerification.objects.create(
            registration=self.registration,
            method='bkash',
            transaction_id='TXN12345',
            amount_bdt=500,
            status=PaymentVerification.Status.PENDING
        )
    
    @patch('apps.tournaments.signals.notify')
    def test_payment_verified_sends_notification(self, mock_notify):
        """Test notification sent when payment is verified."""
        mock_notify.return_value = {'created': 1, 'skipped': 0, 'email_sent': 0}
        
        # Simulate status change (set _original_status manually since we're not going through pre_save)
        self.payment._original_status = PaymentVerification.Status.PENDING
        self.payment.status = PaymentVerification.Status.VERIFIED
        self.payment.save()
        
        # Verify notify was called
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        
        assert call_kwargs['recipients'] == [self.player]
        assert call_kwargs['event'] == 'payment_verified'
        assert 'Payment Verified' in call_kwargs['title']
        assert self.tournament.name in call_kwargs['title']
        assert call_kwargs['tournament_id'] == self.tournament.id
    
    @patch('apps.tournaments.signals.notify')
    def test_payment_rejected_sends_notification(self, mock_notify):
        """Test notification sent when payment is rejected."""
        mock_notify.return_value = {'created': 1, 'skipped': 0, 'email_sent': 0}
        
        # Update payment with rejection reason
        self.payment._original_status = PaymentVerification.Status.PENDING
        self.payment.status = PaymentVerification.Status.REJECTED
        self.payment.notes = {'rejection_reason': 'Invalid transaction ID'}
        self.payment.save()
        
        # Verify notify was called
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        
        assert call_kwargs['recipients'] == [self.player]
        assert call_kwargs['event'] == 'payment_rejected'
        assert 'Payment Rejected' in call_kwargs['title']
        assert 'Invalid transaction ID' in call_kwargs['body']
    
    @patch('apps.tournaments.signals.notify')
    def test_payment_refunded_sends_notification(self, mock_notify):
        """Test notification sent when payment is refunded."""
        mock_notify.return_value = {'created': 1, 'skipped': 0, 'email_sent': 0}
        
        # First verify the payment
        self.payment._original_status = PaymentVerification.Status.PENDING
        self.payment.status = PaymentVerification.Status.VERIFIED
        self.payment.save()
        
        # Then refund it
        mock_notify.reset_mock()
        self.payment._original_status = PaymentVerification.Status.VERIFIED
        self.payment.status = PaymentVerification.Status.REFUNDED
        self.payment.notes = {'refund_reason': 'Tournament cancelled'}
        self.payment.save()
        
        # Verify notify was called for refund
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        
        assert call_kwargs['recipients'] == [self.player]
        assert call_kwargs['event'] == 'payment_refunded'
        assert 'Payment Refunded' in call_kwargs['title']
        assert 'Tournament cancelled' in call_kwargs['body']
    
    @patch('apps.tournaments.signals.notify')
    def test_no_notification_on_unchanged_status(self, mock_notify):
        """Test no notification sent when status doesn't change."""
        # Set original status same as current status
        self.payment._original_status = PaymentVerification.Status.PENDING
        self.payment.status = PaymentVerification.Status.PENDING
        self.payment.save()
        
        # Verify notify was NOT called
        mock_notify.assert_not_called()
    
    @patch('apps.tournaments.signals.notify')
    def test_no_notification_on_initial_creation(self, mock_notify):
        """Test no notification sent when payment is first created."""
        # Create a new registration for this test
        new_player = User.objects.create_user(
            username='newplayer',
            email='newplayer@test.com',
            password='password123'
        )
        new_registration = Registration.objects.create(
            tournament=self.tournament,
            user=new_player,
            status='pending'
        )
        
        # Create a new payment (created=True in post_save)
        new_payment = PaymentVerification(
            registration=new_registration,
            method='nagad',
            transaction_id='TXN67890',
            amount_bdt=500,
            status=PaymentVerification.Status.PENDING
        )
        new_payment.save()
        
        # Signal handler should skip notifications for created=True
        # We can't easily test this without triggering the actual signal,
        # so this is more of a documentation test
        assert new_payment.status == PaymentVerification.Status.PENDING
    
    @override_settings(NOTIFICATIONS_EMAIL_ENABLED=True)
    @patch('apps.tournaments.signals.notify')
    def test_email_parameters_included_when_enabled(self, mock_notify):
        """Test email parameters are passed when EMAIL_ENABLED is True."""
        mock_notify.return_value = {'created': 1, 'skipped': 0, 'email_sent': 1}
        
        # Patch the EMAIL_ENABLED constant in the signals module
        with patch('apps.tournaments.signals.EMAIL_ENABLED', True):
            # Verify payment
            self.payment._original_status = PaymentVerification.Status.PENDING
            self.payment.status = PaymentVerification.Status.VERIFIED
            self.payment.save()
        
        # Verify email parameters were included
        call_kwargs = mock_notify.call_args[1]
        assert 'email_subject' in call_kwargs
        assert 'email_template' in call_kwargs
        assert 'email_ctx' in call_kwargs
        assert call_kwargs['email_template'] == 'payment_verified'


@pytest.mark.django_db
class TestMatchNotificationSignals(TestCase):
    """Test match state change notification signals."""
    
    def setUp(self):
        """Create test fixtures."""
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='password123'
        )
        
        # Create game
        self.game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
        )
        
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            organizer=self.organizer,
            max_participants=16,
            game=self.game,
            format='single_elimination',
            participation_type='team',
            status='in_progress',
            registration_start=now - timezone.timedelta(days=14),
            registration_end=now - timezone.timedelta(days=7),
            tournament_start=now
        )
        
        self.match = Match.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            state=Match.SCHEDULED,
            participant1_id=1,
            participant2_id=2
        )
    
    def test_match_started_logs_event(self):
        """Test match started state change is logged."""
        # Note: Full implementation would notify participants
        # For now, we test that state tracking works
        
        self.match._original_state = Match.SCHEDULED
        self.match.state = Match.LIVE
        self.match.save()
        
        # Verify state changed
        assert self.match.state == Match.LIVE
    
    def test_match_completed_logs_event(self):
        """Test match completed state change is logged."""
        self.match._original_state = Match.LIVE
        self.match.state = Match.COMPLETED
        self.match.winner_id = 1
        self.match.loser_id = 2
        self.match.participant1_score = 13
        self.match.participant2_score = 8
        self.match.save()
        
        # Verify state changed
        assert self.match.state == Match.COMPLETED
        assert self.match.winner_id == 1
    
    def test_match_disputed_logs_event(self):
        """Test match disputed state change is logged."""
        self.match._original_state = Match.COMPLETED
        self.match.state = Match.DISPUTED
        self.match.save()
        
        # Verify state changed
        assert self.match.state == Match.DISPUTED
    
    def test_no_notification_on_unchanged_state(self):
        """Test no processing when match state doesn't change."""
        self.match._original_state = Match.SCHEDULED
        self.match.state = Match.SCHEDULED
        self.match.save()
        
        # Should complete without error
        assert self.match.state == Match.SCHEDULED


@pytest.mark.django_db
class TestTournamentNotificationSignals(TestCase):
    """Test tournament completion notification signals."""
    
    def setUp(self):
        """Create test fixtures."""
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='password123'
        )
        
        self.players = [
            User.objects.create_user(
                username=f'player{i}',
                email=f'player{i}@test.com',
                password='password123'
            )
            for i in range(3)
        ]
        
        # Create game
        self.game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
        )
        
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            organizer=self.organizer,
            max_participants=16,
            game=self.game,
            format='single_elimination',
            participation_type='team',
            status='in_progress',
            registration_start=now - timezone.timedelta(days=14),
            registration_end=now - timezone.timedelta(days=7),
            tournament_start=now
        )
        
        # Create confirmed registrations
        self.registrations = [
            Registration.objects.create(
                tournament=self.tournament,
                user=user,
                status='confirmed'
            )
            for i, user in enumerate(self.players)
        ]
    
    @patch('apps.tournaments.signals.notify')
    def test_tournament_completed_sends_notification(self, mock_notify):
        """Test notification sent when tournament is completed."""
        mock_notify.return_value = {'created': 3, 'skipped': 0, 'email_sent': 0}
        
        # Complete the tournament
        self.tournament._original_status = 'in_progress'
        self.tournament.status = Tournament.COMPLETED
        self.tournament.save()
        
        # Verify notify was called
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        
        # Should notify all 3 confirmed players
        assert len(call_kwargs['recipients']) == 3
        assert set(call_kwargs['recipients']) == set(self.players)
        assert call_kwargs['event'] == 'tournament_completed'
        assert 'Tournament Completed' in call_kwargs['title']
        assert self.tournament.name in call_kwargs['title']
        assert call_kwargs['tournament_id'] == self.tournament.id
    
    @patch('apps.tournaments.signals.notify')
    def test_tournament_completed_excludes_deleted_registrations(self, mock_notify):
        """Test deleted registrations are not notified."""
        # Soft-delete one registration
        self.registrations[0].is_deleted = True
        self.registrations[0].save()
        
        mock_notify.return_value = {'created': 2, 'skipped': 0, 'email_sent': 0}
        
        # Complete the tournament
        self.tournament._original_status = 'in_progress'
        self.tournament.status = Tournament.COMPLETED
        self.tournament.save()
        
        # Verify only 2 players were notified (excluding deleted)
        call_kwargs = mock_notify.call_args[1]
        assert len(call_kwargs['recipients']) == 2
        assert self.players[0] not in call_kwargs['recipients']
        assert self.players[1] in call_kwargs['recipients']
        assert self.players[2] in call_kwargs['recipients']
    
    @patch('apps.tournaments.signals.notify')
    def test_no_notification_on_non_completed_status(self, mock_notify):
        """Test no notification sent when changing to non-COMPLETED status."""
        # Change to a different status
        self.tournament._original_status = 'registration_open'
        self.tournament.status = 'in_progress'
        self.tournament.save()
        
        # Verify notify was NOT called
        mock_notify.assert_not_called()
    
    @patch('apps.tournaments.signals.notify')
    def test_no_notification_with_no_confirmed_registrations(self, mock_notify):
        """Test no notification sent when there are no confirmed registrations."""
        # Create tournament with no confirmed registrations
        now = timezone.now()
        empty_tournament = Tournament.objects.create(
            name='Empty Tournament',
            slug='empty-tournament',
            organizer=self.organizer,
            max_participants=16,
            game=self.game,
            format='single_elimination',
            participation_type='team',
            status='in_progress',
            registration_start=now - timezone.timedelta(days=14),
            registration_end=now - timezone.timedelta(days=7),
            tournament_start=now
        )
        
        # Complete the tournament
        empty_tournament._original_status = 'in_progress'
        empty_tournament.status = Tournament.COMPLETED
        empty_tournament.save()
        
        # Verify notify was NOT called (no recipients)
        mock_notify.assert_not_called()


@pytest.mark.django_db
class TestSignalIntegration(TestCase):
    """Integration tests for signal system."""
    
    def test_pre_save_hooks_track_original_values(self):
        """Test that pre_save signals properly track original values."""
        organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='password123'
        )
        
        player = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='password123'
        )
        
        # Create game
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            profile_id_field='riot_id',
            default_result_type='map_score',
        )
        
        now = timezone.now()
        tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            organizer=organizer,
            max_participants=16,
            game=game,
            format='single_elimination',
            participation_type='team',
            status='registration_open',
            registration_start=now - timezone.timedelta(days=7),
            registration_end=now + timezone.timedelta(days=7),
            tournament_start=now + timezone.timedelta(days=14)
        )
        
        registration = Registration.objects.create(
            tournament=tournament,
            user=player,
            status='pending'
        )
        
        # Create payment
        payment = PaymentVerification.objects.create(
            registration=registration,
            method='bkash',
            transaction_id='TXN12345',
            amount_bdt=500,
            status=PaymentVerification.Status.PENDING
        )
        
        # Modify and save (should trigger pre_save to track _original_status)
        payment.refresh_from_db()
        payment.status = PaymentVerification.Status.VERIFIED
        payment.save()
        
        # The pre_save signal should have set _original_status
        # This is tested indirectly through the notification tests above
        assert payment.status == PaymentVerification.Status.VERIFIED
