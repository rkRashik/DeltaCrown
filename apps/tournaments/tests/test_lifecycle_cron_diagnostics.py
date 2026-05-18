"""
Unit tests for lifecycle_cron memory diagnostics.

Covers:
    - _mem_diag_enabled(): env var parsing (all truthy values, falsy values,
      case-insensitivity, whitespace stripping)
    - _rss_mb(): returns a float, handles /proc unavailability gracefully
    - lifecycle_cron view: correct log lines emitted when diagnostics enabled
      and suppressed when disabled

Pure mock-based — no database, no Django ORM.
"""

import logging
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest


# ---------------------------------------------------------------------------
# _mem_diag_enabled
# ---------------------------------------------------------------------------

class TestMemDiagEnabled:
    """_mem_diag_enabled() must accept the documented truthy set."""

    def _call(self, value):
        from deltacrown.lifecycle_cron import _mem_diag_enabled
        with patch.dict(os.environ, {'ENABLE_MEMORY_DIAGNOSTICS': value}, clear=False):
            return _mem_diag_enabled()

    def _call_unset(self):
        from deltacrown.lifecycle_cron import _mem_diag_enabled
        env = {k: v for k, v in os.environ.items() if k != 'ENABLE_MEMORY_DIAGNOSTICS'}
        with patch.dict(os.environ, env, clear=True):
            return _mem_diag_enabled()

    # ── truthy values ───────────────────────────────────────────────

    def test_accepts_1(self):
        assert self._call('1') is True

    def test_accepts_true_lower(self):
        assert self._call('true') is True

    def test_accepts_true_upper(self):
        assert self._call('TRUE') is True

    def test_accepts_true_mixed(self):
        assert self._call('True') is True

    def test_accepts_yes_lower(self):
        assert self._call('yes') is True

    def test_accepts_yes_upper(self):
        assert self._call('YES') is True

    def test_accepts_on_lower(self):
        assert self._call('on') is True

    def test_accepts_on_upper(self):
        assert self._call('ON') is True

    def test_strips_whitespace(self):
        assert self._call('  1  ') is True

    def test_strips_whitespace_true(self):
        assert self._call('  true  ') is True

    # ── falsy values ────────────────────────────────────────────────

    def test_rejects_0(self):
        assert self._call('0') is False

    def test_rejects_false(self):
        assert self._call('false') is False

    def test_rejects_empty(self):
        assert self._call('') is False

    def test_rejects_no(self):
        assert self._call('no') is False

    def test_rejects_off(self):
        assert self._call('off') is False

    def test_unset_returns_false(self):
        assert self._call_unset() is False

    # ── evaluated at call time, not import time ──────────────────────

    def test_re_evaluated_per_call(self):
        """Value must be read from os.environ at call time, not module load."""
        from deltacrown.lifecycle_cron import _mem_diag_enabled
        with patch.dict(os.environ, {'ENABLE_MEMORY_DIAGNOSTICS': '0'}):
            assert _mem_diag_enabled() is False
        with patch.dict(os.environ, {'ENABLE_MEMORY_DIAGNOSTICS': '1'}):
            assert _mem_diag_enabled() is True
        with patch.dict(os.environ, {'ENABLE_MEMORY_DIAGNOSTICS': '0'}):
            assert _mem_diag_enabled() is False


# ---------------------------------------------------------------------------
# _rss_mb
# ---------------------------------------------------------------------------

class TestRssMb:
    """_rss_mb() must return a float and never raise."""

    def test_returns_float(self):
        from deltacrown.lifecycle_cron import _rss_mb
        result = _rss_mb()
        assert isinstance(result, float)

    def test_positive_or_minus_one(self):
        from deltacrown.lifecycle_cron import _rss_mb
        result = _rss_mb()
        assert result > 0 or result == -1.0

    def test_parses_proc_status_correctly(self):
        from deltacrown.lifecycle_cron import _rss_mb
        fake_status = (
            "Name:\tpython3\n"
            "VmRSS:\t  204800 kB\n"
            "VmSwap:\t      0 kB\n"
        )
        with patch('builtins.open', mock_open(read_data=fake_status)):
            result = _rss_mb()
        assert result == pytest.approx(200.0)  # 204800 kB / 1024 = 200 MB

    def test_returns_minus_one_when_proc_unavailable(self):
        from deltacrown.lifecycle_cron import _rss_mb
        with patch('builtins.open', side_effect=OSError('no proc')):
            with patch.dict('sys.modules', {'psutil': None}):
                result = _rss_mb()
        assert result == -1.0

    def test_never_raises(self):
        from deltacrown.lifecycle_cron import _rss_mb
        with patch('builtins.open', side_effect=RuntimeError('unexpected')):
            result = _rss_mb()  # must not raise
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# lifecycle_cron view — log line assertions
# ---------------------------------------------------------------------------

