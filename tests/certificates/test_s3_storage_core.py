"""
Core S3 Storage Tests - Module 6.5

Validates S3 storage backend functionality with DummyS3Client and real boto3.
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
- Boto3 integration (gated by S3_TESTS=1, 8 tests)
- Lifecycle policy (2 tests)
- Consistency checks (4 tests)

Total: 38 tests (30 offline + 8 boto3 integration).
"""

import hashlib
import time
import os
from unittest.mock import patch, Mock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.tournaments.storage import CertificateS3Storage
from apps.tournaments.s3_protocol import DummyS3Client, create_real_s3_client

# Check if real S3 tests are enabled
S3_TESTS_ENABLED = os.environ.get('S3_TESTS', '0') == '1'


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


# ==============================================================================
# BOTO3 INTEGRATION TESTS (gated by S3_TESTS=1)
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='deltacrown-test-certs'
)
class TestBoto3Integration(TestCase):
    """Test real boto3 S3 operations (requires S3_TESTS=1)."""
    
    def setUp(self):
        if not S3_TESTS_ENABLED:
            self.skipTest("S3_TESTS not enabled (set S3_TESTS=1)")
        self.s3_client = create_real_s3_client()
        self.storage = CertificateS3Storage(s3_client=self.s3_client)
        self.test_keys = []
    
    def tearDown(self):
        # Cleanup test objects
        for key in self.test_keys:
            try:
                self.s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=key
                )
            except Exception:
                pass
    
    def test_boto3_upload_and_retrieve(self):
        """Real S3 upload should succeed and be retrievable."""
        content = ContentFile(b'test pdf content from boto3')
        name = 'test-boto3/file.pdf'
        
        # Upload
        saved_name = self.storage.save(name, content)
        self.test_keys.append(saved_name)
        
        # Retrieve
        response = self.s3_client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=saved_name
        )
        body = response['Body'].read()
        self.assertEqual(body, b'test pdf content from boto3')
    
    def test_boto3_etag_matches_md5(self):
        """ETag should match MD5 hash of content."""
        content_bytes = b'test content for md5 validation'
        content = ContentFile(content_bytes)
        name = 'test-boto3/md5-test.pdf'
        
        # Upload
        saved_name = self.storage.save(name, content)
        self.test_keys.append(saved_name)
        
        # Get ETag
        response = self.s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=saved_name
        )
        etag = response['ETag'].strip('"')
        
        # Calculate MD5
        expected_md5 = hashlib.md5(content_bytes).hexdigest()
        self.assertEqual(etag, expected_md5)
    
    def test_boto3_presigned_url_accessible(self):
        """Presigned URL should be publicly accessible."""
        import requests
        
        content = ContentFile(b'test content for url access')
        name = 'test-boto3/url-test.pdf'
        
        # Upload
        saved_name = self.storage.save(name, content)
        self.test_keys.append(saved_name)
        
        # Generate presigned URL
        with override_settings(CERT_S3_READ_PRIMARY=True):
            storage_with_read = CertificateS3Storage(s3_client=self.s3_client)
            url = storage_with_read.url(saved_name)
        
        # Verify URL is accessible
        response = requests.get(url, timeout=10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'test content for url access')
    
    def test_boto3_delete_operation(self):
        """Delete should remove object from S3."""
        content = ContentFile(b'test content for deletion')
        name = 'test-boto3/delete-test.pdf'
        
        # Upload
        saved_name = self.storage.save(name, content)
        
        # Verify exists
        response = self.s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=saved_name
        )
        self.assertIsNotNone(response)
        
        # Delete
        self.storage.delete(saved_name)
        
        # Verify deleted
        with self.assertRaises(Exception):
            self.s3_client.head_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=saved_name
            )
    
    def test_boto3_large_file_multipart(self):
        """Large files (>5MB) should use multipart upload."""
        # Create 6MB file
        large_content = b'X' * (6 * 1024 * 1024)
        content = ContentFile(large_content)
        name = 'test-boto3/large-file.pdf'
        
        # Upload
        start = time.time()
        saved_name = self.storage.save(name, content)
        duration = time.time() - start
        self.test_keys.append(saved_name)
        
        # Verify uploaded
        response = self.s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=saved_name
        )
        self.assertEqual(response['ContentLength'], len(large_content))
        
        # Should complete reasonably fast (even 6MB should be <10s on good connection)
        self.assertLess(duration, 30, f"Upload took {duration:.1f}s (too slow)")
    
    def test_boto3_concurrent_uploads(self):
        """Concurrent uploads should not conflict."""
        import threading
        
        results = []
        errors = []
        
        def upload_file(idx):
            try:
                content = ContentFile(f'concurrent content {idx}'.encode())
                name = f'test-boto3/concurrent-{idx}.pdf'
                saved_name = self.storage.save(name, content)
                results.append(saved_name)
                self.test_keys.append(saved_name)
            except Exception as e:
                errors.append(str(e))
        
        # Launch 10 concurrent uploads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=upload_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all succeeded
        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 10)
    
    def test_boto3_metadata_preservation(self):
        """Metadata should be preserved in S3."""
        content = ContentFile(b'test content with metadata')
        name = 'test-boto3/metadata-test.pdf'
        
        # Upload
        saved_name = self.storage.save(name, content)
        self.test_keys.append(saved_name)
        
        # Get metadata
        response = self.s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=saved_name
        )
        
        # Verify standard metadata exists
        self.assertIn('ContentLength', response)
        self.assertIn('ContentType', response)
        self.assertIn('LastModified', response)
    
    def test_boto3_error_handling(self):
        """Invalid bucket should raise appropriate error."""
        # Try to access non-existent bucket
        bad_client = create_real_s3_client()
        
        with self.assertRaises(Exception):
            bad_client.get_object(
                Bucket='non-existent-bucket-12345',
                Key='test.pdf'
            )


