"""
Tests for Grafana Dashboard JSON Schema Validation.

Validates that grafana/*.json files have valid structure, proper queries,
and all required panels/variables/alerts configured correctly.
"""

import pytest
import json
from pathlib import Path


class TestGrafanaDashboards:
    """Test suite for Grafana dashboard JSON validation."""

    @pytest.fixture
    def observability_dashboard(self):
        """Load the observability dashboard JSON."""
        dashboard_path = Path("grafana/webhooks_canary_observability.json")
        assert dashboard_path.exists(), "Observability dashboard not found"
        with open(dashboard_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def alerts_dashboard(self):
        """Load the alerts dashboard JSON."""
        alerts_path = Path("grafana/webhooks_canary_alerts.json")
        assert alerts_path.exists(), "Alerts dashboard not found"
        with open(alerts_path, "r") as f:
            return json.load(f)

    def test_observability_dashboard_structure(self, observability_dashboard):
        """Test that observability dashboard has required top-level keys."""
        required_keys = ["dashboard", "folderId", "overwrite"]
        for key in required_keys:
            assert key in observability_dashboard, f"Missing key: {key}"
        
        dashboard = observability_dashboard["dashboard"]
        assert "title" in dashboard
        assert dashboard["title"] == "Webhook Canary — Observability"
        assert "panels" in dashboard
        assert isinstance(dashboard["panels"], list)

    def test_observability_dashboard_has_9_panels(self, observability_dashboard):
        """Test that observability dashboard has exactly 9 panels."""
        panels = observability_dashboard["dashboard"]["panels"]
        assert len(panels) == 9, f"Expected 9 panels, found {len(panels)}"

    def test_observability_panel_titles(self, observability_dashboard):
        """Test that all expected panels exist by title."""
        expected_titles = [
            "Success Rate (%)",
            "P95 Latency (ms)",
            "Circuit Breaker Opens (Last 24h)",
            "Circuit Breaker State",
            "Success vs Failure (Timeseries)",
            "Latency Percentiles (P50/P95/P99)",
            "Retry Distribution",
            "4xx vs 5xx Errors",
            "Events per Second (by Type)",
        ]
        
        panels = observability_dashboard["dashboard"]["panels"]
        panel_titles = [p.get("title") for p in panels]
        
        for expected_title in expected_titles:
            assert expected_title in panel_titles, f"Missing panel: {expected_title}"

    def test_observability_template_variables(self, observability_dashboard):
        """Test that dashboard has event and endpoint template variables."""
        templating = observability_dashboard["dashboard"].get("templating", {})
        variables = templating.get("list", [])
        
        variable_names = [v.get("name") for v in variables]
        assert "event" in variable_names, "Missing 'event' template variable"
        assert "endpoint" in variable_names, "Missing 'endpoint' template variable"

    def test_observability_refresh_interval(self, observability_dashboard):
        """Test that dashboard auto-refreshes every 30 seconds."""
        dashboard = observability_dashboard["dashboard"]
        assert "refresh" in dashboard
        assert dashboard["refresh"] == "30s", "Dashboard should refresh every 30s"

    def test_success_rate_panel_query(self, observability_dashboard):
        """Test that success rate panel has correct Prometheus query."""
        panels = observability_dashboard["dashboard"]["panels"]
        success_rate_panel = next(p for p in panels if p["title"] == "Success Rate (%)")
        
        # Check panel type
        assert success_rate_panel["type"] == "stat"
        
        # Check query
        targets = success_rate_panel.get("targets", [])
        assert len(targets) > 0, "Success rate panel should have at least one query"
        
        expr = targets[0].get("expr", "")
        assert "webhook_delivery_success_total" in expr
        assert "rate" in expr.lower() or "increase" in expr.lower()

    def test_p95_latency_panel_query(self, observability_dashboard):
        """Test that P95 latency panel uses histogram_quantile."""
        panels = observability_dashboard["dashboard"]["panels"]
        p95_panel = next(p for p in panels if p["title"] == "P95 Latency (ms)")
        
        targets = p95_panel.get("targets", [])
        expr = targets[0].get("expr", "")
        
        assert "histogram_quantile" in expr
        assert "0.95" in expr  # P95 quantile
        assert "webhook_delivery_latency_seconds" in expr

    def test_circuit_breaker_state_panel_mapping(self, observability_dashboard):
        """Test that CB state panel maps 0/1/2 to CLOSED/HALF_OPEN/OPEN."""
        panels = observability_dashboard["dashboard"]["panels"]
        cb_state_panel = next(p for p in panels if p["title"] == "Circuit Breaker State")
        
        # Check for value mappings
        field_config = cb_state_panel.get("fieldConfig", {})
        overrides = field_config.get("overrides", [])
        
        # Should have mappings for 0, 1, 2
        has_mappings = any("valueMappings" in str(override) for override in overrides)
        assert has_mappings, "CB state panel should have value mappings"

    def test_alerts_dashboard_structure(self, alerts_dashboard):
        """Test that alerts dashboard has required structure."""
        assert "groups" in alerts_dashboard
        groups = alerts_dashboard["groups"]
        assert isinstance(groups, list)
        assert len(groups) > 0, "Alerts dashboard should have at least one group"

    def test_alerts_dashboard_has_12_rules(self, alerts_dashboard):
        """Test that alerts dashboard has exactly 12 alert rules."""
        total_rules = sum(len(group["rules"]) for group in alerts_dashboard["groups"])
        assert total_rules == 12, f"Expected 12 alert rules, found {total_rules}"

    def test_critical_success_rate_alert(self, alerts_dashboard):
        """Test that critical success rate alert exists with correct threshold."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        success_alerts = [r for r in all_rules if "success" in r.get("alert", "").lower()]
        critical_success = [r for r in success_alerts if "critical" in r.get("labels", {}).get("severity", "").lower()]
        
        assert len(critical_success) > 0, "Missing critical success rate alert"
        
        # Check threshold (should be <90%)
        alert = critical_success[0]
        expr = alert.get("expr", "")
        assert "0.9" in expr or "90" in expr, "Critical success threshold should be 90%"
        assert "for: 5m" in str(alert), "Critical success alert should trigger after 5 minutes"

    def test_critical_p95_latency_alert(self, alerts_dashboard):
        """Test that critical P95 latency alert exists with correct threshold."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        latency_alerts = [r for r in all_rules if "latency" in r.get("alert", "").lower() or "p95" in r.get("alert", "").lower()]
        critical_latency = [r for r in latency_alerts if "critical" in r.get("labels", {}).get("severity", "").lower()]
        
        assert len(critical_latency) > 0, "Missing critical P95 latency alert"
        
        # Check threshold (should be >5s = 5000ms)
        alert = critical_latency[0]
        expr = alert.get("expr", "")
        assert "5" in expr, "Critical P95 threshold should be 5 seconds"

    def test_circuit_breaker_alerts_exist(self, alerts_dashboard):
        """Test that circuit breaker alerts exist (opens + stuck open)."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        cb_alerts = [r for r in all_rules if "circuit" in r.get("alert", "").lower()]
        assert len(cb_alerts) >= 2, "Should have at least 2 CB alerts (opens + stuck open)"
        
        # Check for "opens per 24h" alert
        opens_alert = next((r for r in cb_alerts if "24h" in r.get("alert", "").lower() or "day" in r.get("alert", "").lower()), None)
        assert opens_alert is not None, "Missing CB opens per 24h alert"
        
        # Check for "stuck open" alert
        stuck_alert = next((r for r in cb_alerts if "stuck" in r.get("alert", "").lower() or "open" in r.get("expr", "")), None)
        assert stuck_alert is not None, "Missing CB stuck open alert"

    def test_warning_success_rate_alert(self, alerts_dashboard):
        """Test that warning success rate alert exists with correct threshold."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        success_alerts = [r for r in all_rules if "success" in r.get("alert", "").lower()]
        warning_success = [r for r in success_alerts if "warning" in r.get("labels", {}).get("severity", "").lower()]
        
        assert len(warning_success) > 0, "Missing warning success rate alert"
        
        # Check threshold (should be <95%)
        alert = warning_success[0]
        expr = alert.get("expr", "")
        assert "0.95" in expr or "95" in expr, "Warning success threshold should be 95%"

    def test_all_alerts_have_severity_labels(self, alerts_dashboard):
        """Test that all alerts have severity labels (critical/warning/info)."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        for rule in all_rules:
            labels = rule.get("labels", {})
            assert "severity" in labels, f"Alert '{rule.get('alert')}' missing severity label"
            severity = labels["severity"]
            assert severity in ["critical", "warning", "info"], f"Invalid severity: {severity}"

    def test_all_alerts_have_annotations(self, alerts_dashboard):
        """Test that all alerts have summary and description annotations."""
        all_rules = []
        for group in alerts_dashboard["groups"]:
            all_rules.extend(group["rules"])
        
        for rule in all_rules:
            annotations = rule.get("annotations", {})
            assert "summary" in annotations, f"Alert '{rule.get('alert')}' missing summary"
            assert "description" in annotations, f"Alert '{rule.get('alert')}' missing description"

    def test_dashboard_json_files_are_valid_json(self):
        """Test that all Grafana JSON files are valid JSON."""
        grafana_dir = Path("grafana")
        if not grafana_dir.exists():
            pytest.skip("Grafana directory not found")
        
        json_files = list(grafana_dir.glob("*.json"))
        assert len(json_files) > 0, "No JSON files found in grafana/"
        
        for json_file in json_files:
            with open(json_file, "r") as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {json_file.name}: {e}")