# Minimal request/response scaffolding so we can call the view
# without a running Django server.

def _make_request(secret='test-secret'):
    req = MagicMock()
    req.META = {'HTTP_AUTHORIZATION': f'Bearer {secret}'}
    req.method = 'POST'
    return req


def _run_cron_with_diag(enabled_value, caplog):
    """Call lifecycle_cron view with all task runners stubbed out."""
    from deltacrown import lifecycle_cron as mod

    stub_result = {'ok': True}

    task_patches = [
        patch.object(mod, '_run_auto_advance', return_value=stub_result),
        patch.object(mod, '_run_wrapup', return_value=stub_result),
        patch.object(mod, '_run_no_show', return_value=stub_result),
        patch.object(mod, '_run_lobby_close', return_value=stub_result),
        patch.object(mod, '_run_payment_expiry', return_value=stub_result),
        patch.object(mod, '_run_group_playoff_reconcile', return_value=stub_result),
        patch.object(mod, '_run_auto_confirm_submissions', return_value=stub_result),
        patch.object(mod, '_run_dispute_escalation', return_value=stub_result),
    ]

    with patch.dict(os.environ, {
        'CRON_SECRET': 'test-secret',
        'ENABLE_MEMORY_DIAGNOSTICS': enabled_value,
    }):
        # Re-read secret at call time (module-level constant needs patching)
        with patch.object(mod, '_CRON_SECRET', 'test-secret'):
            with patch.object(mod.cache, 'add', return_value=True):
                with patch.object(mod.cache, 'delete'):
                    with patch.object(mod, '_rss_mb', return_value=128.5):
                        for p in task_patches:
                            p.start()
                        try:
                            with caplog.at_level(logging.INFO, logger='deltacrown.lifecycle_cron'):
                                mod.lifecycle_cron(_make_request())
                        finally:
                            for p in task_patches:
                                p.stop()


class TestCronDiagLogLines:
    """When ENABLE_MEMORY_DIAGNOSTICS is truthy, specific log lines must appear."""

    def test_diag_enabled_emits_all_three_lines(self, caplog):
        _run_cron_with_diag('1', caplog)
        messages = caplog.messages
        assert any('memory diagnostics enabled' in m for m in messages), \
            "Expected '[lifecycle_cron] memory diagnostics enabled' in logs"
        assert any(m.startswith('[lifecycle_cron] rss_start=') for m in messages), \
            "Expected '[lifecycle_cron] rss_start=...' line in logs"
        assert any(m.startswith('[lifecycle_cron] rss_end=') for m in messages), \
            "Expected '[lifecycle_cron] rss_end=... delta=...' line in logs"

    def test_diag_enabled_with_true(self, caplog):
        _run_cron_with_diag('true', caplog)
        assert any('rss_start=' in m for m in caplog.messages)

    def test_diag_enabled_with_yes(self, caplog):
        _run_cron_with_diag('yes', caplog)
        assert any('rss_start=' in m for m in caplog.messages)

    def test_diag_enabled_with_on(self, caplog):
        _run_cron_with_diag('on', caplog)
        assert any('rss_start=' in m for m in caplog.messages)

    def test_diag_disabled_no_rss_lines(self, caplog):
        _run_cron_with_diag('0', caplog)
        messages = caplog.messages
        assert not any('rss_start=' in m for m in messages), \
            "rss_start line must NOT appear when diagnostics disabled"
        assert not any('rss_end=' in m for m in messages), \
            "rss_end line must NOT appear when diagnostics disabled"
        assert not any('memory diagnostics enabled' in m for m in messages)

    def test_diag_disabled_started_line_still_appears(self, caplog):
        """'started' log must appear regardless of diagnostics flag."""
        _run_cron_with_diag('0', caplog)
        assert any(m == '[lifecycle_cron] started' for m in caplog.messages)

    def test_rss_values_contain_mb_suffix(self, caplog):
        _run_cron_with_diag('1', caplog)
        rss_start_lines = [m for m in caplog.messages if m.startswith('[lifecycle_cron] rss_start=')]
        assert rss_start_lines, "No rss_start line found"
        assert 'MB' in rss_start_lines[0], f"Expected MB in: {rss_start_lines[0]}"
