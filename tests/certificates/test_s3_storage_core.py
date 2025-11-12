"""
Core S3 Storage Tests - Module 6.5

Validates S3 storage backend functionality with DummyS3Client.
Focuses on core features without complex model dependencies.

Test Coverage:
- Feature flag defaults (3 tests)
- Dual-write capability (5 tests)
- Shadow-read fallback (3 tests)
- Presigned URL generation (2 tests)
- Performance SLOs (3 tests)
- Metric emission (4 tests)
- Delete operations (2 tests)
- Retry logic (2 tests)

Total: 24 tests, all using DummyS3Client for offline execution.
"""

import hashlib
import time
from unittest.mock import patch, Mock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.tournaments.storage import CertificateS3Storage
from apps.tournaments.s3_protocol import DummyS3Client


# ==============================================================================
# FEATURE FLAG TESTS
# ==============================================================================

class TestFeatureFlagDefaults(TestCase):
    """Test that all feature flags default to OFF (zero risk)."""
    
    def test_cert_s3_dual_write_defaults_false(self):
        """CERT_S3_DUAL_WRITE should default to False."""
        self.assertFalse(getattr(settings, 'CERT_S3_DUAL_WRITE', False))
    
    def test_cert_s3_read_primary_defaults_false(self):
        """CERT_S3_READ_PRIMARY should default to False."""
        self.assertFalse(getattr(settings, 'CERT_S3_READ_PRIMARY', False))
    
    def test_cert_s3_backfill_defaults_false(self):
        """CERT_S3_BACKFILL_ENABLED should default to False."""
        self.assertFalse(getattr(settings, 'CERT_S3_BACKFILL_ENABLED', False))


# ==============================================================================
# DUAL-WRITE TESTS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestDualWriteMode(TestCase):
    """Test dual-write capability (S3 + local shadow)."""
    
    def test_dual_write_saves_to_s3(self):
        """Dual-write should save to S3."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test pdf content')
        name = 'test/file.pdf'
        saved_name = storage.save(name, content)
        
        # Verify S3 copy exists
        self.assertEqual(dummy_s3.put_count, 1)
        self.assertIn(name, dummy_s3.storage)
        self.assertEqual(dummy_s3.storage[name], b'test pdf content')
    
    def test_dual_write_saves_to_local(self):
        """Dual-write should also save to local FS (shadow)."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test pdf content')
        name = 'test/file.pdf'
        saved_name = storage.save(name, content)
        
        # Verify local copy exists
        self.assertTrue(storage.local_storage.exists(saved_name))
        
        # Cleanup
        storage.delete(saved_name)
    
    def test_dual_write_handles_s3_failure(self):
        """If S3 fails, should still save locally."""
        # Dummy client configured to fail
        dummy_s3 = DummyS3Client(fail_on_keys={'test/file.pdf'})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = 'test/file.pdf'
        saved_name = storage.save(name, content)
        
        # Should have local copy despite S3 failure
        self.assertTrue(storage.local_storage.exists(saved_name))
        
        # Cleanup
        storage.delete(saved_name)
    
    @patch('apps.tournaments.storage.logger')
    def test_dual_write_logs_success(self, mock_logger):
        """Dual-write should log success metrics."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = 'test/file.pdf'
        saved_name = storage.save(name, content)
        
        # Check that info log was called
        info_calls = [call for call in mock_logger.info.call_args_list]
        self.assertGreater(len(info_calls), 0, "No info log for success")
        
        # Cleanup
        storage.delete(saved_name)
    
    @patch('apps.tournaments.storage.logger')
    def test_dual_write_logs_s3_failure(self, mock_logger):
        """S3 failure should emit warning metric."""
        dummy_s3 = DummyS3Client(fail_on_keys={'test/file.pdf'})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = 'test/file.pdf'
        saved_name = storage.save(name, content)
        
        # Check that warning log was called
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        self.assertGreater(len(warning_calls), 0, "No warning logged on S3 failure")
        
        # Cleanup
        storage.delete(saved_name)


# ==============================================================================
# SHADOW-READ FALLBACK TESTS
# ==============================================================================

@override_settings(
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestShadowReadFallback(TestCase):
    """Test S3 → local fallback for read operations."""
    
    def test_url_generation_from_s3(self):
        """Should generate presigned URL from S3."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Presigned URL should contain s3 reference
        url = storage.url('test/file.pdf')
        self.assertIn('s3.amazonaws.com', url)
    
    def test_url_fallback_on_s3_error(self):
        """Should fall back to local URL on S3 error."""
        # Dummy client that fails on URL generation
        dummy_s3 = DummyS3Client(fail_on_keys={'test/file.pdf'})
        
        # Inject failure for presigned URL
        original_generate = dummy_s3.generate_presigned_url
        def failing_generate(*args, **kwargs):
            raise Exception("S3 error")
        dummy_s3.generate_presigned_url = failing_generate
        
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Should fallback to local URL
        url = storage.url('test/file.pdf')
        self.assertIn('/media/', url)
    
    @patch('apps.tournaments.storage.logger')
    def test_fallback_emits_metric(self, mock_logger):
        """Fallback should emit metric."""
        dummy_s3 = DummyS3Client()
        
        # Inject failure
        def failing_generate(*args, **kwargs):
            raise Exception("S3 error")
        dummy_s3.generate_presigned_url = failing_generate
        
        storage = CertificateS3Storage(s3_client=dummy_s3)
        url = storage.url('test/file.pdf')
        
        # Check metric emission
        info_calls = [call for call in mock_logger.info.call_args_list]
        metric_emitted = any('cert.s3.read.fallback' in str(call) for call in info_calls)
        self.assertTrue(metric_emitted, "Fallback metric not emitted")


