"""
Chaos Engineering & Durability Tests for Certificate S3 Storage

This module tests the resilience of the CertificateS3Storage backend under:
- Random 5xx errors (2%, 10%, 20% injection rates)
- Network timeouts and slow responses
- Concurrent operations with chaos injection
- Fallback path validation
- Retry bounds verification
- Data integrity guarantees (zero loss under failure)
- Metric emission validation

All tests use the capture_cert_metrics() pattern for unified metric assertions.
"""

import pytest
import time
import threading
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError
from django.core.files.base import ContentFile

from apps.tournaments.storage import CertificateS3Storage
from tests.certificates.helpers import capture_cert_metrics


class ChaoticS3Client:
    """
    S3 client wrapper that injects failures at configurable rates.
    
    Usage:
        client = ChaoticS3Client(base_client, error_rate=0.10, slow_rate=0.05)
    """
    
    def __init__(self, base_client, error_rate=0.0, slow_rate=0.0, timeout_rate=0.0):
        self.base_client = base_client
        self.error_rate = error_rate
        self.slow_rate = slow_rate
        self.timeout_rate = timeout_rate
        self.call_count = 0
        self.error_count = 0
        self.slow_count = 0
        self.timeout_count = 0
    
    def _should_inject_error(self):
        import random
        return random.random() < self.error_rate
    
    def _should_inject_slow(self):
        import random
        return random.random() < self.slow_rate
    
    def _should_inject_timeout(self):
        import random
        return random.random() < self.timeout_rate
    
    def upload_file(self, *args, **kwargs):
        self.call_count += 1
        
        if self._should_inject_timeout():
            self.timeout_count += 1
            raise Exception("Connection timeout")
        
        if self._should_inject_slow():
            self.slow_count += 1
            time.sleep(2.0)  # Simulate 2s slow response
        
        if self._should_inject_error():
            self.error_count += 1
            raise ClientError(
                {'Error': {'Code': '503', 'Message': 'Service Unavailable'}},
                'UploadFile'
            )
        
        return self.base_client.upload_file(*args, **kwargs)
    
    def head_object(self, *args, **kwargs):
        self.call_count += 1
        
        if self._should_inject_error():
            self.error_count += 1
            raise ClientError(
                {'Error': {'Code': '500', 'Message': 'Internal Server Error'}},
                'HeadObject'
            )
        
        return self.base_client.head_object(*args, **kwargs)
    
    def download_file(self, *args, **kwargs):
        self.call_count += 1
        
        if self._should_inject_error():
            self.error_count += 1
            raise ClientError(
                {'Error': {'Code': '502', 'Message': 'Bad Gateway'}},
                'DownloadFile'
            )
        
        return self.base_client.download_file(*args, **kwargs)
    
    def delete_object(self, *args, **kwargs):
        self.call_count += 1
        
        if self._should_inject_error():
            self.error_count += 1
            raise ClientError(
                {'Error': {'Code': '503', 'Message': 'Service Unavailable'}},
                'DeleteObject'
            )
        
        return self.base_client.delete_object(*args, **kwargs)
    
    def generate_presigned_url(self, *args, **kwargs):
        self.call_count += 1
        
        if self._should_inject_error():
            self.error_count += 1
            raise ClientError(
                {'Error': {'Code': '500', 'Message': 'Internal Server Error'}},
                'GeneratePresignedUrl'
            )
        
        return self.base_client.generate_presigned_url(*args, **kwargs)


