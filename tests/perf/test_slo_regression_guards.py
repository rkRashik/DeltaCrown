"""
SLO Regression Guard Tests

Compares current performance against historical baseline.
Fails if ANY scenario regresses by >15% on p95 latency.

Baseline Source:
- CI: artifacts/performance/baseline_<run_id>.json (from perf-baseline.yml)
- Local: tests/perf/fixtures/baseline_reference.json (committed)

Usage (CI):
    pytest tests/perf/test_slo_regression_guards.py -v -m regression

Usage (Local with custom baseline):
    PERF_BASELINE_PATH=path/to/baseline.json pytest tests/perf/test_slo_regression_guards.py
"""

import os
import json
import pytest
from pathlib import Path

from tests.perf.perf_harness import PerfHarness


# Default baseline path (committed fixture)
DEFAULT_BASELINE_PATH = Path(__file__).parent / "fixtures" / "baseline_reference.json"


def load_baseline():
    """Load baseline from env var or default fixture."""
    baseline_path = os.getenv('PERF_BASELINE_PATH', str(DEFAULT_BASELINE_PATH))
    
    if not os.path.exists(baseline_path):
        pytest.skip(f"Baseline not found at {baseline_path}")
    
    with open(baseline_path, 'r') as f:
        return json.load(f)


def compute_regression_percent(current_value, baseline_value):
    """
    Compute regression percentage.
    
    Positive = slower (bad), Negative = faster (good)
    """
    if baseline_value == 0:
        return 0.0
    
    return ((current_value - baseline_value) / baseline_value) * 100


@pytest.fixture(scope='module')
def baseline_data():
    """Load baseline data once per test module."""
    return load_baseline()


@pytest.fixture(scope='module')
def current_harness_results():
    """Run perf harness once per test module (reduced samples for CI)."""
    samples = int(os.getenv('PERF_SAMPLES', '150'))  # Reduced for CI speed
    
    harness = PerfHarness(samples=samples)
    results = harness.run_all_scenarios()
    
    return results


@pytest.mark.regression
@pytest.mark.performance
class TestSLORegressionGuards:
    """Guard tests that fail if performance regresses >15%."""
    
    def test_registration_p95_no_regression(self, baseline_data, current_harness_results):
        """
        Registration p95 should NOT regress by >15%.
        
        Baseline: Read from baseline_data['scenarios']['registration']['p95_ms']
        Current: From current harness run
        """
        baseline_p95 = baseline_data['scenarios']['registration']['p95_ms']
        current_p95 = current_harness_results['registration']['p95_ms']
        
        regression_pct = compute_regression_percent(current_p95, baseline_p95)
        
        assert regression_pct <= 15.0, (
            f"Registration p95 regressed by {regression_pct:.1f}% "
            f"(baseline: {baseline_p95}ms → current: {current_p95}ms). "
            f"Threshold: ≤15% regression."
        )
        
        # Log improvement if faster
        if regression_pct < 0:
            print(f"✅ Registration p95 IMPROVED by {abs(regression_pct):.1f}% ({current_p95}ms)")
    
    def test_result_submit_p95_no_regression(self, baseline_data, current_harness_results):
        """Result submission p95 should NOT regress by >15%."""
        baseline_p95 = baseline_data['scenarios']['result_submit']['p95_ms']
        current_p95 = current_harness_results['result_submit']['p95_ms']
        
        regression_pct = compute_regression_percent(current_p95, baseline_p95)
        
        assert regression_pct <= 15.0, (
            f"Result submit p95 regressed by {regression_pct:.1f}% "
            f"(baseline: {baseline_p95}ms → current: {current_p95}ms)"
        )
    
    def test_websocket_broadcast_p95_no_regression(self, baseline_data, current_harness_results):
        """WebSocket broadcast p95 should NOT regress by >15%."""
        baseline_p95 = baseline_data['scenarios']['websocket_broadcast']['p95_ms']
        current_p95 = current_harness_results['websocket_broadcast']['p95_ms']
        
        regression_pct = compute_regression_percent(current_p95, baseline_p95)
        
        assert regression_pct <= 15.0, (
            f"WebSocket broadcast p95 regressed by {regression_pct:.1f}% "
            f"(baseline: {baseline_p95}ms → current: {current_p95}ms)"
        )
    
    def test_economy_transfer_p95_no_regression(self, baseline_data, current_harness_results):
        """Economy transfer p95 should NOT regress by >15%."""
        baseline_p95 = baseline_data['scenarios']['economy_transfer']['p95_ms']
        current_p95 = current_harness_results['economy_transfer']['p95_ms']
        
        regression_pct = compute_regression_percent(current_p95, baseline_p95)
        
        assert regression_pct <= 15.0, (
            f"Economy transfer p95 regressed by {regression_pct:.1f}% "
            f"(baseline: {baseline_p95}ms → current: {current_p95}ms)"
        )
    
    def test_all_scenarios_error_rate_stable(self, baseline_data, current_harness_results):
        """
        Error rates should remain stable (no increase >0.5%).
        
        Example: If baseline error rate = 0.2%, current should be ≤0.7%
        """
        for scenario_name in ['registration', 'result_submit', 'websocket_broadcast', 'economy_transfer']:
            baseline_error = baseline_data['scenarios'][scenario_name]['error_rate_percent']
            current_error = current_harness_results[scenario_name]['error_rate_percent']
            
            error_increase = current_error - baseline_error
            
            assert error_increase <= 0.5, (
                f"{scenario_name} error rate increased by {error_increase:.2f}% "
                f"(baseline: {baseline_error}% → current: {current_error}%). "
                f"Threshold: ≤0.5% increase."
            )
    
    def test_registration_p99_no_severe_regression(self, baseline_data, current_harness_results):
        """
        Registration p99 (tail latency) should NOT regress by >20%.
        
        Allows slightly higher threshold for tail latency (more variance).
        """
        baseline_p99 = baseline_data['scenarios']['registration']['p99_ms']
        current_p99 = current_harness_results['registration']['p99_ms']
        
        regression_pct = compute_regression_percent(current_p99, baseline_p99)
        
        assert regression_pct <= 20.0, (
            f"Registration p99 regressed by {regression_pct:.1f}% "
            f"(baseline: {baseline_p99}ms → current: {current_p99}ms). "
            f"Threshold: ≤20% regression for tail latency."
        )


