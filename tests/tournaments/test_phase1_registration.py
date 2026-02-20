"""
Phase 1 Registration System Tests.

Covers:
- P1-T02: Command Center alert service
- P1-T03: Custom question wiring
- P1-T04: Lineup snapshot on team registration
- P1-T06: Registration number generation
- P1-T08: Payment queue (verify/reject)
- P1-T09: Refund policy model fields

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.command_center_service import CommandCenterService

User = get_user_model()


# ===========================================================================
# Helpers
# ===========================================================================

import uuid as _uuid


def _uid():
    return _uuid.uuid4().hex[:8]


def _make_game(**kwargs):
    uid = _uid()
    defaults = dict(
        name=f'Game-{uid}', slug=f'game-{uid}', short_code=uid[:4].upper(),
        category='FPS', display_name=f'Game {uid}', game_type='TEAM_VS_TEAM',
        is_active=True,
    )
    defaults.update(kwargs)
    return Game.objects.create(**defaults)


def _make_tournament(game, organizer, **kwargs):
    uid = _uid()
    now = timezone.now()
    defaults = dict(
        name=f'Tournament-{uid}',
        slug=f'tournament-{uid}',
        description='Test tournament for Phase 1 tests',
        game=game,
        organizer=organizer,
        status='registration_open',
        participation_type='team',
        format='single_elimination',
        max_participants=32,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    username = username or f'user-{_uid()}'
    defaults = dict(email=f'{username}@test.com', password='pass123')
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)


# ===========================================================================
# P1-T02: Command Center Alerts
# ===========================================================================

class TestCommandCenterAlerts(TestCase):
    """Test CommandCenterService.get_alerts logic."""

    def _make_tournament_mock(self, **kwargs):
        mock = MagicMock()
        mock.registration_end = kwargs.get('registration_end', timezone.now() + timedelta(days=7))
        mock.tournament_start = kwargs.get('tournament_start', timezone.now() + timedelta(days=14))
        mock.status = kwargs.get('status', 'registration_open')
        mock.enable_check_in = kwargs.get('enable_check_in', False)
        mock.check_in_minutes_before = kwargs.get('check_in_minutes_before', 30)
        return mock

    def test_no_alerts_when_everything_clear(self):
        """No alerts when stats are all zeros."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert alerts == []

    def test_critical_alert_for_open_disputes(self):
        """Open disputes generate CRITICAL alert."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 3, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'critical'
        assert '3' in alerts[0]['title']
        assert alerts[0]['link_tab'] == 'disputes'

    def test_warning_alert_for_pending_payments(self):
        """Pending payments generate WARNING alert."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 5},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'warning'
        assert '5' in alerts[0]['title']
        assert 'Payment' in alerts[0]['title']

    def test_warning_alert_for_pending_registrations(self):
        """Pending registrations generate WARNING alert."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 2},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'warning'
        assert 'Registration' in alerts[0]['title']

    def test_warning_when_registration_closes_within_24h(self):
        """Registration deadline within 24h generates WARNING."""
        t = self._make_tournament_mock(
            registration_end=timezone.now() + timedelta(hours=10)
        )
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'warning'
        assert 'Closes' in alerts[0]['title']

    def test_no_deadline_alert_when_more_than_24h(self):
        """No deadline alert when > 24h remaining."""
        t = self._make_tournament_mock(
            registration_end=timezone.now() + timedelta(hours=48)
        )
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert alerts == []

    def test_info_alert_for_disputes_under_review(self):
        """Disputes under review generate INFO alert."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 2},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'info'
        assert 'Under Review' in alerts[0]['title']

    def test_info_alert_for_live_matches(self):
        """Live matches generate INFO alert."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 4},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'info'
        assert 'Live' in alerts[0]['title']

    def test_checkin_alert_when_within_2h(self):
        """Check-in imminent generates INFO alert."""
        t = self._make_tournament_mock(
            enable_check_in=True,
            check_in_minutes_before=30,
            tournament_start=timezone.now() + timedelta(hours=1),
        )
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 0},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['severity'] == 'info'
        assert 'Check-In' in alerts[0]['title']

    def test_multiple_alerts_sorted_by_severity(self):
        """Multiple alerts produced; critical first."""
        t = self._make_tournament_mock(
            registration_end=timezone.now() + timedelta(hours=10)
        )
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 1},
            payment_stats={'pending': 2},
            dispute_stats={'open': 1, 'under_review': 1},
            match_stats={'live': 1},
        )
        # critical â†’ warning â†’ warning â†’ warning â†’ info â†’ info
        assert len(alerts) >= 5
        assert alerts[0]['severity'] == 'critical'

    def test_singular_vs_plural_titles(self):
        """Single item should not have plural 's'."""
        t = self._make_tournament_mock()
        alerts = CommandCenterService.get_alerts(
            t,
            reg_stats={'pending': 0},
            payment_stats={'pending': 1},
            dispute_stats={'open': 0, 'under_review': 0},
            match_stats={'live': 0},
        )
        assert len(alerts) == 1
        assert alerts[0]['title'] == '1 Payment Awaiting Verification'


# ===========================================================================
# P1-T02: Lifecycle Progress
# ===========================================================================

class TestLifecycleProgress(TestCase):
    """Test CommandCenterService.get_lifecycle_progress."""

    def test_draft_stage(self):
        t = MagicMock(status='draft')
        result = CommandCenterService.get_lifecycle_progress(t)
        assert result['stage'] == 'draft'
        assert result['progress_pct'] == 0
        assert result['stages'][0]['status'] == 'active'

    def test_registration_stage(self):
        t = MagicMock(status='registration_open')
        result = CommandCenterService.get_lifecycle_progress(t)
        assert result['progress_pct'] == 20
        assert result['stages'][1]['status'] == 'active'

    def test_completed_stage(self):
        t = MagicMock(status='completed')
        result = CommandCenterService.get_lifecycle_progress(t)
        assert result['progress_pct'] == 100
        assert result['stages'][4]['status'] == 'done'

    def test_cancelled_resets_all(self):
        t = MagicMock(status='cancelled')
        result = CommandCenterService.get_lifecycle_progress(t)
        assert result['progress_pct'] == 0
        for s in result['stages']:
            assert s['status'] == 'cancelled'


# ===========================================================================
# P1-T02: Upcoming Events
# ===========================================================================

class TestUpcomingEvents(TestCase):
    """Test CommandCenterService.get_upcoming_events."""

    def test_future_events_returned(self):
        t = MagicMock()
        t.registration_end = timezone.now() + timedelta(days=1)
        t.tournament_start = timezone.now() + timedelta(days=5)
        t.enable_check_in = False
        del t.tournament_end  # so hasattr returns False
        events = CommandCenterService.get_upcoming_events(t)
        assert len(events) == 2
        assert events[0]['label'] == 'Registration Closes'

    def test_past_events_excluded(self):
        t = MagicMock()
        t.registration_end = timezone.now() - timedelta(days=1)
        t.tournament_start = timezone.now() - timedelta(hours=1)
        t.enable_check_in = False
        del t.tournament_end
        events = CommandCenterService.get_upcoming_events(t)
        assert events == []

    def test_checkin_event_included(self):
        t = MagicMock()
        t.registration_end = None
        t.tournament_start = timezone.now() + timedelta(days=1)
        t.enable_check_in = True
        t.check_in_minutes_before = 30
        del t.tournament_end
        events = CommandCenterService.get_upcoming_events(t)
        labels = [e['label'] for e in events]
        assert 'Check-In Opens' in labels
        assert 'Tournament Starts' in labels


# ===========================================================================
# P1-T06: Registration Number Auto-Generation
# ===========================================================================

@pytest.mark.django_db
class TestRegistrationNumber:
    """Test registration_number auto-generation."""

    def test_auto_generates_on_first_save(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user)
        reg = Registration.objects.create(tournament=t, user=user, status='pending')
        assert reg.registration_number is not None
        assert reg.registration_number.startswith('DC-')

    def test_format_is_dc_yy_seq(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user)
        reg = Registration.objects.create(tournament=t, user=user, status='pending')
        year = timezone.now().strftime('%y')
        assert reg.registration_number.startswith(f'DC-{year}-')
        # Sequence portion should be zero-padded to 4 digits
        seq = reg.registration_number.split('-')[-1]
        assert len(seq) == 4

    def test_sequential_numbering(self):
        game = _make_game()
        org = _make_user()
        t = _make_tournament(game, org)
        user1 = _make_user()
        user2 = _make_user()

        reg1 = Registration.objects.create(tournament=t, user=user1, status='pending')
        reg2 = Registration.objects.create(tournament=t, user=user2, status='pending')

        seq1 = int(reg1.registration_number.split('-')[-1])
        seq2 = int(reg2.registration_number.split('-')[-1])
        assert seq2 == seq1 + 1

    def test_no_overwrite_on_resave(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user)
        reg = Registration.objects.create(tournament=t, user=user, status='pending')
        original_num = reg.registration_number
        reg.status = 'confirmed'
        reg.save()
        reg.refresh_from_db()
        assert reg.registration_number == original_num


# ===========================================================================
# P1-T09: Refund Policy Model Fields
# ===========================================================================

@pytest.mark.django_db
class TestRefundPolicyFields:
    """Test Tournament refund_policy and refund_policy_text fields."""

    def test_default_refund_policy_is_no_refund(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user)
        assert t.refund_policy == 'no_refund'

    def test_custom_refund_policy_with_text(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user,
                             refund_policy='custom',
                             refund_policy_text='50% refund before bracket generation')
        assert t.refund_policy == 'custom'
        assert '50%' in t.refund_policy_text

    def test_refund_policy_choices_are_valid(self):
        valid_choices = ['no_refund', 'refund_until_checkin', 'refund_until_bracket',
                         'full_refund', 'custom']
        field = Tournament._meta.get_field('refund_policy')
        db_choices = [c[0] for c in field.choices]
        assert set(valid_choices) == set(db_choices)


# ===========================================================================
# P1-T08: Payment Verify / Reject
# ===========================================================================

@pytest.mark.django_db
class TestPaymentVerifyReject:
    """Test Payment.verify() and Payment.reject() methods."""

    def _setup_payment(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user,
                             has_entry_fee=True,
                             entry_fee_amount=Decimal('100.00'))
        reg = Registration.objects.create(tournament=t, user=user, status='payment_submitted')
        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id=f'TXN-{_uid()}',
            status='submitted',
        )
        return payment, user

    def test_verify_payment(self):
        payment, user = self._setup_payment()
        staff = _make_user(is_staff=True)
        payment.verify(verified_by=staff)
        payment.refresh_from_db()
        assert payment.status == 'verified'
        assert payment.verified_by == staff
        assert payment.verified_at is not None

    def test_reject_payment(self):
        payment, user = self._setup_payment()
        staff = _make_user(is_staff=True)
        payment.reject(rejected_by=staff, reason='Fake screenshot')
        payment.refresh_from_db()
        assert payment.status == 'rejected'

    def test_payment_amount_must_be_positive(self):
        """Payment with amount <= 0 should fail constraint."""
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user,
                             has_entry_fee=True,
                             entry_fee_amount=Decimal('100.00'))
        reg = Registration.objects.create(tournament=t, user=user, status='payment_submitted')
        with pytest.raises(Exception):
            Payment.objects.create(
                registration=reg,
                payment_method='bkash',
                amount=Decimal('-50.00'),
                transaction_id=f'TXN-{_uid()}',
                status='submitted',
            )


# ===========================================================================
# P1-T04: Lineup Snapshot
# ===========================================================================

@pytest.mark.django_db
class TestLineupSnapshot:
    """Test that lineup_snapshot field stores team roster at registration time."""

    def test_lineup_snapshot_field_exists(self):
        """Registration model has lineup_snapshot JSONField."""
        field = Registration._meta.get_field('lineup_snapshot')
        assert field is not None

    def test_lineup_snapshot_stores_data(self):
        user = _make_user()
        game = _make_game()
        t = _make_tournament(game, user)
        snapshot_data = {
            'team_name': 'Team Alpha',
            'members': [
                {'username': 'player1', 'game_id': 'RIOT#1234'},
                {'username': 'player2', 'game_id': 'RIOT#5678'},
            ],
            'captured_at': timezone.now().isoformat(),
        }
        reg = Registration.objects.create(
            tournament=t, user=user, status='pending',
            lineup_snapshot=snapshot_data,
        )
        reg.refresh_from_db()
        assert reg.lineup_snapshot['team_name'] == 'Team Alpha'
        assert len(reg.lineup_snapshot['members']) == 2


# ===========================================================================
# P1-T03: Custom Questions (Model Existence)
# ===========================================================================

@pytest.mark.django_db
class TestCustomQuestions:
    """Test RegistrationQuestion model exists and is functional."""

    def test_registration_question_model_exists(self):
        try:
            from apps.tournaments.models.registration import RegistrationQuestion
        except ImportError:
            pytest.skip('RegistrationQuestion model not yet implemented (P1-T03 pending)')
        field_names = [f.name for f in RegistrationQuestion._meta.get_fields()]
        assert 'tournament' in field_names
        assert 'question_text' in field_names
        assert 'is_required' in field_names

    def test_registration_answer_model_exists(self):
        try:
            from apps.tournaments.models.registration import RegistrationAnswer
        except ImportError:
            pytest.skip('RegistrationAnswer model not yet implemented (P1-T03 pending)')
        field_names = [f.name for f in RegistrationAnswer._meta.get_fields()]
        assert 'registration' in field_names
        assert 'question' in field_names
        assert 'answer_text' in field_names
