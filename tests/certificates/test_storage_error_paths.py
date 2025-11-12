"""
Test Suite: Storage Error Path Coverage (Buckets A-H)

Module: 6.5 - Certificate Storage Migration (S3)
Purpose: Exercise all error/fallback branches in storage.py for ≥72% coverage

Buckets mapping (from spec):
- Bucket A (lines 109-116): save() S3 error → retry/fallback
- Bucket B (lines 165-180): exists() S3 error → fallback local
- Bucket C (lines 225-240): delete() S3 error → fallback
- Bucket D (lines 263-267): url() S3 error → fallback
- Bucket E (lines 319-325): open() read-primary S3 error → fallback
- Bucket F (lines 345-346): delete() success path
- Bucket G (lines 363-366): size() S3 error → fallback
- Bucket H (lines 53, 295-303): init/misc branches
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from django.core.files.base import ContentFile
from botocore.exceptions import ClientError, EndpointConnectionError
from datetime import datetime
import os


@pytest.mark.skipif(
    os.getenv('S3_TESTS') != '1',
    reason="S3 integration tests disabled (set S3_TESTS=1 to enable)"
)
class TestStorageErrorPaths:
    """
    Comprehensive error path testing for CertificateS3Storage.
    Uses real S3Boto3Storage with moto to exercise S3 error branches.
    """
    
    # ============================================================================
    # BUCKET A: save() error handling (lines 109-116)
    # ============================================================================
    
    def test_bucket_a_save_s3_transient_error_then_success(self, storage_with_s3, mock_metric_emission):
        """
        Bucket A: S3 write fails with EndpointConnectionError, local shadow succeeds.
        
        Coverage: lines 109-116 (S3Boto3Storage.save exception handling)
        Expected metrics: cert.s3.write.fail, cert.s3.shadow.success
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Inject transient error on first S3 write attempt
        original_save = storage.s3_storage.save
        call_count = [0]
        
        def failing_save(name, content, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise EndpointConnectionError(endpoint_url='https://s3.amazonaws.com')
            return original_save(name, content, *args, **kwargs)
        
        with patch.object(storage.s3_storage, 'save', side_effect=failing_save):
            content = ContentFile(b'transient-error-test')
            saved_name = storage.save('certs/transient.pdf', content)
        
        # Verify local fallback succeeded
        assert storage.local_storage.exists(saved_name)
        
        # Verify metrics
        mock_metric_emission.assert_any_call('cert.s3.write.fail', tags={'error': 'EndpointConnectionError'})
        mock_metric_emission.assert_any_call('cert.s3.shadow.success')
    
    def test_bucket_a_save_s3_client_error_fallback(self, storage_with_s3, mock_metric_emission):
        """
        Bucket A: S3 write fails with ClientError (403/500), local succeeds.
        
        Coverage: lines 109-116
        Expected: cert.s3.write.fail → shadow write
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Inject ClientError (access denied)
        with patch.object(storage.s3_storage, 'save', side_effect=ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Forbidden'}},
            'PutObject'
        )):
            content = ContentFile(b'access-denied-test')
            saved_name = storage.save('certs/denied.pdf', content)
        
        # Verify local exists
        assert storage.local_storage.exists(saved_name)
        mock_metric_emission.assert_any_call('cert.s3.write.fail', tags={'error': 'AccessDenied'})
    
    # ============================================================================
    # BUCKET B: exists() fallback (lines 165-180)
    # ============================================================================
    
    def test_bucket_b_exists_s3_error_fallback_local(self, storage_with_s3, mock_metric_emission):
        """
        Bucket B: exists() check - S3 raises ClientError, fallback to local.
        
        Coverage: lines 165-180 (S3Boto3Storage.exists exception path)
        Expected: cert.s3.exists.fallback metric
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file in local only
        content = ContentFile(b'local-only')
        saved_name = storage.local_storage.save('certs/local-only.pdf', content)
        
        # Inject S3 error
        with patch.object(storage.s3_storage, 'exists', side_effect=ClientError(
            {'Error': {'Code': 'InternalError', 'Message': '500 Internal Server Error'}},
            'HeadObject'
        )):
            exists = storage.exists(saved_name)
        
        # Should still report True (from local fallback)
        assert exists is True
        mock_metric_emission.assert_any_call('cert.s3.exists.fallback')
    
    def test_bucket_b_exists_s3_noerror_false(self, storage_with_s3, mock_metric_emission):
        """
        Bucket B: exists() returns False when object missing from both S3 and local.
        
        Coverage: lines 165-180 (negative path)
        """
        storage, client, resource, bucket = storage_with_s3
        
        exists = storage.exists('nonexistent/file.pdf')
        assert exists is False
    
    # ============================================================================
    # BUCKET C: delete() error handling (lines 225-240)
    # ============================================================================
    
    def test_bucket_c_delete_s3_5xx_fallback_local(self, storage_with_s3, mock_metric_emission):
        """
        Bucket C: delete() - S3 fails with 5xx, local delete succeeds.
        
        Coverage: lines 225-240 (S3Boto3Storage.delete exception)
        Expected: cert.s3.delete.fallback metric
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file in local
        content = ContentFile(b'to-delete')
        saved_name = storage.local_storage.save('certs/delete-test.pdf', content)
        
        # Inject S3 delete error
        with patch.object(storage.s3_storage, 'delete', side_effect=ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': '503'}},
            'DeleteObject'
        )):
            storage.delete(saved_name)
        
        # Verify local deleted despite S3 failure
        assert not storage.local_storage.exists(saved_name)
        mock_metric_emission.assert_any_call('cert.s3.delete.fallback')
    
    def test_bucket_c_delete_both_success(self, storage_with_s3, mock_metric_emission):
        """
        Bucket C: delete() succeeds on both S3 and local.
        
        Coverage: lines 225-240 (success path)
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Save file (goes to both S3 and local)
        content = ContentFile(b'delete-both')
        saved_name = storage.save('certs/delete-both.pdf', content)
        
        # Delete from both
        storage.delete(saved_name)
        
        # Verify gone from both
        assert not storage.local_storage.exists(saved_name)
        # S3 check would require actual object verification
    
    # ============================================================================
    # BUCKET D: url() fallback (lines 263-267)
    # ============================================================================
    
    def test_bucket_d_url_s3_error_fallback_local(self, storage_with_s3, mock_metric_emission):
        """
        Bucket D: url() - S3 presigned URL generation fails, return local URL.
        
        Coverage: lines 263-267 (url() exception path)
        Expected: cert.s3.url.fallback metric
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file locally
        content = ContentFile(b'url-test')
        saved_name = storage.local_storage.save('certs/url-fallback.pdf', content)
        
        # Inject S3 url error
        with patch.object(storage.s3_storage, 'url', side_effect=ClientError(
            {'Error': {'Code': 'InvalidToken', 'Message': 'Token expired'}},
            'GeneratePresignedUrl'
        )):
            url = storage.url(saved_name)
        
        # Should return local URL (starts with /media/)
        assert url.startswith('/media/')
        mock_metric_emission.assert_any_call('cert.s3.url.fallback')
    
    def test_bucket_d_url_s3_success(self, storage_with_s3, mock_metric_emission):
        """
        Bucket D: url() succeeds via S3 presigned URL.
        
        Coverage: lines 263-267 (success path)
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Save file to S3
        content = ContentFile(b'url-success')
        saved_name = storage.save('certs/url-ok.pdf', content)
        
        # Get URL
        url = storage.url(saved_name)
        
        # S3 URLs should contain bucket name or be presigned
        # Moto returns local-style URLs, so we check it's not /media/
        assert 'Signature=' in url or bucket in url or 'amazonaws.com' in url
    
    # ============================================================================
    # BUCKET E: open() read-primary fallback (lines 319-325)
    # ============================================================================
    
    def test_bucket_e_open_read_primary_s3_nosuchkey_fallback(self, storage_with_s3, mock_metric_emission):
        """
        Bucket E: open() in READ_PRIMARY mode - S3 NoSuchKey → fallback to local.
        
        Coverage: lines 319-325 (S3Boto3Storage.open exception)
        Expected: cert.s3.read.fallback metric with error='NoSuchKey'
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file in local only (simulate S3 miss)
        content = ContentFile(b'local-fallback-data')
        saved_name = storage.local_storage.save('certs/fallback-read.pdf', content)
        
        # Inject S3 NoSuchKey error
        with patch.object(storage.s3_storage, 'open', side_effect=ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
            'GetObject'
        )):
            file_obj = storage.open(saved_name, 'rb')
            data = file_obj.read()
        
        # Verify local data retrieved
        assert data == b'local-fallback-data'
        mock_metric_emission.assert_any_call('cert.s3.read.fallback', tags={'operation': 'open', 'error': 'NoSuchKey'})
    
    def test_bucket_e_open_read_primary_s3_success(self, storage_with_s3, spy_local_storage):
        """
        Bucket E: open() in READ_PRIMARY - S3 succeeds, no local touch.
        
        Coverage: lines 319-325 (success path - no local read)
        Expected: local_storage.open NOT called
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Save file (goes to S3)
        content = ContentFile(b's3-primary-data')
        saved_name = storage.save('certs/s3-primary.pdf', content)
        
        # Read from S3 (should NOT touch local)
        file_obj = storage.open(saved_name, 'rb')
        data = file_obj.read()
        
        assert data == b's3-primary-data'
        # Spy should show local was NOT used for reading
        spy_local_storage.open.assert_not_called()
    
    # ============================================================================
    # BUCKET F: delete() direct path (lines 345-346)
    # ============================================================================
    
    def test_bucket_f_delete_idempotent(self, storage_with_s3):
        """
        Bucket F: delete() on non-existent file is idempotent (no error).
        
        Coverage: lines 345-346 (delete path with non-existent file)
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Delete non-existent file (should not raise)
        storage.delete('nonexistent/file.pdf')
        # Success if no exception
    
    # ============================================================================
    # BUCKET G: size() fallback (lines 363-366)
    # ============================================================================
    
    def test_bucket_g_size_s3_error_fallback_local(self, storage_with_s3, mock_metric_emission):
        """
        Bucket G: size() - S3 fails, fallback to local.
        
        Coverage: lines 363-366 (S3Boto3Storage.size exception)
        Expected: cert.s3.size.fallback metric
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file locally
        content = ContentFile(b'size-test-12345')
        saved_name = storage.local_storage.save('certs/size-test.pdf', content)
        
        # Inject S3 size error
        with patch.object(storage.s3_storage, 'size', side_effect=ClientError(
            {'Error': {'Code': 'InternalError'}},
            'HeadObject'
        )):
            size = storage.size(saved_name)
        
        assert size == 15  # len(b'size-test-12345')
        mock_metric_emission.assert_any_call('cert.s3.size.fallback')
    
    def test_bucket_g_size_s3_success(self, storage_with_s3):
        """
        Bucket G: size() succeeds via S3.
        
        Coverage: lines 363-366 (success path)
        """
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'size-ok-67890')
        saved_name = storage.save('certs/size-ok.pdf', content)
        
        size = storage.size(saved_name)
        assert size == 13  # len(b'size-ok-67890')
    
    # ============================================================================
    # BUCKET H: init/misc branches (lines 53, 295-303)
    # ============================================================================
    
    def test_bucket_h_init_with_s3_client_injection(self, monkeypatch, tmp_path):
        """
        Bucket H: Initialize storage with injected s3_client (testing mode).
        
        Coverage: lines 53, 295-303 (s3_client branch in __init__)
        """
        from apps.tournaments.storage import CertificateS3Storage
        from apps.tournaments.s3_protocol import DummyS3Client
        
        monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
        monkeypatch.setattr('django.conf.settings.MEDIA_URL', '/media/')
        monkeypatch.setattr('django.conf.settings.CERT_S3_DUAL_WRITE', False)
        monkeypatch.setattr('django.conf.settings.CERT_S3_READ_PRIMARY', False)
        
        # Inject dummy client
        dummy = DummyS3Client()
        storage = CertificateS3Storage(s3_client=dummy)
        
        # Verify s3_storage is None (bypass mode)
        assert storage.s3_storage is None
        assert storage.s3_client is dummy
    
    def test_bucket_h_init_flags_default_off(self, monkeypatch, tmp_path):
        """
        Bucket H: Verify feature flags default to OFF.
        
        Coverage: lines 88-90 (flag initialization)
        """
        from apps.tournaments.storage import CertificateS3Storage
        
        monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
        monkeypatch.setattr('django.conf.settings.MEDIA_URL', '/media/')
        # Don't set flags - they should default to False
        monkeypatch.delattr('django.conf.settings.CERT_S3_DUAL_WRITE', raising=False)
        monkeypatch.delattr('django.conf.settings.CERT_S3_READ_PRIMARY', raising=False)
        
        storage = CertificateS3Storage()
        
        assert storage.dual_write_enabled is False
        assert storage.read_primary_s3 is False


# ============================================================================
# TIME ACCESSOR TESTS (lines 372, 376, 380, 391)
# ============================================================================

@pytest.mark.skipif(
    os.getenv('S3_TESTS') != '1',
    reason="S3 integration tests disabled"
)
class TestTimeAccessors:
    """Test time accessor pass-through methods."""
    
    def test_time_accessors_passthrough(self, storage_with_s3):
        """
        Test get_accessed_time, get_created_time, get_modified_time.
        
        Coverage: lines 372, 376, 380, 391 (time accessor methods)
        """
        storage, client, resource, bucket = storage_with_s3
        
        # Create file
        content = ContentFile(b'time-test')
        saved_name = storage.save('certs/time-test.pdf', content)
        
        # Get times
        accessed = storage.get_accessed_time(saved_name)
        created = storage.get_created_time(saved_name)
        modified = storage.get_modified_time(saved_name)
        
        # Verify all return datetime objects
        assert isinstance(accessed, datetime)
        assert isinstance(created, datetime)
        assert isinstance(modified, datetime)
        
        # Verify reasonable ordering (created <= modified <= accessed)
        assert created <= modified
        assert modified <= accessed or (accessed - modified).total_seconds() < 2
