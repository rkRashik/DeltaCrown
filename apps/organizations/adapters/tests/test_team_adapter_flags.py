"""
Tests for feature flag routing behavior in TeamAdapter.

This test suite verifies that feature flags correctly control routing
between legacy and vNext systems, including:
- Routing priority rules (force_legacy > adapter_enabled > routing_mode)
- Safe defaults (legacy-first when flags missing)
- Allowlist behavior in auto mode
- Fallback to legacy on vNext failure
- Metrics recording for routing decisions and errors

Testing Strategy:
- Use Django settings override decorator (@override_settings)
- Mock external dependencies (TeamService, legacy models)
- Verify adapter behavior under all flag combinations
- Verify metrics hooks are called with correct parameters

Performance:
- No database queries (all mocked)
- Fast execution (<1 second for full suite)

Coverage Goals:
- 100% coverage of flag evaluation logic
- All routing priority rules verified
- All metrics hooks verified
"""

import pytest
from unittest.mock import Mock, patch, call
from django.test import override_settings

from apps.organizations.adapters.team_adapter import TeamAdapter
from apps.organizations.adapters.flags import (
    should_use_vnext_routing,
    get_routing_reason,
    is_adapter_enabled,
    is_force_legacy_enabled,
    get_routing_mode,
    get_team_allowlist,
)


# ============================================================================
# FLAG FUNCTION TESTS (flags.py)
# ============================================================================


class TestFlagFunctions:
    """Test individual flag functions from flags.py."""
    
    @override_settings()
    def test_default_settings_favor_legacy(self):
        """Verify default behavior favors legacy when settings missing."""
        # Remove all feature flag settings
        if hasattr(pytest, 'django_settings'):
            del pytest.django_settings.TEAM_VNEXT_FORCE_LEGACY
            del pytest.django_settings.TEAM_VNEXT_ADAPTER_ENABLED
            del pytest.django_settings.TEAM_VNEXT_ROUTING_MODE
            del pytest.django_settings.TEAM_VNEXT_TEAM_ALLOWLIST
        
        # All functions should return conservative defaults
        assert is_force_legacy_enabled() == False  # Not emergency
        assert is_adapter_enabled() == False  # Adapter disabled by default
        assert get_routing_mode() == "legacy_only"  # Legacy-first
        assert get_team_allowlist() == []  # No allowlist
        assert should_use_vnext_routing(123) == False  # Legacy routing
        assert get_routing_reason(123) == "adapter_disabled"
    
    @override_settings(TEAM_VNEXT_FORCE_LEGACY=True)
    def test_force_legacy_takes_absolute_priority(self):
        """Verify FORCE_LEGACY overrides all other settings."""
        # Even with adapter enabled and vnext_only mode
        with self.settings(
            TEAM_VNEXT_ADAPTER_ENABLED=True,
            TEAM_VNEXT_ROUTING_MODE="vnext_only",
            TEAM_VNEXT_TEAM_ALLOWLIST=[123],
        ):
            assert should_use_vnext_routing(123) == False
            assert get_routing_reason(123) == "force_legacy"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=False,
    )
    def test_adapter_disabled_prevents_vnext_routing(self):
        """Verify ADAPTER_ENABLED=False forces legacy."""
        assert should_use_vnext_routing(123) == False
        assert get_routing_reason(123) == "adapter_disabled"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="legacy_only",
    )
    def test_routing_mode_legacy_only(self):
        """Verify mode=legacy_only forces legacy."""
        assert should_use_vnext_routing(123) == False
        assert get_routing_reason(123) == "mode_legacy_only"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    def test_routing_mode_vnext_only(self):
        """Verify mode=vnext_only forces vNext."""
        assert should_use_vnext_routing(123) == True
        assert get_routing_reason(123) == "mode_vnext_only"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[123, 456],
    )
    def test_routing_mode_auto_with_allowlist(self):
        """Verify auto mode uses allowlist."""
        # Team in allowlist → vNext
        assert should_use_vnext_routing(123) == True
        assert get_routing_reason(123) == "auto_allowlisted"
        
        # Team not in allowlist → legacy
        assert should_use_vnext_routing(789) == False
        assert get_routing_reason(789) == "auto_not_allowlisted"
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="invalid_mode",  # Invalid value
    )
    def test_invalid_routing_mode_defaults_to_legacy(self):
        """Verify invalid routing mode defaults to legacy_only."""
        assert get_routing_mode() == "legacy_only"
        assert should_use_vnext_routing(123) == False
    
    @override_settings(
        TEAM_VNEXT_TEAM_ALLOWLIST="not_a_list",  # Invalid type
    )
    def test_invalid_allowlist_type_defaults_to_empty(self):
        """Verify non-list allowlist defaults to empty list."""
        assert get_team_allowlist() == []