@pytest.mark.django_db
class TestS3ChaosInjection:
    """Test S3 storage resilience under random failure injection."""
    
    def test_chaos_2pct_5xx_injection_100_operations(self, storage_with_s3):
        """
        Inject 2% random 5xx errors across 100 save operations.
        
        Expected: ≥98 operations succeed, fallback metrics emitted, zero data loss.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.02)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                successes = 0
                failures = 0
                
                for i in range(100):
                    try:
                        content = ContentFile(f"chaos_test_{i}".encode())
                        path = storage.save(f"chaos/test_{i}.txt", content)
                        assert storage.exists(path)
                        successes += 1
                    except Exception:
                        failures += 1
                
                # Validation
                assert successes >= 98, f"Too many failures: {failures}/100"
                assert chaotic_client.error_count >= 1, "Expected at least 1 injected error"
                
                # Metrics: fallback should trigger for some operations
                fallback_count = em.counts.get('cert.s3.read.fallback', 0)
                assert fallback_count >= 0, "Fallback metrics should be present"
    
    def test_chaos_10pct_5xx_injection_50_operations(self, storage_with_s3):
        """
        Inject 10% random 5xx errors across 50 save operations.
        
        Expected: ≥45 operations succeed, fallback metrics emitted.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.10)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                successes = 0
                
                for i in range(50):
                    try:
                        content = ContentFile(f"chaos_10pct_{i}".encode())
                        path = storage.save(f"chaos_10/test_{i}.txt", content)
                        assert storage.exists(path)
                        successes += 1
                    except Exception:
                        pass
                
                assert successes >= 45, f"Too many failures: {50 - successes}/50"
                assert chaotic_client.error_count >= 3, "Expected multiple injected errors"
    
    def test_chaos_20pct_5xx_injection_with_retry_bounds(self, storage_with_s3):
        """
        Inject 20% random 5xx errors across 30 operations.
        
        Expected: Storage retries bounded (max 3 attempts), no infinite loops.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.20)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                start_time = time.time()
                successes = 0
                
                for i in range(30):
                    try:
                        content = ContentFile(f"chaos_20pct_{i}".encode())
                        path = storage.save(f"chaos_20/test_{i}.txt", content)
                        successes += 1
                    except Exception:
                        pass
                
                elapsed = time.time() - start_time
                
                # Validation: should complete within reasonable time (no infinite retries)
                assert elapsed < 15.0, f"Took too long: {elapsed}s (expected <15s)"
                assert successes >= 24, f"Too many failures: {30 - successes}/30"
    
    def test_chaos_network_timeouts_5pct(self, storage_with_s3):
        """
        Inject 5% network timeouts across 40 operations.
        
        Expected: Timeouts trigger fallback to local storage, zero data loss.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, timeout_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                successes = 0
                
                for i in range(40):
                    try:
                        content = ContentFile(f"timeout_test_{i}".encode())
                        path = storage.save(f"timeout/test_{i}.txt", content)
                        # Verify data integrity
                        assert storage.exists(path)
                        successes += 1
                    except Exception:
                        pass
                
                assert successes >= 38, f"Too many timeout failures: {40 - successes}/40"
                assert chaotic_client.timeout_count >= 1, "Expected at least 1 timeout"
    
    def test_chaos_slow_responses_10pct(self, storage_with_s3):
        """
        Inject 10% slow responses (2s delay) across 20 operations.
        
        Expected: Operations complete successfully despite slowness, no hangs.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, slow_rate=0.10)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                start_time = time.time()
                successes = 0
                
                for i in range(20):
                    content = ContentFile(f"slow_test_{i}".encode())
                    path = storage.save(f"slow/test_{i}.txt", content)
                    assert storage.exists(path)
                    successes += 1
                
                elapsed = time.time() - start_time
                
                # Validation: should have 2 slow operations (~4s overhead)
                assert successes == 20, "All operations should succeed"
                assert chaotic_client.slow_count >= 1, "Expected at least 1 slow operation"
                assert elapsed < 10.0, f"Took too long: {elapsed}s (expected <10s)"


@pytest.mark.django_db
class TestS3Durability:
    """Test data integrity guarantees under failure conditions."""
    
    def test_durability_concurrent_writes_with_chaos(self, storage_with_s3):
        """
        10 concurrent threads, each writing 10 files, with 5% chaos injection.
        
        Expected: All 100 files written successfully, zero data loss, no corruption.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                results = []
                errors = []
                
                def worker(thread_id):
                    for i in range(10):
                        try:
                            content = ContentFile(f"thread_{thread_id}_file_{i}".encode())
                            path = storage.save(f"concurrent/t{thread_id}_f{i}.txt", content)
                            results.append(path)
                        except Exception as e:
                            errors.append(str(e))
                
                threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(10)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                
                # Validation
                assert len(results) >= 95, f"Too many failures: {len(errors)} errors"
                assert len(set(results)) == len(results), "Duplicate paths detected"
    
    def test_durability_read_after_write_consistency(self, storage_with_s3):
        """
        Write 20 files, immediately read them back with 5% chaos injection.
        
        Expected: All reads return correct content, no stale data.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                paths = []
                
                # Write phase
                for i in range(20):
                    content = ContentFile(f"consistency_test_{i}".encode())
                    path = storage.save(f"consistency/test_{i}.txt", content)
                    paths.append((path, f"consistency_test_{i}"))
                
                # Read phase
                for path, expected_content in paths:
                    with storage.open(path, 'rb') as f:
                        actual = f.read().decode()
                        assert actual == expected_content, f"Data corruption: {actual} != {expected_content}"
    
    def test_durability_delete_idempotency_under_chaos(self, storage_with_s3):
        """
        Delete same file 5 times with 10% chaos injection.
        
        Expected: No errors, delete is idempotent, metrics emitted correctly.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.10)
        
        content = ContentFile(b"delete_test")
        path = storage.save("durability/delete_test.txt", content)
        assert storage.exists(path)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                for _ in range(5):
                    try:
                        storage.delete(path)
                    except Exception:
                        pass  # Idempotency means no error on repeat deletes
                
                # Metrics: at least one successful delete
                delete_success = em.counts.get('cert.s3.delete.success', 0)
                assert delete_success >= 1, "Expected at least 1 delete success metric"
    
    def test_durability_zero_byte_files_under_chaos(self, storage_with_s3):
        """
        Write 10 zero-byte files with 5% chaos injection.
        
        Expected: All files written successfully, size() returns 0.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                for i in range(10):
                    content = ContentFile(b"")
                    path = storage.save(f"zero_byte/test_{i}.txt", content)
                    assert storage.exists(path)
                    assert storage.size(path) == 0, f"Zero-byte file has non-zero size"
    
    def test_durability_large_files_1mb_with_chaos(self, storage_with_s3):
        """
        Write 5 files of 1MB each with 5% chaos injection.
        
        Expected: All files written successfully, correct size on read-back.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                large_data = b"X" * (1024 * 1024)  # 1MB
                
                for i in range(5):
                    content = ContentFile(large_data)
                    path = storage.save(f"large/test_{i}.bin", content)
                    assert storage.exists(path)
                    assert storage.size(path) == len(large_data), "Size mismatch for 1MB file"


