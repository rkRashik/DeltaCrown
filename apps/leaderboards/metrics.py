"""
Leaderboards Observability & Metrics (Phase E Section 10)

Prometheus-style metrics for leaderboards service monitoring.
Tracks request counts, cache hit/miss rates, and latency.

Usage:
    from apps.leaderboards.metrics import record_leaderboard_request
    
    with record_leaderboard_request(scope='tournament', source='cache'):
        # ... fetch leaderboard data ...
        pass

Metrics Exported:
    - leaderboards_requests_total: Total leaderboard requests (labeled by scope)
    - leaderboards_cache_hits_total: Cache hit count
    - leaderboards_cache_misses_total: Cache miss count
    - leaderboards_latency_ms_bucket: Request latency histogram

Dashboard Queries:
    # Request rate by scope
    rate(leaderboards_requests_total[5m])
    
    # Cache hit ratio
    sum(rate(leaderboards_cache_hits_total[5m])) / 
    (sum(rate(leaderboards_cache_hits_total[5m])) + sum(rate(leaderboards_cache_misses_total[5m])))
    
    # P95 latency
    histogram_quantile(0.95, rate(leaderboards_latency_ms_bucket[5m]))
"""

import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ===========================
# In-Memory Metrics Storage
# ===========================
# NOTE: For production, replace with Prometheus client library or statsd
# This implementation uses in-memory counters for simplicity

_metrics_storage: Dict[str, Any] = {
    'requests_total': {},  # {scope: count}
    'cache_hits_total': 0,
    'cache_misses_total': 0,
    'latency_samples': [],  # [(latency_ms, scope), ...]
}


def get_metrics_snapshot() -> Dict[str, Any]:
    """
    Get current metrics snapshot for monitoring/debugging.
    
    Returns:
        Dict with current metric values
    
    Example:
        >>> snapshot = get_metrics_snapshot()
        >>> print(snapshot['cache_hit_ratio'])
        0.85
    """
    total_hits = _metrics_storage['cache_hits_total']
    total_misses = _metrics_storage['cache_misses_total']
    total_cache_requests = total_hits + total_misses
    
    cache_hit_ratio = (total_hits / total_cache_requests) if total_cache_requests > 0 else 0.0
    
    # Compute latency percentiles
    latency_samples = [lat for lat, _ in _metrics_storage['latency_samples'][-1000:]]  # Last 1000 samples
    latency_samples.sort()
    
    p50 = latency_samples[int(len(latency_samples) * 0.50)] if latency_samples else 0.0
    p95 = latency_samples[int(len(latency_samples) * 0.95)] if latency_samples else 0.0
    p99 = latency_samples[int(len(latency_samples) * 0.99)] if latency_samples else 0.0
    
    return {
        'requests_total': dict(_metrics_storage['requests_total']),
        'cache_hits_total': total_hits,
        'cache_misses_total': total_misses,
        'cache_hit_ratio': cache_hit_ratio,
        'latency_percentiles': {
            'p50': p50,
            'p95': p95,
            'p99': p99,
        },
        'sample_count': len(latency_samples),
    }


def reset_metrics() -> None:
    """
    Reset all metrics (for testing purposes only).
    
    WARNING: Do not call in production.
    """
    _metrics_storage['requests_total'].clear()
    _metrics_storage['cache_hits_total'] = 0
    _metrics_storage['cache_misses_total'] = 0
    _metrics_storage['latency_samples'].clear()


# ===========================
# Metric Recording Functions
# ===========================

def increment_requests_total(scope: str) -> None:
    """
    Increment total request counter for given scope.
    
    Args:
        scope: Leaderboard scope (tournament, season, all_time)
    
    Example:
        >>> increment_requests_total('tournament')
    """
    if scope not in _metrics_storage['requests_total']:
        _metrics_storage['requests_total'][scope] = 0
    _metrics_storage['requests_total'][scope] += 1


def increment_cache_hits() -> None:
    """
    Increment cache hit counter.
    
    Example:
        >>> increment_cache_hits()
    """
    _metrics_storage['cache_hits_total'] += 1


def increment_cache_misses() -> None:
    """
    Increment cache miss counter.
    
    Example:
        >>> increment_cache_misses()
    """
    _metrics_storage['cache_misses_total'] += 1


def record_latency(latency_ms: float, scope: str) -> None:
    """
    Record request latency sample.
    
    Args:
        latency_ms: Request duration in milliseconds
        scope: Leaderboard scope (tournament, season, all_time)
    
    Example:
        >>> record_latency(45.3, 'tournament')
    """
    _metrics_storage['latency_samples'].append((latency_ms, scope))
    
    # Keep only last 10,000 samples to prevent unbounded growth
    if len(_metrics_storage['latency_samples']) > 10000:
        _metrics_storage['latency_samples'] = _metrics_storage['latency_samples'][-10000:]


# ===========================
# Context Manager for Request Tracking
# ===========================

@contextmanager
def record_leaderboard_request(
    scope: str,
    source: Optional[str] = None
):
    """
    Context manager to automatically record request metrics.
    
    Args:
        scope: Leaderboard scope (tournament, season, all_time)
        source: Data source (cache, snapshot, live, disabled)
            - If 'cache': increment cache_hits_total
            - If 'snapshot' or 'live': increment cache_misses_total
            - If 'disabled': no cache metric recorded
    
    Yields:
        None
    
    Example:
        >>> with record_leaderboard_request(scope='tournament', source='cache'):
        ...     data = fetch_leaderboard()
        ...     # Metrics automatically recorded on context exit
    """
    start_time = time.perf_counter()
    
    try:
        yield
    finally:
        # Record latency
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        record_latency(duration_ms, scope)
        
        # Increment request counter
        increment_requests_total(scope)
        
        # Record cache hit/miss
        if source == 'cache':
            increment_cache_hits()
        elif source in ['snapshot', 'live']:
            increment_cache_misses()
        # If source='disabled', no cache metric recorded


# ===========================
# Prometheus Export (Future Enhancement)
# ===========================
# TODO: Integrate with Prometheus client library for production
# 
# from prometheus_client import Counter, Histogram
# 
# REQUESTS_TOTAL = Counter(
#     'leaderboards_requests_total',
#     'Total leaderboard requests',
#     ['scope']
# )
# 
# CACHE_HITS = Counter(
#     'leaderboards_cache_hits_total',
#     'Cache hit count'
# )
# 
# CACHE_MISSES = Counter(
#     'leaderboards_cache_misses_total',
#     'Cache miss count'
# )
# 
# LATENCY_HISTOGRAM = Histogram(
#     'leaderboards_latency_ms',
#     'Request latency in milliseconds',
#     ['scope'],
#     buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
# )
# 
# def increment_requests_total(scope: str) -> None:
#     REQUESTS_TOTAL.labels(scope=scope).inc()
# 
# def increment_cache_hits() -> None:
#     CACHE_HITS.inc()
# 
# def increment_cache_misses() -> None:
#     CACHE_MISSES.inc()
# 
# def record_latency(latency_ms: float, scope: str) -> None:
#     LATENCY_HISTOGRAM.labels(scope=scope).observe(latency_ms)