@pytest.mark.regression
class TestRegressionReporting:
    """Generate detailed regression report for CI artifacts."""
    
    def test_generate_regression_report(self, baseline_data, current_harness_results):
        """
        Generate JSON report comparing all metrics.
        
        Output: artifacts/performance/regression_report.json
        """
        report = {
            'baseline_timestamp': baseline_data.get('timestamp', 'unknown'),
            'current_timestamp': current_harness_results.get('timestamp', 'unknown'),
            'scenarios': {}
        }
        
        for scenario_name in ['registration', 'result_submit', 'websocket_broadcast', 'economy_transfer']:
            baseline_scenario = baseline_data['scenarios'][scenario_name]
            current_scenario = current_harness_results[scenario_name]
            
            p50_regression = compute_regression_percent(
                current_scenario['p50_ms'],
                baseline_scenario['p50_ms']
            )
            p95_regression = compute_regression_percent(
                current_scenario['p95_ms'],
                baseline_scenario['p95_ms']
            )
            p99_regression = compute_regression_percent(
                current_scenario['p99_ms'],
                baseline_scenario['p99_ms']
            )
            error_delta = current_scenario['error_rate_percent'] - baseline_scenario['error_rate_percent']
            
            report['scenarios'][scenario_name] = {
                'p50': {
                    'baseline_ms': baseline_scenario['p50_ms'],
                    'current_ms': current_scenario['p50_ms'],
                    'regression_percent': round(p50_regression, 2)
                },
                'p95': {
                    'baseline_ms': baseline_scenario['p95_ms'],
                    'current_ms': current_scenario['p95_ms'],
                    'regression_percent': round(p95_regression, 2),
                    'status': 'FAIL' if p95_regression > 15.0 else 'PASS'
                },
                'p99': {
                    'baseline_ms': baseline_scenario['p99_ms'],
                    'current_ms': current_scenario['p99_ms'],
                    'regression_percent': round(p99_regression, 2),
                    'status': 'FAIL' if p99_regression > 20.0 else 'PASS'
                },
                'error_rate': {
                    'baseline_percent': baseline_scenario['error_rate_percent'],
                    'current_percent': current_scenario['error_rate_percent'],
                    'delta_percent': round(error_delta, 2),
                    'status': 'FAIL' if error_delta > 0.5 else 'PASS'
                }
            }
        
        # Write report
        report_path = Path('artifacts/performance/regression_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Regression report written to: {report_path}")
        
        # Assert no failures
        failed_scenarios = [
            name for name, data in report['scenarios'].items()
            if data['p95']['status'] == 'FAIL' or data['error_rate']['status'] == 'FAIL'
        ]
        
        assert len(failed_scenarios) == 0, (
            f"Performance regression detected in: {', '.join(failed_scenarios)}. "
            f"See artifacts/performance/regression_report.json for details."
        )