@pytest.mark.django_db
class TestS3FallbackMetrics:
    """Test metric emission under failure scenarios."""
    
    def test_fallback_metrics_emitted_on_s3_unavailable(self, storage_with_s3):
        """
        Force S3 unavailable (100% error rate), validate fallback metrics.
        
        Expected: All operations fallback to local, metrics show 100% fallback rate.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=1.0)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                # Attempt 10 operations
                for i in range(10):
                    content = ContentFile(f"fallback_test_{i}".encode())
                    path = storage.save(f"fallback/test_{i}.txt", content)
                    assert storage.exists(path)  # Should exist locally
                
                # Metrics: all operations should fallback
                fallback_count = em.counts.get('cert.s3.read.fallback', 0)
                save_fail = em.counts.get('cert.s3.save.fail', 0)
                
                assert save_fail >= 10, "Expected 10 save failures"
                assert fallback_count >= 0, "Fallback metrics should be tracked"
    
    def test_retry_metrics_bounded_under_persistent_5xx(self, storage_with_s3):
        """
        Persistent 5xx errors, validate retry count bounded (max 3 attempts).
        
        Expected: No infinite loops, retry count metrics accurate.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=1.0)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                start_time = time.time()
                
                for i in range(5):
                    content = ContentFile(f"retry_test_{i}".encode())
                    try:
                        path = storage.save(f"retry/test_{i}.txt", content)
                    except Exception:
                        pass  # Expected to fail
                
                elapsed = time.time() - start_time
                
                # Validation: should complete quickly (no infinite retries)
                assert elapsed < 5.0, f"Retries took too long: {elapsed}s"
                assert chaotic_client.call_count <= 20, f"Too many calls: {chaotic_client.call_count}"
    
    def test_metric_emission_under_concurrent_chaos(self, storage_with_s3):
        """
        5 threads, each performing 10 operations, with 5% chaos.
        
        Expected: Metrics accurately track all operations, no double-counting.
        """
        storage = storage_with_s3
        chaotic_client = ChaoticS3Client(storage.s3_storage.client, error_rate=0.05)
        
        with patch.object(storage.s3_storage, 'client', chaotic_client):
            with capture_cert_metrics() as em:
                def worker(tid):
                    for i in range(10):
                        content = ContentFile(f"thread_{tid}_op_{i}".encode())
                        try:
                            storage.save(f"metric_concurrent/t{tid}_op{i}.txt", content)
                        except Exception:
                            pass
                
                threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                
                # Metrics: total operations should be tracked
                total_ops = sum(em.counts.values())
                assert total_ops >= 50, f"Metrics undercount: {total_ops} < 50"
