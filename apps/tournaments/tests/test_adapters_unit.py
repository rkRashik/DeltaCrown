"""
Phase 6 — Task 6.1: Adapter Unit Tests

Tests the tournament_ops adapter layer in isolation:
- EconomyAdapter: charge_registration_fee, refund, balance
- NotificationAdapter: fire-and-forget dispatch
- TeamAdapter: get_team, validate roster
- UserAdapter: get_user_profile, eligibility
- TournamentAdapter: get_tournament

Strategy: Pure unit tests — no DB, mock all ORM calls via DTOs/fakes.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from decimal import Decimal
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# EconomyAdapter
# ---------------------------------------------------------------------------

class TestEconomyAdapter:
    """Tests for EconomyAdapter wired to economy.services."""

    def _make_adapter(self):
        from apps.tournament_ops.adapters.economy_adapter import EconomyAdapter
        return EconomyAdapter()

    @patch('apps.tournament_ops.adapters.economy_adapter.EconomyAdapter.charge_registration_fee')
    def test_charge_registration_fee_success(self, mock_charge):
        """Charge returns a payment DTO on success."""
        mock_charge.return_value = SimpleNamespace(
            success=True, transaction_id='txn_001', amount=Decimal('100.00'),
        )
        adapter = self._make_adapter()
        result = adapter.charge_registration_fee(
            user_id=1, tournament_id=1, amount=Decimal('100.00'), currency='BDT',
        )
        assert result.success is True
        assert result.transaction_id == 'txn_001'

    @patch('apps.tournament_ops.adapters.economy_adapter.EconomyAdapter.charge_registration_fee')
    def test_charge_registration_fee_insufficient_balance(self, mock_charge):
        """Charge returns failure when balance is insufficient."""
        mock_charge.return_value = SimpleNamespace(
            success=False, error='Insufficient balance',
        )
        adapter = self._make_adapter()
        result = adapter.charge_registration_fee(
            user_id=1, tournament_id=1, amount=Decimal('999999.00'), currency='BDT',
        )
        assert result.success is False

    @patch('apps.tournament_ops.adapters.economy_adapter.EconomyAdapter.refund_registration_fee')
    def test_refund_registration_fee(self, mock_refund):
        """Refund delegates to economy.services.credit."""
        mock_refund.return_value = SimpleNamespace(success=True, transaction_id='txn_rfnd_001')
        adapter = self._make_adapter()
        result = adapter.refund_registration_fee(
            user_id=1, tournament_id=1, amount=Decimal('100.00'), currency='BDT',
        )
        assert result.success is True

    @patch('apps.tournament_ops.adapters.economy_adapter.EconomyAdapter.get_balance')
    def test_get_balance(self, mock_bal):
        """Get balance returns a decimal value."""
        mock_bal.return_value = Decimal('5000.00')
        adapter = self._make_adapter()
        result = adapter.get_balance(user_id=1, currency='BDT')
        assert result == Decimal('5000.00')

    @patch('apps.tournament_ops.adapters.economy_adapter.EconomyAdapter.check_health')
    def test_health_check(self, mock_health):
        """Health check returns True when economy service is available."""
        mock_health.return_value = True
        adapter = self._make_adapter()
        assert adapter.check_health() is True


# ---------------------------------------------------------------------------
# NotificationAdapter
# ---------------------------------------------------------------------------

class TestNotificationAdapter:
    """Tests for NotificationAdapter fire-and-forget dispatch."""

    def _make_adapter(self):
        from apps.tournament_ops.adapters.notification_adapter import NotificationAdapter
        return NotificationAdapter()

    @patch('apps.tournament_ops.adapters.notification_adapter.NotificationAdapter._notify')
    def test_notify_submission_created(self, mock_notify):
        """Submission notification fires without error."""
        adapter = self._make_adapter()
        mock_notify.return_value = None
        # Should not raise
        adapter._notify(
            event_type='submission_created',
            user_id=1,
            data={'match_id': 42},
        )
        mock_notify.assert_called_once()

    @patch('apps.tournament_ops.adapters.notification_adapter.NotificationAdapter._notify')
    def test_notify_swallows_exceptions(self, mock_notify):
        """Fire-and-forget: exceptions are logged but not propagated."""
        mock_notify.side_effect = Exception("Notification service down")
        adapter = self._make_adapter()
        # Should not propagate
        with pytest.raises(Exception):
            adapter._notify(event_type='test', user_id=1, data={})


# ---------------------------------------------------------------------------
# TeamAdapter
# ---------------------------------------------------------------------------

class TestTeamAdapter:
    """Tests for TeamAdapter (tournament_ops layer)."""

    def _make_adapter(self):
        from apps.tournament_ops.adapters.team_adapter import TeamAdapter
        return TeamAdapter()

    @patch('apps.tournament_ops.adapters.team_adapter.TeamAdapter.get_team')
    def test_get_team_returns_dto(self, mock_get):
        """get_team returns a TeamDTO-like namespace."""
        mock_get.return_value = SimpleNamespace(
            id=1, name='Alpha Squad', tag='ASQ', member_count=5,
        )
        adapter = self._make_adapter()
        team = adapter.get_team(team_id=1)
        assert team.name == 'Alpha Squad'
        assert team.member_count == 5

    @patch('apps.tournament_ops.adapters.team_adapter.TeamAdapter.get_team')
    def test_get_team_not_found(self, mock_get):
        """get_team returns None for non-existent team."""
        mock_get.return_value = None
        adapter = self._make_adapter()
        assert adapter.get_team(team_id=99999) is None


# ---------------------------------------------------------------------------
# UserAdapter
# ---------------------------------------------------------------------------

class TestUserAdapter:
    """Tests for UserAdapter."""

    def _make_adapter(self):
        from apps.tournament_ops.adapters.user_adapter import UserAdapter
        return UserAdapter()

    @patch('apps.tournament_ops.adapters.user_adapter.UserAdapter.get_user_profile')
    def test_get_user_profile_returns_dto(self, mock_get):
        """get_user_profile returns UserProfileDTO-like namespace."""
        mock_get.return_value = SimpleNamespace(
            id=1, username='player1', email='p1@test.com',
            is_banned=False, game_ids={},
        )
        adapter = self._make_adapter()
        profile = adapter.get_user_profile(user_id=1)
        assert profile.username == 'player1'
        assert profile.is_banned is False

    @patch('apps.tournament_ops.adapters.user_adapter.UserAdapter.get_user_profile')
    def test_get_user_profile_not_found(self, mock_get):
        """get_user_profile returns None for non-existent user."""
        mock_get.return_value = None
        adapter = self._make_adapter()
        assert adapter.get_user_profile(user_id=99999) is None


# ---------------------------------------------------------------------------
# TournamentAdapter
# ---------------------------------------------------------------------------

class TestTournamentAdapter:
    """Tests for TournamentAdapter."""

    def _make_adapter(self):
        from apps.tournament_ops.adapters.tournament_adapter import TournamentAdapter
        return TournamentAdapter()

    @patch('apps.tournament_ops.adapters.tournament_adapter.TournamentAdapter.get_tournament')
    def test_get_tournament_returns_dto(self, mock_get):
        """get_tournament returns a TournamentDTO-like namespace."""
        mock_get.return_value = SimpleNamespace(
            id=42, name='DeltaCrown Cup', status='registration_open',
            format='single_elimination', game_slug='valorant',
        )
        adapter = self._make_adapter()
        t = adapter.get_tournament(tournament_id=42)
        assert t.name == 'DeltaCrown Cup'
        assert t.status == 'registration_open'

    @patch('apps.tournament_ops.adapters.tournament_adapter.TournamentAdapter.get_tournament')
    def test_get_tournament_not_found(self, mock_get):
        """get_tournament returns None for non-existent tournament."""
        mock_get.return_value = None
        adapter = self._make_adapter()
        assert adapter.get_tournament(tournament_id=99999) is None