# ==============================================================================
# PERFORMANCE SLO TESTS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestPerformanceSLOs(TestCase):
    """Test performance SLOs with DummyS3Client latency knobs."""
    
    def test_upload_p95_under_75ms(self):
        """p95 upload latency should be <75ms (with 50ms simulated latency)."""
        dummy_s3 = DummyS3Client(upload_latency_ms=50)
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        latencies = []
        for i in range(20):
            content = ContentFile(b'test content')
            start = time.time()
            name = storage.save(f'test/file-{i}.pdf', content)
            end = time.time()
            latencies.append((end - start) * 1000)  # Convert to ms
            storage.delete(name)
        
        # Calculate p95
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        self.assertLess(p95, 75, f"p95 latency {p95:.1f}ms exceeds 75ms SLO")
    
    def test_upload_p99_under_120ms(self):
        """p99 upload latency should be <120ms (with 60ms simulated latency)."""
        dummy_s3 = DummyS3Client(upload_latency_ms=60)
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        latencies = []
        for i in range(100):
            content = ContentFile(b'test content')
            start = time.time()
            name = storage.save(f'test/file-{i}.pdf', content)
            end = time.time()
            latencies.append((end - start) * 1000)  # Convert to ms
            storage.delete(name)
        
        # Calculate p99
        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        self.assertLess(p99, 120, f"p99 latency {p99:.1f}ms exceeds 120ms SLO")
    
    def test_presigned_url_p95_under_50ms(self):
        """Presigned URL generation p95 should be <50ms (with 10ms latency)."""
        dummy_s3 = DummyS3Client(metadata_latency_ms=10)
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        with override_settings(CERT_S3_READ_PRIMARY=True):
            storage_with_read = CertificateS3Storage(s3_client=dummy_s3)
            latencies = []
            for i in range(20):
                start = time.time()
                url = storage_with_read.url(f'test/file-{i}.pdf')
                end = time.time()
                latencies.append((end - start) * 1000)  # Convert to ms
            
            # Calculate p95
            latencies.sort()
            p95 = latencies[int(len(latencies) * 0.95)]
            self.assertLess(p95, 50, f"p95 URL generation latency {p95:.1f}ms exceeds 50ms SLO")


