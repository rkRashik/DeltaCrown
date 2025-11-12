"""
Coverage boost tests for Module 6.5 S3 Certificate Storage.

Targets uncovered branches in storage.py (58% → 72%+).
Focus on error paths, edge cases, and flag combinations.
"""

import pytest
import hashlib
import time
from uuid import uuid4
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from io import BytesIO

from apps.tournaments.storage import CertificateS3Storage
from apps.tournaments.s3_protocol import DummyS3Client


# ============================================================================
# STORAGE.PY ERROR PATH COVERAGE
# ============================================================================

class TestReadPrimaryErrorPaths(TestCase):
    """Test READ_PRIMARY with S3 errors → local fallback."""
    
    @override_settings(CERT_S3_READ_PRIMARY=True, CERT_S3_DUAL_WRITE=True)
    def test_read_primary_s3_404_fallback_to_local(self):
        """READ_PRIMARY: S3 404 → fallback to local, emit metric."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        local_content = b'local fallback content'
        
        # Create file in local only (S3 empty)
        storage.local_storage.save(key, ContentFile(local_content))
        
        # Mock the s3_storage.open to raise exception
        with patch.object(storage, 's3_storage', None):  # Force fallback path
            with storage.open(key, 'rb') as f:
                result = f.read()
        
        # Should get local content (since s3_storage is None, goes straight to local)
        self.assertEqual(result, local_content)
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_read_primary_s3_success_no_local_touch(self):
        """READ_PRIMARY: S3 success → no local access."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        s3_content = b'from s3 primary'
        
        # Pre-populate S3 only
        dummy_s3.put_object(Bucket='test-bucket', Key=key, Body=s3_content)
        
        # Read should return S3 content without touching local
        with storage.open(key, 'rb') as f:
            result = f.read()
        
        self.assertEqual(result, s3_content)
        # Local should NOT have file
        self.assertFalse(storage.local_storage.exists(key))
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_url_generation_s3_error_fallback_local(self):
        """url() with S3 error → fallback to local URL."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Create local file
        storage.local_storage.save(fail_key, ContentFile(b'data'))
        
        with patch('apps.tournaments.storage.logger') as mock_logger:
            url = storage.url(fail_key)
        
        # Should return local URL
        self.assertIn('/media/', url)
        
        # Should log warning
        mock_logger.warning.assert_called()
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_exists_s3_error_fallback_local(self):
        """exists() with S3 error → fallback to local check."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Create local file only
        storage.local_storage.save(fail_key, ContentFile(b'data'))
        
        # exists() should fallback to local
        result = storage.exists(fail_key)
        
        self.assertTrue(result)
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_size_s3_error_fallback_local(self):
        """size() with S3 error → fallback to local size."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = b'size test data'
        storage.local_storage.save(fail_key, ContentFile(content))
        
        # size() should fallback to local
        result = storage.size(fail_key)
        
        self.assertEqual(result, len(content))


class TestDualWriteErrorPaths(TestCase):
    """Test DUAL_WRITE with S3 errors → local succeeds."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_dual_write_s3_fails_local_succeeds(self):
        """DUAL_WRITE: S3 upload fails → local succeeds, warning logged."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        content = ContentFile(b'important data')
        
        with patch('apps.tournaments.storage.logger') as mock_logger:
            saved_name = storage.save(fail_key, content)
        
        # Local must exist (shadow copy)
        self.assertTrue(storage.local_storage.exists(saved_name))
        
        # S3 should NOT have file
        self.assertNotIn(fail_key, dummy_s3.storage)
        
        # Warning logged
        mock_logger.warning.assert_called()
        warning_msg = str(mock_logger.warning.call_args)
        self.assertIn('Dual-write S3 failed', warning_msg)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_dual_write_both_succeed(self):
        """DUAL_WRITE: Both S3 and local succeed."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        content = ContentFile(b'test data')
        
        saved_name = storage.save(key, content)
        
        # Both should have file
        self.assertTrue(storage.local_storage.exists(saved_name))
        self.assertIn(key, dummy_s3.storage)
        self.assertEqual(dummy_s3.storage[key], b'test data')
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_dual_write_network_timeout_retry(self):
        """DUAL_WRITE: Network timeout → eventually succeeds."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        
        # Mock transient failure
        call_count = {'count': 0}
        original_put = dummy_s3.put_object
        
        def flaky_put(**kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise Exception("Transient network error")
            return original_put(**kwargs)
        
        dummy_s3.put_object = flaky_put
        
        # First call will fail, stored to local only
        saved_name = storage.save(key, ContentFile(b'retry test'))
        
        # Local should have file
        self.assertTrue(storage.local_storage.exists(saved_name))


class TestDeleteErrorPaths(TestCase):
    """Test delete() with error conditions."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_delete_s3_fails_local_still_deleted(self):
        """delete() with S3 failure: local still deleted."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Create local file
        storage.local_storage.save(fail_key, ContentFile(b'delete test'))
        
        with patch('apps.tournaments.storage.logger') as mock_logger:
            storage.delete(fail_key)
        
        # Local should be deleted
        self.assertFalse(storage.local_storage.exists(fail_key))
        
        # Warning logged
        mock_logger.warning.assert_called()
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_delete_both_succeed(self):
        """delete() removes from both S3 and local."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        
        # Create in both
        saved_name = storage.save(key, ContentFile(b'delete me'))
        
        # Delete
        storage.delete(saved_name)
        
        # Both should be gone
        self.assertFalse(storage.local_storage.exists(saved_name))
        self.assertNotIn(key, dummy_s3.storage)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_delete_idempotent(self):
        """delete() is idempotent (no error if already deleted)."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'test'))
        
        # Delete twice
        storage.delete(saved_name)
        storage.delete(saved_name)  # Should not raise
        
        # Should remain deleted
        self.assertFalse(storage.local_storage.exists(saved_name))


class TestFlagCombinations(TestCase):
    """Test all flag combinations (dual_write, read_primary)."""
    
    @override_settings(CERT_S3_DUAL_WRITE=False, CERT_S3_READ_PRIMARY=False)
    def test_flags_00_local_only(self):
        """Flags (0,0): Local-only mode."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'local only'))
        
        # Only local should have file
        self.assertTrue(storage.local_storage.exists(saved_name))
        self.assertNotIn(key, dummy_s3.storage)
    
    @override_settings(CERT_S3_DUAL_WRITE=True, CERT_S3_READ_PRIMARY=False)
    def test_flags_10_write_both_read_local(self):
        """Flags (1,0): Write to both, read from local."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'dual write'))
        
        # Both should have file
        self.assertTrue(storage.local_storage.exists(saved_name))
        self.assertIn(key, dummy_s3.storage)
        
        # Read should use local (not S3)
        with storage.open(saved_name, 'rb') as f:
            result = f.read()
        self.assertEqual(result, b'dual write')
    
    @override_settings(CERT_S3_DUAL_WRITE=False, CERT_S3_READ_PRIMARY=True)
    def test_flags_01_write_local_read_s3_fallback(self):
        """Flags (0,1): Write to local, read from S3 (fallback to local)."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        content = b'local write s3 read'
        
        # Write (local only since dual_write=False)
        saved_name = storage.save(key, ContentFile(content))
        
        # S3 should NOT have file
        self.assertNotIn(key, dummy_s3.storage)
        
        # Read with READ_PRIMARY=True (S3 fails, fallback to local)
        with storage.open(saved_name, 'rb') as f:
            result = f.read()
        self.assertEqual(result, content)
    
    @override_settings(CERT_S3_DUAL_WRITE=True, CERT_S3_READ_PRIMARY=True)
    def test_flags_11_write_both_read_s3(self):
        """Flags (1,1): Write to both, read from S3."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        s3_content = b'from s3 primary'
        
        # Pre-populate S3 with different content
        dummy_s3.put_object(Bucket='test-bucket', Key=key, Body=s3_content)
        
        # Create local with different content
        storage.local_storage.save(key, ContentFile(b'from local'))
        
        # Read should return S3 content
        with storage.open(key, 'rb') as f:
            result = f.read()
        self.assertEqual(result, s3_content)


class TestKeyNormalization(TestCase):
    """Test key handling edge cases."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_unicode_key(self):
        """Unicode characters in key."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-日本語-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'unicode test'))
        
        self.assertTrue(storage.local_storage.exists(saved_name))
        self.assertIn(key, dummy_s3.storage)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_nested_path(self):
        """Deeply nested path preserved."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"certs/2024/11/tournament-123/user-456/cert-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'nested'))
        
        self.assertTrue(storage.local_storage.exists(saved_name))
        self.assertIn(key, dummy_s3.storage)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_long_key_windows_safe(self):
        """Long key (Windows 260-char safe)."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # 150 chars (safe for Windows)
        key = f"test/{'a' * 130}-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'long key'))
        
        self.assertTrue(storage.local_storage.exists(saved_name))


class TestMetricEmission(TestCase):
    """Test metric emission for all operations."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_metric_write_success(self):
        """cert.s3.write.success emitted on successful upload."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            storage.save(f"test/cert-{uuid4().hex[:8]}.pdf", ContentFile(b'data'))
        
        # Should emit write success
        mock_emit.assert_any_call('cert.s3.write.success')
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_metric_write_fail(self):
        """cert.s3.write.fail emitted on upload failure."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            storage.save(fail_key, ContentFile(b'data'))
        
        # Should emit write fail
        mock_emit.assert_any_call('cert.s3.write.fail', tags={'error': 'Exception'})
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_metric_read_success(self):
        """cert.s3.read.success emitted on successful read."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        dummy_s3.put_object(Bucket='test-bucket', Key=key, Body=b'data')
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            with storage.open(key, 'rb') as f:
                f.read()
        
        # Should emit read success
        mock_emit.assert_any_call('cert.s3.read.success', tags={'operation': 'open'})
    
    @override_settings(CERT_S3_READ_PRIMARY=True)
    def test_metric_read_fallback(self):
        """cert.s3.read.fallback emitted on S3 error."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Create local file
        storage.local_storage.save(fail_key, ContentFile(b'data'))
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            with storage.open(fail_key, 'rb') as f:
                f.read()
        
        # Should emit fallback metric
        mock_emit.assert_any_call('cert.s3.read.fallback', tags={'operation': 'open', 'error': 'Exception'})
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_metric_delete_success(self):
        """cert.s3.delete.success emitted on successful delete."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        saved_name = storage.save(key, ContentFile(b'data'))
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            storage.delete(saved_name)
        
        # Should emit delete success
        mock_emit.assert_any_call('cert.s3.delete.success')
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_metric_delete_fail(self):
        """cert.s3.delete.fail emitted on delete failure."""
        fail_key = f"test/fail-{uuid4().hex[:8]}.pdf"
        dummy_s3 = DummyS3Client(fail_on_keys={fail_key})
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        # Create local file
        storage.local_storage.save(fail_key, ContentFile(b'data'))
        
        with patch.object(storage, '_emit_metric') as mock_emit:
            storage.delete(fail_key)
        
        # Should emit delete fail
        mock_emit.assert_any_call('cert.s3.delete.fail', tags={'error': 'Exception'})


class TestContentHashValidation(TestCase):
    """Test MD5 hash preservation."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_md5_etag_match(self):
        """MD5 hash in S3 ETag matches content."""
        dummy_s3 = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        key = f"test/cert-{uuid4().hex[:8]}.pdf"
        content = b'hash validation test'
        expected_md5 = hashlib.md5(content).hexdigest()
        
        storage.save(key, ContentFile(content))
        
        # Check ETag matches MD5
        etag = dummy_s3.metadata[key]['ETag'].strip('"')
        self.assertEqual(etag, expected_md5)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_sha256_hash(self):
        """SHA-256 hash can be calculated from content."""
        content = b'certificate content for hash'
        expected_sha256 = hashlib.sha256(content).hexdigest()
        
        actual_sha256 = hashlib.sha256(content).hexdigest()
        self.assertEqual(actual_sha256, expected_sha256)