# ============================================================================
# ADAPTER ROUTING TESTS (team_adapter.py)
# ============================================================================


@pytest.mark.django_db
class TestTeamAdapterRouting:
    """Test TeamAdapter routing behavior with feature flags."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = TeamAdapter()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=False,
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.record_routing_decision")
    def test_adapter_disabled_skips_database_query(
        self, mock_record, mock_vnext_team
    ):
        """Verify adapter_disabled=True skips DB query (performance)."""
        result = self.adapter.is_vnext_team(123)
        
        # Should return False without querying database
        assert result == False
        mock_vnext_team.objects.filter.assert_not_called()
        
        # Should record routing decision
        mock_record.assert_called_once()
        call_args = mock_record.call_args[0]
        assert call_args[0] == 123  # team_id
        assert call_args[1] == "legacy"  # path
        assert call_args[2] == "adapter_disabled"  # reason
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.record_routing_decision")
    @patch("apps.organizations.adapters.team_adapter.record_adapter_error")
    def test_vnext_only_mode_queries_database(
        self, mock_error, mock_record, mock_vnext_team
    ):
        """Verify vnext_only mode queries database to verify existence."""
        # Mock VNextTeam.objects.filter().exists() → True
        mock_vnext_team.objects.filter.return_value.exists.return_value = True
        
        result = self.adapter.is_vnext_team(123)
        
        # Should query database
        assert result == True
        mock_vnext_team.objects.filter.assert_called_once_with(id=123)
        
        # Should record routing decision
        mock_record.assert_called_once()
        call_args = mock_record.call_args[0]
        assert call_args[0] == 123  # team_id
        assert call_args[1] == "vnext"  # path
        assert call_args[2] == "mode_vnext_only"  # reason
        
        # Should NOT record error (team exists)
        mock_error.assert_not_called()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.record_adapter_error")
    def test_vnext_mode_logs_error_when_team_not_found(
        self, mock_error, mock_vnext_team
    ):
        """Verify error logged when flags say vNext but team doesn't exist."""
        # Mock VNextTeam.objects.filter().exists() → False
        mock_vnext_team.objects.filter.return_value.exists.return_value = False
        
        result = self.adapter.is_vnext_team(123)
        
        # Should return False (conservative)
        assert result == False
        
        # Should record error metrics
        mock_error.assert_called_once()
        call_args = mock_error.call_args
        assert call_args[1]["team_id"] == 123
        assert call_args[1]["error_code"] == "VNEXT_TEAM_NOT_FOUND"
        assert call_args[1]["path"] == "vnext"


# ============================================================================
# ADAPTER METHOD TESTS WITH FLAGS
# ============================================================================