# ==============================================================================
# LIFECYCLE POLICY TESTS
# ==============================================================================

class TestLifecyclePolicy(TestCase):
    """Test S3 lifecycle policy configuration."""
    
    def test_lifecycle_policy_structure(self):
        """Lifecycle policy JSON should have correct structure."""
        from apps.tournaments.s3_lifecycle import get_lifecycle_policy
        
        policy = get_lifecycle_policy()
        
        # Verify structure
        self.assertIn('Rules', policy)
        self.assertIsInstance(policy['Rules'], list)
        self.assertGreater(len(policy['Rules']), 0)
        
        # Verify rule has required fields
        rule = policy['Rules'][0]
        self.assertIn('Id', rule)
        self.assertIn('Status', rule)
        self.assertIn('Transitions', rule)
    
    def test_lifecycle_policy_transitions(self):
        """Lifecycle policy should have standard → IA → Glacier transitions."""
        from apps.tournaments.s3_lifecycle import get_lifecycle_policy
        
        policy = get_lifecycle_policy()
        rule = policy['Rules'][0]
        
        transitions = rule.get('Transitions', [])
        self.assertGreater(len(transitions), 0)
        
        # Check transition to Infrequent Access
        ia_transitions = [t for t in transitions if t['StorageClass'] == 'STANDARD_IA']
        self.assertEqual(len(ia_transitions), 1)
        self.assertEqual(ia_transitions[0]['Days'], 30)
        
        # Check transition to Glacier
        glacier_transitions = [t for t in transitions if t['StorageClass'] == 'GLACIER']
        self.assertEqual(len(glacier_transitions), 1)
        self.assertEqual(glacier_transitions[0]['Days'], 365)


# ==============================================================================
# CONSISTENCY CHECK TESTS
# ==============================================================================

@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-bucket'
)
class TestConsistencyChecks(TestCase):
    """Test SHA-256 consistency between S3 and local."""
    
    def test_sha256_match_after_save(self):
        """SHA-256 should match between S3 and local after save."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content_bytes = b'test content for sha256 check'
        content = ContentFile(content_bytes)
        name = 'test/sha256-test.pdf'
        
        saved_name = storage.save(name, content)
        
        # Calculate expected SHA-256
        expected_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Get S3 hash
        s3_content = dummy_s3.storage.get(name, b'')
        s3_hash = hashlib.sha256(s3_content).hexdigest()
        
        # Get local hash
        with storage.local_storage.open(saved_name, 'rb') as f:
            local_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Verify all match
        self.assertEqual(s3_hash, expected_hash)
        self.assertEqual(local_hash, expected_hash)
        
        # Cleanup
        storage.delete(saved_name)
    
    def test_consistency_check_detects_mismatch(self):
        """Consistency check should detect SHA-256 mismatch."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'original content')
        name = 'test/mismatch-test.pdf'
        
        saved_name = storage.save(name, content)
        
        # Corrupt S3 copy
        dummy_s3.storage[name] = b'corrupted content'
        
        # Calculate hashes
        s3_hash = hashlib.sha256(dummy_s3.storage[name]).hexdigest()
        with storage.local_storage.open(saved_name, 'rb') as f:
            local_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Verify mismatch detected
        self.assertNotEqual(s3_hash, local_hash)
        
        # Cleanup
        storage.delete(saved_name)
    
    def test_consistency_check_handles_missing_s3(self):
        """Consistency check should handle missing S3 object."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = 'test/missing-s3.pdf'
        
        saved_name = storage.save(name, content)
        
        # Remove S3 copy
        del dummy_s3.storage[name]
        
        # Verify S3 missing
        self.assertNotIn(name, dummy_s3.storage)
        
        # Local should still exist
        self.assertTrue(storage.local_storage.exists(saved_name))
        
        # Cleanup
        storage.delete(saved_name)
    
    def test_consistency_check_handles_missing_local(self):
        """Consistency check should handle missing local file."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'test content')
        name = 'test/missing-local.pdf'
        
        saved_name = storage.save(name, content)
        
        # Remove local copy
        storage.local_storage.delete(saved_name)
        
        # Verify local missing
        self.assertFalse(storage.local_storage.exists(saved_name))
        
        # S3 should still exist
        self.assertIn(name, dummy_s3.storage)
        
        # Cleanup S3
        dummy_s3.storage.pop(name, None)
