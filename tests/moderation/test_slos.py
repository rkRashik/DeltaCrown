"""
SLO Guard Tests for Moderation Enforcement Gates.

Parses benchmark results from Artifacts/benchmarks/phase_8_3/ and validates:
- WebSocket gate p95 ≤ 50ms
- Purchase gate p95 ≤ 50ms
- Policy query p95 ≤ 100ms

Tests FAIL if any p95 exceeds threshold by >10%.
"""
import json
import pytest
from pathlib import Path


BENCHMARK_DIR = Path("Artifacts/benchmarks/phase_8_3")
SLO_THRESHOLDS = {
    "websocket_gate": 50.0,  # ms
    "purchase_gate": 50.0,    # ms
    "policy_query": 100.0,    # ms
    "scoped_websocket_gate": 50.0,  # ms
    "fast_path_websocket": 50.0,  # ms
    "fast_path_purchase": 50.0     # ms
}
TOLERANCE_FACTOR = 1.10  # Allow 10% over threshold


def load_benchmark_result(test_name: str) -> dict:
    """Load benchmark JSON result for a test."""
    result_file = BENCHMARK_DIR / f"{test_name}_results.json"
    
    if not result_file.exists():
        pytest.skip(f"Benchmark result not found: {result_file}")
    
    with open(result_file, 'r') as f:
        return json.load(f)


class TestSLOCompliance:
    """Validate all enforcement gates meet SLO thresholds."""
    
    def test_websocket_gate_slo(self):
        """WebSocket gate p95 must be ≤ 50ms (allow 10% tolerance = 55ms)."""
        result = load_benchmark_result("websocket_gate")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["websocket_gate"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"WebSocket gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )
    
    def test_purchase_gate_slo(self):
        """Purchase gate p95 must be ≤ 50ms (allow 10% tolerance = 55ms)."""
        result = load_benchmark_result("purchase_gate")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["purchase_gate"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"Purchase gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )
    
    def test_policy_query_slo(self):
        """Policy query p95 must be ≤ 100ms (allow 10% tolerance = 110ms)."""
        result = load_benchmark_result("policy_query")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["policy_query"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"Policy query p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )
    
    def test_scoped_websocket_gate_slo(self):
        """Scoped WebSocket gate p95 must be ≤ 50ms (allow 10% tolerance = 55ms)."""
        result = load_benchmark_result("scoped_websocket_gate")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["scoped_websocket_gate"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"Scoped WebSocket gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )
    
    def test_fast_path_websocket_slo(self):
        """Fast path (no sanctions) WebSocket p95 must be ≤ 50ms."""
        result = load_benchmark_result("fast_path_websocket")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["fast_path_websocket"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"Fast path WebSocket p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )
    
    def test_fast_path_purchase_slo(self):
        """Fast path (no sanctions) purchase p95 must be ≤ 50ms."""
        result = load_benchmark_result("fast_path_purchase")
        p95_ms = result['p95_ms']
        threshold = SLO_THRESHOLDS["fast_path_purchase"] * TOLERANCE_FACTOR
        
        assert p95_ms <= threshold, (
            f"Fast path purchase p95 ({p95_ms:.2f}ms) exceeds SLO threshold "
            f"({threshold:.2f}ms with 10% tolerance)"
        )


class TestSLOReport:
    """Generate comprehensive SLO report from all benchmarks."""
    
    def test_generate_slo_summary_report(self):
        """Generate human-readable SLO summary."""
        report_lines = ["=== Moderation Enforcement SLO Report ===", ""]
        all_passing = True
        
        for test_name, threshold_ms in SLO_THRESHOLDS.items():
            try:
                result = load_benchmark_result(test_name)
                p95_ms = result['p95_ms']
                p50_ms = result['p50_ms']
                p99_ms = result['p99_ms']
                threshold_with_tolerance = threshold_ms * TOLERANCE_FACTOR
                
                status = "✅ PASS" if p95_ms <= threshold_with_tolerance else "❌ FAIL"
                if "FAIL" in status:
                    all_passing = False
                
                report_lines.append(f"{test_name}:")
                report_lines.append(f"  {status}")
                report_lines.append(f"  p50: {p50_ms:.2f}ms | p95: {p95_ms:.2f}ms | p99: {p99_ms:.2f}ms")
                report_lines.append(f"  SLO threshold: {threshold_ms:.2f}ms (+ 10% tolerance = {threshold_with_tolerance:.2f}ms)")
                report_lines.append("")
            except Exception as e:
                report_lines.append(f"{test_name}: ⚠️ SKIP (benchmark not run: {e})")
                report_lines.append("")
        
        report = "\n".join(report_lines)
        print(report)
        
        # Save report to file
        report_file = BENCHMARK_DIR / "slo_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Assert all passing
        assert all_passing, "One or more gates exceeded SLO thresholds (see report above)"
