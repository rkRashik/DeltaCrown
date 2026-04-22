"""Dry-run rehearsal utilities for S3 certificate migration.

Provides a lightweight `DryRunStats` helper used by tests to track
latencies, byte counts, hash match statistics and simple decision
metrics without requiring AWS credentials.
"""
from __future__ import annotations

from typing import List, Dict
import math


class DryRunStats:
    """Collect simple performance and correctness metrics for a dry run.

    Methods are intentionally small and deterministic to make unit tests
    straightforward and stable.
    """

    def __init__(self) -> None:
        self.upload_times: List[float] = []
        self.url_gen_times: List[float] = []
        self.total_bytes: int = 0
        self.hash_matches: int = 0
        self.hash_mismatches: int = 0
        self.errors: List[str] = []

    def add_upload(self, duration_ms: float, byte_count: int) -> None:
        self.upload_times.append(float(duration_ms))
        try:
            self.total_bytes += int(byte_count)
        except Exception:
            # be forgiving for tests that may pass non-int types
            self.total_bytes += int(float(byte_count))

    def add_url_gen(self, duration_ms: float) -> None:
        self.url_gen_times.append(float(duration_ms))

    def add_hash_match(self) -> None:
        self.hash_matches += 1

    def add_hash_mismatch(self) -> None:
        self.hash_mismatches += 1

    def add_error(self, message: str) -> None:
        self.errors.append(str(message))

    @staticmethod
    def get_percentile(values: List[float], percentile: float) -> float:
        """Return the percentile value using linear interpolation.

        - Empty list -> 0
        - Single value -> that value
        - Otherwise use interpolation between sorted neighbors
        """
        if not values:
            return 0
        vals = sorted(float(v) for v in values)
        n = len(vals)
        if n == 1:
            return vals[0]
        # Position in 0..n-1
        idx = percentile * (n - 1)
        low = int(math.floor(idx))
        high = int(math.ceil(idx))
        if low == high:
            return vals[low]
        frac = idx - low
        return vals[low] + frac * (vals[high] - vals[low])

    def get_summary(self) -> Dict[str, float]:
        total_objects = len(self.upload_times)
        total_bytes = int(self.total_bytes)
        total_mb = total_bytes / (1024.0 * 1024.0)

        upload_p50 = self.get_percentile(self.upload_times, 0.50)
        upload_p95 = self.get_percentile(self.upload_times, 0.95)
        upload_p99 = self.get_percentile(self.upload_times, 0.99)

        url_p95 = self.get_percentile(self.url_gen_times, 0.95)
        url_p99 = self.get_percentile(self.url_gen_times, 0.99)

        total_hash = self.hash_matches + self.hash_mismatches
        if total_hash:
            hash_success_rate = (self.hash_matches / total_hash) * 100.0
        else:
            hash_success_rate = 100.0

        return {
            'total_objects': total_objects,
            'total_bytes': total_bytes,
            'total_mb': total_mb,
            'upload_p50': upload_p50,
            'upload_p95': upload_p95,
            'upload_p99': upload_p99,
            'url_p95': url_p95,
            'url_p99': url_p99,
            'hash_matches': self.hash_matches,
            'hash_mismatches': self.hash_mismatches,
            'hash_success_rate': hash_success_rate,
            'errors': len(self.errors),
        }


__all__ = ['DryRunStats']