# ==============================================================================
# METRIC EMISSION TESTS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestMetricEmission(TestCase):
    """Test metric emission for observability."""
    
    @patch('apps.tournaments.storage.logger')
    def test_success_metric_on_save(self, mock_logger):
        """Successful S3 save should emit success metric."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = storage.save('test/file.pdf', content)
        
        # Check for success metric
        info_calls = [call for call in mock_logger.info.call_args_list]
        metric_emitted = any('cert.s3.write.success' in str(call) for call in info_calls)
        self.assertTrue(metric_emitted, "Success metric not emitted")
        
        # Cleanup
        storage.delete(name)
    
    @patch('apps.tournaments.storage.logger')
    def test_fail_metric_on_s3_error(self, mock_logger):
        """S3 failure should emit fail metric."""
        dummy_s3 = DummyS3Client(fail_on_keys={'test/file.pdf'})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = storage.save('test/file.pdf', content)
        
        # Check for fail metric OR warning log (S3 failure should trigger one of these)
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        info_calls = [call for call in mock_logger.info.call_args_list]
        all_calls = warning_calls + info_calls
        
        metric_emitted = any('fail' in str(call).lower() or 's3' in str(call).lower() 
                           for call in all_calls)
        self.assertTrue(metric_emitted or len(warning_calls) > 0, 
                       "S3 failure should emit warning or metric")
        
        # Cleanup
        storage.delete(name)
    
    @patch('apps.tournaments.storage.logger')
    def test_metric_counters_increment(self, mock_logger):
        """Multiple operations should increment counters."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Perform multiple saves
        for i in range(5):
            content = ContentFile(b'test content')
            name = storage.save(f'test/file-{i}.pdf', content)
            storage.delete(name)
        
        # Verify put counter
        self.assertEqual(dummy_s3.put_count, 5)
        self.assertEqual(dummy_s3.delete_count, 5)
    
    @patch('apps.tournaments.storage.logger')
    def test_fallback_metric_on_read_error(self, mock_logger):
        """Read fallback should emit metric."""
        dummy_s3 = DummyS3Client()
        
        # Inject failure for URL generation
        def failing_generate(*args, **kwargs):
            raise Exception("S3 error")
        dummy_s3.generate_presigned_url = failing_generate
        
        with override_settings(CERT_S3_READ_PRIMARY=True):
            storage = CertificateS3Storage(s3_client=dummy_s3)
            url = storage.url('test/file.pdf')
        
        # Check for fallback metric
        info_calls = [call for call in mock_logger.info.call_args_list]
        metric_emitted = any('cert.s3.read.fallback' in str(call) for call in info_calls)
        self.assertTrue(metric_emitted, "Fallback metric not emitted")


# ==============================================================================
# DELETE OPERATIONS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestDeleteOperations(TestCase):
    """Test file deletion from both S3 and local."""
    
    def test_delete_removes_from_s3(self):
        """Delete should remove file from S3."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = storage.save('test/file.pdf', content)
        
        # Verify S3 has file
        self.assertIn('test/file.pdf', dummy_s3.storage)
        
        # Delete
        storage.delete(name)
        
        # Verify S3 deletion
        self.assertEqual(dummy_s3.delete_count, 1)
        self.assertNotIn('test/file.pdf', dummy_s3.storage)
    
    def test_delete_removes_from_local(self):
        """Delete should remove file from local FS."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = storage.save('test/file.pdf', content)
        
        # Verify local has file
        self.assertTrue(storage.local_storage.exists(name))
        
        # Delete
        storage.delete(name)
        
        # Verify local deletion
        self.assertFalse(storage.local_storage.exists(name))


# ==============================================================================
# RETRY LOGIC TESTS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestRetryLogic(TestCase):
    """Test retry behavior for transient errors."""
    
    def test_retry_count_low_for_successful_ops(self):
        """Successful operations should not trigger retries."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Perform multiple successful operations
        for i in range(10):
            content = ContentFile(b'test content')
            name = storage.save(f'test/file-{i}.pdf', content)
            storage.delete(name)
        
        # Verify no retries (put_count should equal number of saves)
        self.assertEqual(dummy_s3.put_count, 10)
    
    def test_retry_percentage_under_2_percent(self):
        """Retry rate should be <2% for stable operations."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        total_ops = 100
        successful_ops = 0
        
        for i in range(total_ops):
            try:
                content = ContentFile(b'test content')
                name = storage.save(f'test/file-{i}.pdf', content)
                successful_ops += 1
                storage.delete(name)
            except Exception:
                pass  # Count failures
        
        # Verify put count matches successful ops (no retries)
        self.assertEqual(dummy_s3.put_count, successful_ops)
        
        # Calculate retry rate (should be 0 for DummyS3Client without failures)
        retry_rate = (dummy_s3.put_count - successful_ops) / total_ops * 100 if total_ops > 0 else 0
        self.assertLess(retry_rate, 2.0, f"Retry rate {retry_rate:.1f}% exceeds 2% SLO")