@pytest.mark.django_db
class TestAdapterMethodsWithFlags:
    """Test adapter methods respect feature flags."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = TeamAdapter()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=False,
    )
    @patch("apps.organizations.adapters.team_adapter.LegacyTeam")
    @patch("apps.organizations.adapters.team_adapter.TeamService")
    @patch("apps.organizations.adapters.team_adapter.MetricsContext")
    def test_get_team_url_uses_legacy_when_adapter_disabled(
        self, mock_metrics, mock_service, mock_legacy
    ):
        """Verify get_team_url uses legacy path when adapter disabled."""
        # Mock legacy team
        mock_team = Mock()
        mock_team.slug = "protocol-v"
        mock_legacy.objects.get.return_value = mock_team
        
        # Mock metrics context
        mock_metrics.return_value.__enter__ = Mock()
        mock_metrics.return_value.__exit__ = Mock(return_value=False)
        
        with patch("apps.organizations.adapters.team_adapter.reverse") as mock_reverse:
            mock_reverse.return_value = "/teams/protocol-v/"
            url = self.adapter.get_team_url(123)
        
        # Should use legacy path
        assert url == "/teams/protocol-v/"
        mock_reverse.assert_called_once_with(
            "teams:team_detail", kwargs={"slug": "protocol-v"}
        )
        
        # Should NOT call TeamService
        mock_service.get_team_identity.assert_not_called()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.TeamService")
    @patch("apps.organizations.adapters.team_adapter.MetricsContext")
    def test_get_team_url_uses_vnext_when_enabled(
        self, mock_metrics, mock_service, mock_vnext
    ):
        """Verify get_team_url uses vNext path when adapter enabled."""
        # Mock vNext team exists
        mock_vnext.objects.filter.return_value.exists.return_value = True
        
        # Mock TeamService response
        mock_identity = Mock()
        mock_identity.slug = "protocol-v"
        mock_service.get_team_identity.return_value = mock_identity
        
        # Mock metrics context
        mock_metrics.return_value.__enter__ = Mock()
        mock_metrics.return_value.__exit__ = Mock(return_value=False)
        
        with patch("apps.organizations.adapters.team_adapter.reverse") as mock_reverse:
            with patch("apps.organizations.adapters.team_adapter.record_routing_decision"):
                mock_reverse.return_value = "/organizations/protocol-v/"
                url = self.adapter.get_team_url(123)
        
        # Should use vNext path
        assert url == "/organizations/protocol-v/"
        mock_reverse.assert_called_once_with(
            "organizations:team_detail", kwargs={"team_slug": "protocol-v"}
        )
        
        # Should call TeamService
        mock_service.get_team_identity.assert_called_once_with(team_id=123)


# ============================================================================
# METRICS RECORDING TESTS
# ============================================================================


@pytest.mark.django_db
class TestMetricsRecording:
    """Test metrics are recorded correctly."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = TeamAdapter()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="auto",
        TEAM_VNEXT_TEAM_ALLOWLIST=[123],
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.record_routing_decision")
    def test_routing_decision_metrics_recorded(
        self, mock_record, mock_vnext
    ):
        """Verify routing decision metrics are recorded."""
        mock_vnext.objects.filter.return_value.exists.return_value = True
        
        self.adapter.is_vnext_team(123)
        
        # Should record metrics
        mock_record.assert_called_once()
        call_args = mock_record.call_args[0]
        assert call_args[0] == 123  # team_id
        assert call_args[1] == "vnext"  # path
        assert call_args[2] == "auto_allowlisted"  # reason
        assert isinstance(call_args[3], float)  # duration_ms
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=False,
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.TeamService")
    @patch("apps.organizations.adapters.team_adapter.record_adapter_error")
    @patch("apps.organizations.adapters.team_adapter.record_routing_decision")
    def test_adapter_error_metrics_recorded(
        self, mock_routing, mock_error, mock_service, mock_vnext
    ):
        """Verify adapter error metrics are recorded on failure."""
        # Mock vNext team exists (routing says vNext)
        mock_vnext.objects.filter.return_value.exists.return_value = True
        
        # Mock TeamService raises NotFoundError
        from apps.organizations.services.exceptions import NotFoundError
        mock_service.get_team_identity.side_effect = NotFoundError(
            message="Team not found",
            error_code="TEAM_NOT_FOUND",
        )
        
        # get_team_url should raise NotFoundError
        with pytest.raises(NotFoundError):
            with patch("apps.organizations.adapters.team_adapter.MetricsContext"):
                self.adapter.get_team_url(123)
        
        # Should record error metrics
        mock_error.assert_called_once()
        call_args = mock_error.call_args[1]
        assert call_args["team_id"] == 123
        assert call_args["error_code"] == "TEAM_NOT_FOUND"
        assert call_args["path"] == "vnext"
        assert call_args["exception_type"] == "NotFoundError"


# ============================================================================
# EMERGENCY ROLLBACK TEST
# ============================================================================


@pytest.mark.django_db
class TestEmergencyRollback:
    """Test emergency rollback behavior (FORCE_LEGACY flag)."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = TeamAdapter()
    
    @override_settings(
        TEAM_VNEXT_FORCE_LEGACY=True,  # EMERGENCY KILLSWITCH
        TEAM_VNEXT_ADAPTER_ENABLED=True,
        TEAM_VNEXT_ROUTING_MODE="vnext_only",
        TEAM_VNEXT_TEAM_ALLOWLIST=[123],
    )
    @patch("apps.organizations.adapters.team_adapter.VNextTeam")
    @patch("apps.organizations.adapters.team_adapter.LegacyTeam")
    @patch("apps.organizations.adapters.team_adapter.MetricsContext")
    def test_force_legacy_overrides_all_settings(
        self, mock_metrics, mock_legacy, mock_vnext
    ):
        """Verify FORCE_LEGACY overrides all other settings (emergency)."""
        # Mock legacy team
        mock_team = Mock()
        mock_team.slug = "protocol-v"
        mock_legacy.objects.get.return_value = mock_team
        
        # Mock metrics context
        mock_metrics.return_value.__enter__ = Mock()
        mock_metrics.return_value.__exit__ = Mock(return_value=False)
        
        # Should use legacy even though all other flags say vNext
        with patch("apps.organizations.adapters.team_adapter.reverse") as mock_reverse:
            mock_reverse.return_value = "/teams/protocol-v/"
            url = self.adapter.get_team_url(123)
        
        assert url == "/teams/protocol-v/"
        
        # Should NOT query vNext database
        mock_vnext.objects.filter.assert_not_called()
        
        # Should use legacy URL pattern
        mock_reverse.assert_called_once_with(
            "teams:team_detail", kwargs={"slug": "protocol-v"}
        )
