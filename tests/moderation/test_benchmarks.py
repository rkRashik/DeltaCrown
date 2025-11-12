"""
Micro-benchmarks for moderation enforcement gates.

Performance SLOs (p95):
- check_websocket_access(): ≤50ms
- check_purchase_access(): ≤50ms  
- get_all_active_policies(): ≤100ms

Tests fail if p95 exceeds threshold by >10%.
Results persisted to Artifacts/benchmarks/phase_8_3/
"""
import pytest
import json
import os
from pathlib import Path
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.user_profile.models import UserProfile
from apps.moderation import enforcement
from apps.moderation.services import sanctions_service
from apps.tournaments.models import Tournament

User = get_user_model()

# Benchmark output directory
BENCHMARK_DIR = Path("Artifacts/benchmarks/phase_8_3")
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)


def create_bench_user(username_prefix):
    """Helper to create User + UserProfile for benchmarks."""
    timestamp = timezone.now().timestamp()
    user = User.objects.create_user(
        username=f'{username_prefix}_{timestamp}',
        email=f'{username_prefix}_{timestamp}@bench.com',
        password='testpass123'
    )
    profile = UserProfile.objects.create(
        user=user,
        display_name=f'{username_prefix.title()} Benchmark'
    )
    return profile


@pytest.mark.django_db(transaction=True)
class TestWebSocketGateBenchmark(TransactionTestCase):
    """Benchmark WebSocket gate check performance (SLO: p95 ≤50ms)."""
    
    def setUp(self):
        """Create test users and active BAN."""
        self.moderator = create_bench_user('bench_ws_mod')
        self.subject = create_bench_user('bench_ws_subject')
        
        # Create active BAN
        sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Benchmark test',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=7,
            idempotency_key=f'bench_ws_ban_{timezone.now().timestamp()}'
        )
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True, MODERATION_ENFORCEMENT_WS=True)
    def test_websocket_gate_check_performance(self, benchmark):
        """Benchmark check_websocket_access() - SLO: p95 ≤50ms."""
        result = benchmark(enforcement.check_websocket_access, self.subject.id)
        
        # Verify correctness
        assert result['allowed'] is False
        assert result['reason_code'] == 'BAN'
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000  # Convert to ms
        
        # SLO check: p95 ≤ 50ms (allow 10% tolerance = 55ms)
        threshold_ms = 55.0
        assert p95_ms <= threshold_ms, f"WebSocket gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("websocket_gate", stats, p95_ms)
    
    def _save_benchmark_result(self, name, stats, p95_ms):
        """Save benchmark results to JSON."""
        result = {
            "test": name,
            "p50_ms": stats.stats.median * 1000,
            "p95_ms": p95_ms,
            "p99_ms": stats.stats.q_99 * 1000,
            "mean_ms": stats.stats.mean * 1000,
            "min_ms": stats.stats.min * 1000,
            "max_ms": stats.stats.max * 1000,
            "stddev_ms": stats.stats.stddev * 1000,
            "rounds": stats.stats.rounds
        }
        
        output_file = BENCHMARK_DIR / f"{name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)