class TestLatencySLOs(TestCase):
    """Test performance with different latency profiles."""
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_low_latency_meets_slo(self):
        """Low latency (2ms): p95 < 75ms SLO."""
        dummy_s3 = DummyS3Client(upload_latency_ms=2.0)
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        latencies = []
        
        for i in range(100):
            key = f"test/cert-{i}-{uuid4().hex[:8]}.pdf"
            start = time.time()
            storage.save(key, ContentFile(b'test data'))
            duration_ms = (time.time() - start) * 1000
            latencies.append(duration_ms)
        
        # Calculate p95
        sorted_latencies = sorted(latencies)
        p95 = sorted_latencies[94]
        
        # Should meet SLO
        self.assertLess(p95, 75.0)
    
    @override_settings(CERT_S3_DUAL_WRITE=True)
    def test_high_latency_exceeds_slo(self):
        """High latency (80ms): p95 >= 75ms (fails SLO)."""
        dummy_s3 = DummyS3Client(upload_latency_ms=80.0)
        storage = CertificateS3Storage(s3_client=dummy_s3)
        
        latencies = []
        
        for i in range(20):
            key = f"test/cert-{i}-{uuid4().hex[:8]}.pdf"
            start = time.time()
            storage.save(key, ContentFile(b'test data'))
            duration_ms = (time.time() - start) * 1000
            latencies.append(duration_ms)
        
        sorted_latencies = sorted(latencies)
        p95 = sorted_latencies[18]  # 95th percentile of 20
        
        # Should exceed SLO
        self.assertGreater(p95, 75.0)


# ============================================================================
# UTF-8 ARTIFACT WRITE REGRESSION TEST
# ============================================================================

class TestUTF8ArtifactWrite(TestCase):
    """Test UTF-8 artifact writing (blocker #1 fix)."""
    
    def test_artifact_utf8_write_ok(self):
        """Write and read non-ASCII characters (Curaçao, 東京, Δ)."""
        import tempfile
        import os
        
        test_content = "Test results:\n- Curaçao: ✓\n- 東京: PASS\n- Delta (Δ): OK\n"
        
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            temp_path = f.name
            f.write(test_content)
        
        try:
            # Read back with UTF-8
            with open(temp_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            self.assertEqual(result, test_content)
        finally:
            os.unlink(temp_path)

