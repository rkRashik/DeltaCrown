"""
Test Suite: Storage Error Path Coverage (Buckets A-H) - REFACTORED

Module: 6.5 - Certificate Storage Migration (S3)
Purpose: Exercise all error/fallback branches with capture_cert_metrics pattern

All tests now use unified context manager for reliable metric capture.
"""

import pytest
from unittest.mock import patch
from django.core.files.base import ContentFile
from botocore.exceptions import ClientError, EndpointConnectionError
import os
from tests.certificates.helpers import capture_cert_metrics


@pytest.mark.skipif(
    os.getenv('S3_TESTS') != '1',
    reason="S3 integration tests disabled (set S3_TESTS=1 to enable)"
)
class TestStorageErrorPathsRefactored:
    """
    Comprehensive error path testing using capture_cert_metrics pattern.
    """
    
    # BUCKET A: save() error handling
    def test_bucket_a_save_s3_transient_error(self, storage_with_s3):
        """Bucket A: S3 write fails, local shadow succeeds."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'save', side_effect=EndpointConnectionError(
                endpoint_url='https://s3.amazonaws.com'
            )):
                content = ContentFile(b'transient-error-test')
                saved_name = storage.save('certs/transient.pdf', content)
            
            assert storage.local_storage.exists(saved_name)
            # Note: S3Boto3Storage.save() wrapped by _safe_s3_operation emits 'cert.s3.save.fail'
            assert em.counts.get('cert.s3.save.fail', 0) >= 1
    
    def test_bucket_a_save_s3_client_error(self, storage_with_s3):
        """Bucket A: S3 write fails with ClientError."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'save', side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Forbidden'}},
                'PutObject'
            )):
                content = ContentFile(b'access-denied-test')
                saved_name = storage.save('certs/denied.pdf', content)
            
            assert storage.local_storage.exists(saved_name)
            assert em.counts.get('cert.s3.save.fail', 0) >= 1
    
    # BUCKET B: exists() fallback
    def test_bucket_b_exists_s3_error_fallback(self, storage_with_s3):
        """Bucket B: exists() S3 error → local fallback."""
        storage, client, resource, bucket = storage_with_s3
        
        # Create file locally only
        content = ContentFile(b'local-only')
        saved_name = storage.local_storage.save('certs/local-only.pdf', content)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'exists', side_effect=ClientError(
                {'Error': {'Code': 'InternalError', 'Message': '500'}},
                'HeadObject'
            )):
                exists = storage.exists(saved_name)
            
            assert exists is True
            assert em.counts.get('cert.s3.read.fallback', 0) >= 1
    
    def test_bucket_b_exists_both_false(self, storage_with_s3):
        """Bucket B: exists() returns False when missing."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            exists = storage.exists('nonexistent/file.pdf')
            assert exists is False
    
    # BUCKET C: delete() error handling
    def test_bucket_c_delete_s3_5xx_fallback(self, storage_with_s3):
        """Bucket C: delete() S3 fails, local succeeds."""
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'to-delete')
        saved_name = storage.local_storage.save('certs/delete-test.pdf', content)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'delete', side_effect=ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': '503'}},
                'DeleteObject'
            )):
                storage.delete(saved_name)
            
            assert not storage.local_storage.exists(saved_name)
            assert em.counts.get('cert.s3.delete.fail', 0) >= 1
    
    def test_bucket_c_delete_both_success(self, storage_with_s3):
        """Bucket C: delete() succeeds on both."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b'delete-both')
            saved_name = storage.save('certs/delete-both.pdf', content)
            storage.delete(saved_name)
            
            assert not storage.local_storage.exists(saved_name)
            assert em.counts.get('cert.s3.delete.success', 0) >= 1
    
    # BUCKET D: url() fallback
    def test_bucket_d_url_s3_error_fallback(self, storage_with_s3):
        """Bucket D: url() S3 error → local URL."""
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'url-test')
        saved_name = storage.local_storage.save('certs/url-test.pdf', content)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'url', side_effect=ClientError(
                {'Error': {'Code': 'InvalidRequest', 'Message': 'Invalid'}},
                'GeneratePresignedUrl'
            )):
                url = storage.url(saved_name)
            
            assert url.startswith('/media/')
            assert em.counts.get('cert.s3.read.fallback', 0) >= 1
    
    def test_bucket_d_url_s3_success(self, storage_with_s3):
        """Bucket D: url() S3 presigned URL success."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b'presigned-test')
            saved_name = storage.save('certs/presigned.pdf', content)
            
            # S3 client direct call
            if storage.s3_client:
                url = storage.url(saved_name)
                assert em.counts.get('cert.s3.url.success', 0) >= 1
    
    # BUCKET E: open() read-primary fallback
    def test_bucket_e_open_s3_nosuchkey_fallback(self, storage_with_s3):
        """Bucket E: open() S3 NoSuchKey → local fallback."""
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'read-fallback-test')
        saved_name = storage.local_storage.save('certs/read-fallback.pdf', content)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'open', side_effect=ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
                'GetObject'
            )):
                file_obj = storage.open(saved_name, 'rb')
                data = file_obj.read()
            
            assert data == b'read-fallback-test'
            assert em.counts.get('cert.s3.read.fallback', 0) >= 1
    
    def test_bucket_e_open_s3_success(self, storage_with_s3):
        """Bucket E: open() S3 read success."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b's3-read-success')
            saved_name = storage.save('certs/read-success.pdf', content)
            
            file_obj = storage.open(saved_name, 'rb')
            data = file_obj.read()
            
            assert data == b's3-read-success'
            # May emit cert.s3.read.success if S3 read attempted
    
    # BUCKET F: delete() success path
    def test_bucket_f_delete_idempotent(self, storage_with_s3):
        """Bucket F: delete() is idempotent."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b'idempotent-delete')
            saved_name = storage.save('certs/idempotent.pdf', content)
            
            # Delete twice
            storage.delete(saved_name)
            storage.delete(saved_name)  # Should not fail
            
            assert not storage.local_storage.exists(saved_name)
    
    # BUCKET G: size() fallback
    def test_bucket_g_size_s3_error_fallback(self, storage_with_s3):
        """Bucket G: size() S3 error → local size."""
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'size-test-data')
        saved_name = storage.local_storage.save('certs/size-test.pdf', content)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'size', side_effect=ClientError(
                {'Error': {'Code': 'InternalError', 'Message': '500'}},
                'HeadObject'
            )):
                size = storage.size(saved_name)
            
            assert size == len(b'size-test-data')
            assert em.counts.get('cert.s3.read.fallback', 0) >= 1
    
    def test_bucket_g_size_s3_success(self, storage_with_s3):
        """Bucket G: size() S3 success."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b's3-size-data')
            saved_name = storage.save('certs/size-s3.pdf', content)
            
            size = storage.size(saved_name)
            assert size == len(b's3-size-data')
    
    # BUCKET H: init/misc branches
    def test_bucket_h_storage_init_flags_off(self):
        """Bucket H: Storage init with flags OFF."""
        from apps.tournaments.storage import CertificateS3Storage
        from django.conf import settings
        
        with capture_cert_metrics() as em:
            # Force flags OFF
            with patch.object(settings, 'CERT_S3_DUAL_WRITE', False):
                with patch.object(settings, 'CERT_S3_READ_PRIMARY', False):
                    storage = CertificateS3Storage()
                    
                    assert storage.dual_write_enabled is False
                    assert storage.read_primary_s3 is False
    
    def test_bucket_h_time_accessors(self, storage_with_s3):
        """Bucket H: Time accessor pass-throughs."""
        storage, client, resource, bucket = storage_with_s3
        
        content = ContentFile(b'time-test')
        saved_name = storage.local_storage.save('certs/time-test.pdf', content)
        
        # All time methods pass through to local storage
        accessed = storage.get_accessed_time(saved_name)
        created = storage.get_created_time(saved_name)
        modified = storage.get_modified_time(saved_name)
        
        assert accessed is not None
        assert created is not None
        assert modified is not None
        # Times should be recent and in order
        assert created <= modified
    
    # CHAOS: Random 5xx injection
    def test_chaos_random_5xx_injection_2pct(self, storage_with_s3):
        """Chaos test: 2% random 5xx injection."""
        import random
        storage, client, resource, bucket = storage_with_s3
        
        original_save = storage.s3_storage.save
        
        def chaos_save(name, content, *args, **kwargs):
            if random.random() < 0.02:  # 2% failure rate
                raise ClientError(
                    {'Error': {'Code': 'ServiceUnavailable', 'Message': '503'}},
                    'PutObject'
                )
            return original_save(name, content, *args, **kwargs)
        
        with capture_cert_metrics() as em:
            with patch.object(storage.s3_storage, 'save', side_effect=chaos_save):
                # 20 operations
                for i in range(20):
                    content = ContentFile(f'chaos-{i}'.encode())
                    saved_name = storage.save(f'certs/chaos-{i}.pdf', content)
                    assert storage.local_storage.exists(saved_name)
            
            # Should have at least some successes (98%+ success rate)
            total_save = em.counts.get('cert.s3.save.success', 0) + em.counts.get('cert.s3.save.fail', 0)
            assert total_save >= 18  # At least 90% attempted
    
    # UTF-8 verification
    def test_utf8_artifact_verification(self, storage_with_s3):
        """UTF-8: Verify non-ASCII characters work."""
        storage, client, resource, bucket = storage_with_s3
        
        with capture_cert_metrics() as em:
            # Test various UTF-8 characters
            test_data = 'Curaçao / 東京 / Δ (Delta) / Emoji: 🏆'.encode('utf-8')
            content = ContentFile(test_data)
            saved_name = storage.save('certs/utf8-test.pdf', content)
            
            # Read back
            file_obj = storage.open(saved_name, 'rb')
            read_data = file_obj.read()
            
            assert read_data == test_data
            assert 'Curaçao'.encode('utf-8') in read_data
            assert '東京'.encode('utf-8') in read_data
            assert 'Δ'.encode('utf-8') in read_data