@pytest.mark.django_db(transaction=True)
class TestPurchaseGateBenchmark(TransactionTestCase):
    """Benchmark purchase gate check performance (SLO: p95 ≤50ms)."""
    
    def setUp(self):
        """Create test users and active MUTE."""
        self.moderator = create_bench_user('bench_purchase_mod')
        self.subject = create_bench_user('bench_purchase_subject')
        
        # Create active MUTE
        sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='MUTE',
            reason='Purchase benchmark',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=7,
            idempotency_key=f'bench_purchase_mute_{timezone.now().timestamp()}'
        )
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True, MODERATION_ENFORCEMENT_PURCHASE=True)
    def test_purchase_gate_check_performance(self, benchmark):
        """Benchmark check_purchase_access() - SLO: p95 ≤50ms."""
        result = benchmark(enforcement.check_purchase_access, self.subject.id)
        
        # Verify correctness
        assert result['allowed'] is False
        assert result['reason_code'] == 'MUTE'
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000
        
        # SLO check: p95 ≤ 50ms (allow 10% tolerance = 55ms)
        threshold_ms = 55.0
        assert p95_ms <= threshold_ms, f"Purchase gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("purchase_gate", stats, p95_ms)
    
    def _save_benchmark_result(self, name, stats, p95_ms):
        """Save benchmark results to JSON."""
        result = {
            "test": name,
            "p50_ms": stats.stats.median * 1000,
            "p95_ms": p95_ms,
            "p99_ms": stats.stats.q_99 * 1000,
            "mean_ms": stats.stats.mean * 1000,
            "min_ms": stats.stats.min * 1000,
            "max_ms": stats.stats.max * 1000,
            "stddev_ms": stats.stats.stddev * 1000,
            "rounds": stats.stats.rounds
        }
        
        output_file = BENCHMARK_DIR / f"{name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)


@pytest.mark.django_db(transaction=True)
class TestPolicyQueryBenchmark(TransactionTestCase):
    """Benchmark policy query performance (SLO: p95 ≤100ms)."""
    
    def setUp(self):
        """Create test users and multiple sanctions."""
        self.moderator = create_bench_user('bench_policy_mod')
        self.subject = create_bench_user('bench_policy_subject')
        
        # Create multiple sanctions (3)
        for idx, s_type in enumerate(['BAN', 'MUTE', 'SUSPEND']):
            sanctions_service.create_sanction(
                subject_profile_id=self.subject.id,
                sanction_type=s_type,
                reason=f'Benchmark test {idx}',
                moderator_id=self.moderator.id,
                scope='global',
                scope_id=None,
                duration_days=7,
                idempotency_key=f'bench_policy_{s_type}_{timezone.now().timestamp()}'
            )
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True)
    def test_policy_query_performance(self, benchmark):
        """Benchmark get_all_active_policies() - SLO: p95 ≤100ms."""
        result = benchmark(enforcement.get_all_active_policies, self.subject.id)
        
        # Verify correctness
        assert result['has_active_sanctions'] is True
        assert len(result['sanctions']) == 3
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000
        
        # SLO check: p95 ≤ 100ms (allow 10% tolerance = 110ms)
        threshold_ms = 110.0
        assert p95_ms <= threshold_ms, f"Policy query p95 ({p95_ms:.2f}ms) exceeds SLO threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("policy_query", stats, p95_ms)
    
    def _save_benchmark_result(self, name, stats, p95_ms):
        """Save benchmark results to JSON."""
        result = {
            "test": name,
            "p50_ms": stats.stats.median * 1000,
            "p95_ms": p95_ms,
            "p99_ms": stats.stats.q_99 * 1000,
            "mean_ms": stats.stats.mean * 1000,
            "min_ms": stats.stats.min * 1000,
            "max_ms": stats.stats.max * 1000,
            "stddev_ms": stats.stats.stddev * 1000,
            "rounds": stats.stats.rounds
        }
        
        output_file = BENCHMARK_DIR / f"{name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)


@pytest.mark.django_db(transaction=True)
class TestScopedGateBenchmark(TransactionTestCase):
    """Benchmark scoped gate checks (tournament-specific)."""
    
    def setUp(self):
        """Create test users, tournament, and scoped sanction."""
        self.moderator = create_bench_user('bench_scoped_mod')
        self.subject = create_bench_user('bench_scoped_subject')
        
        self.tournament = Tournament.objects.create(
            name=f'Benchmark Tournament {timezone.now().timestamp()}',
            start_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=14)
        )
        
        # Create tournament-scoped BAN
        sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Scoped benchmark',
            moderator_id=self.moderator.id,
            scope='tournament',
            scope_id=self.tournament.id,
            duration_days=7,
            idempotency_key=f'bench_scoped_ban_{timezone.now().timestamp()}'
        )
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True, MODERATION_ENFORCEMENT_WS=True)
    def test_scoped_websocket_gate_performance(self, benchmark):
        """Benchmark scoped WebSocket gate - SLO: p95 ≤50ms."""
        result = benchmark(
            enforcement.check_websocket_access,
            self.subject.id,
            self.tournament.id
        )
        
        # Verify correctness
        assert result['allowed'] is False
        assert result['reason_code'] == 'BAN'
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000
        
        # SLO check: p95 ≤ 50ms (allow 10% tolerance = 55ms)
        threshold_ms = 55.0
        assert p95_ms <= threshold_ms, f"Scoped WS gate p95 ({p95_ms:.2f}ms) exceeds SLO threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("scoped_websocket_gate", stats, p95_ms)
    
    def _save_benchmark_result(self, name, stats, p95_ms):
        """Save benchmark results to JSON."""
        result = {
            "test": name,
            "p50_ms": stats.stats.median * 1000,
            "p95_ms": p95_ms,
            "p99_ms": stats.stats.q_99 * 1000,
            "mean_ms": stats.stats.mean * 1000,
            "min_ms": stats.stats.min * 1000,
            "max_ms": stats.stats.max * 1000,
            "stddev_ms": stats.stats.stddev * 1000,
            "rounds": stats.stats.rounds
        }
        
        output_file = BENCHMARK_DIR / f"{name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)


@pytest.mark.django_db(transaction=True)
class TestNoSanctionFastPathBenchmark(TransactionTestCase):
    """Benchmark gate checks for users with NO sanctions (fast path)."""
    
    def setUp(self):
        """Create clean user with no sanctions."""
        self.clean_user = create_bench_user('bench_clean_user')
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True, MODERATION_ENFORCEMENT_WS=True)
    def test_websocket_gate_no_sanction_fast_path(self, benchmark):
        """Benchmark WebSocket gate for clean user (should be faster)."""
        result = benchmark(enforcement.check_websocket_access, self.clean_user.id)
        
        # Verify correctness
        assert result['allowed'] is True
        assert result['reason_code'] is None
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000
        
        # Fast path should be well under threshold
        threshold_ms = 55.0
        assert p95_ms <= threshold_ms, f"Fast path p95 ({p95_ms:.2f}ms) exceeds threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("fast_path_websocket", stats, p95_ms)
    
    @override_settings(MODERATION_ENFORCEMENT_ENABLED=True, MODERATION_ENFORCEMENT_PURCHASE=True)
    def test_purchase_gate_no_sanction_fast_path(self, benchmark):
        """Benchmark purchase gate for clean user (should be faster)."""
        result = benchmark(enforcement.check_purchase_access, self.clean_user.id)
        
        # Verify correctness
        assert result['allowed'] is True
        
        # Extract stats
        stats = benchmark.stats
        p95_ms = stats.stats.q_95 * 1000
        
        # Fast path should be well under threshold
        threshold_ms = 55.0
        assert p95_ms <= threshold_ms, f"Fast path p95 ({p95_ms:.2f}ms) exceeds threshold ({threshold_ms}ms)"
        
        # Persist results
        self._save_benchmark_result("fast_path_purchase", stats, p95_ms)
    
    def _save_benchmark_result(self, name, stats, p95_ms):
        """Save benchmark results to JSON."""
        result = {
            "test": name,
            "p50_ms": stats.stats.median * 1000,
            "p95_ms": p95_ms,
            "p99_ms": stats.stats.q_99 * 1000,
            "mean_ms": stats.stats.mean * 1000,
            "min_ms": stats.stats.min * 1000,
            "max_ms": stats.stats.max * 1000,
            "stddev_ms": stats.stats.stddev * 1000,
            "rounds": stats.stats.rounds
        }
        
        output_file = BENCHMARK_DIR / f"{name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
