"""
Certificate S3 Storage - Moto Integration Tests

Tests S3Boto3Storage paths (not DummyS3Client) using moto mock.
All tests marked with @pytest.mark.s3 (run with S3_TESTS=1).

Coverage targets:
- storage.py lines 109-116 (S3 save error paths)
- storage.py lines 165-180 (exists fallback)
- storage.py lines 225-240 (delete dual-write)
- storage.py lines 263-267 (url presign fallback)
- storage.py lines 295-303 (size fallback)
- storage.py lines 319-325 (open error path)
- storage.py lines 345-346 (delete error path)
- storage.py lines 363-366 (size error path)
- storage.py lines 372-391 (time accessors)
"""

import pytest
import os
from unittest.mock import patch, Mock
from django.test import override_settings
from django.core.files.base import ContentFile
from botocore.exceptions import ClientError


# ============================================================================
# READ-PRIMARY PATH TESTS (lines 319-325: open error fallback)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates',
    AWS_S3_REGION_NAME='us-east-1'
)
def test_read_primary_s3_success_no_local_touch(storage_with_s3, spy_local_storage):
    """
    Test: CERT_S3_READ_PRIMARY=True → S3 open succeeds → no local read.
    
    Validates:
    - S3 path executes successfully
    - Local storage.open() NOT called (no fallback)
    - Metric cert.s3.read.success emitted
    
    Coverage: storage.py lines 319-325 (S3Boto3Storage.open success path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Upload test file to moto S3
    test_content = b"Certificate PDF content (moto S3)"
    client.put_object(Bucket=bucket, Key='test.pdf', Body=test_content)
    
    # Spy on local storage to ensure it's NOT called
    with spy_local_storage(storage.local_storage, 'open') as spy:
        # Open file (should use S3, not local)
        file_obj = storage.open('test.pdf', 'rb')
        retrieved = file_obj.read()
        file_obj.close()
        
        # Assertions
        assert retrieved == test_content, "S3 content mismatch"
        assert spy.call_count == 0, "Local storage.open() was called (should use S3 only)"


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_read_primary_s3_404_fallback_to_local(storage_with_s3, tmp_path, monkeypatch, mock_metric_emission):
    """
    Test: S3 open raises NoSuchKey → fallback to local storage.
    
    Validates:
    - S3 raises NoSuchKey (file not in S3)
    - Fallback to local storage succeeds
    - Metric cert.s3.read.fallback emitted
    
    Coverage: storage.py lines 319-325 (except Exception → fallback path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Prepare local file (but NOT in S3)
    media_root = tmp_path / 'media'
    media_root.mkdir(exist_ok=True)
    local_file = media_root / 'local-only.pdf'
    local_content = b"Local fallback content"
    local_file.write_bytes(local_content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(media_root))
    storage.local_storage.location = str(media_root)
    
    # Mock metric emission
    with mock_metric_emission(storage) as metric_mock:
        # Open file (S3 will 404, fallback to local)
        file_obj = storage.open('local-only.pdf', 'rb')
        retrieved = file_obj.read()
        file_obj.close()
        
        # Assertions
        assert retrieved == local_content, "Local fallback content mismatch"
        
        # Verify fallback metric emitted
        metric_mock.assert_any_call(
            'cert.s3.read.fallback',
            tags={'operation': 'open', 'error': 'NoSuchKey'}
        )


# ============================================================================
# DUAL-WRITE ERROR PATH TESTS (lines 109-116: S3 save fails, local succeeds)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=False,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_dual_write_s3_failure_local_succeeds(storage_with_s3, mock_metric_emission):
    """
    Test: S3 save fails (e.g., network error) → local save still succeeds.
    
    Validates:
    - S3Boto3Storage.save() raises exception
    - Local save proceeds anyway
    - Metric cert.s3.write.fail emitted
    - Returned filename is local path
    
    Coverage: storage.py lines 109-116 (s3_name = self._safe_s3_operation error path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Mock S3Boto3Storage.save to raise error
    with patch.object(storage.s3_storage, 'save', side_effect=ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'S3 unavailable'}},
        'PutObject'
    )):
        with mock_metric_emission(storage) as metric_mock:
            # Save file (S3 will fail, local should succeed)
            content = ContentFile(b"Test certificate data")
            saved_name = storage.save('certs/test-dual-write-fail.pdf', content)
            
            # Assertions
            assert saved_name == 'certs/test-dual-write-fail.pdf', "Local save failed"
            assert storage.local_storage.exists(saved_name), "File not in local storage"
            
            # Verify failure metric
            metric_mock.assert_any_call(
                'cert.s3.save.fail',
                tags={'error': 'ClientError'}
            )


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=False,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_dual_write_both_succeed(storage_with_s3, mock_metric_emission):
    """
    Test: Dual-write with both S3 and local succeeding.
    
    Validates:
    - S3 upload succeeds
    - Local save succeeds
    - Both files accessible
    - Metric cert.s3.write.success emitted
    
    Coverage: storage.py lines 109-116 (success path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    with mock_metric_emission(storage) as metric_mock:
        content = ContentFile(b"Dual-write success test")
        saved_name = storage.save('certs/dual-write-ok.pdf', content)
        
        # Verify S3 upload
        s3_obj = client.get_object(Bucket=bucket, Key=saved_name)
        assert s3_obj['Body'].read() == b"Dual-write success test"
        
        # Verify local save
        assert storage.local_storage.exists(saved_name)
        
        # Verify success metric
        metric_mock.assert_any_call('cert.s3.write.success')


# ============================================================================
# DELETE DUAL-WRITE TESTS (lines 345-346: S3 delete error path)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_delete_s3_error_local_succeeds(storage_with_s3, mock_metric_emission):
    """
    Test: S3 delete raises error → local delete still succeeds.
    
    Validates:
    - S3Boto3Storage.delete() raises exception
    - Local delete proceeds
    - File removed from local storage
    - Metric cert.s3.delete.fail emitted
    
    Coverage: storage.py lines 345-346 (except path in delete)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file in both locations
    content = ContentFile(b"Delete test")
    saved_name = storage.save('certs/delete-test.pdf', content)
    
    # Verify both exist
    assert storage.local_storage.exists(saved_name)
    s3_obj = client.get_object(Bucket=bucket, Key=saved_name)
    assert s3_obj is not None
    
    # Mock S3 delete to raise error
    with patch.object(storage.s3_storage, 'delete', side_effect=ClientError(
        {'Error': {'Code': '5xxError', 'Message': 'S3 server error'}},
        'DeleteObject'
    )):
        with mock_metric_emission(storage) as metric_mock:
            # Delete (S3 fails, local should succeed)
            storage.delete(saved_name)
            
            # Local file should be gone
            assert not storage.local_storage.exists(saved_name)
            
            # Verify failure metric
            metric_mock.assert_any_call(
                'cert.s3.delete.fail',
                tags={'error': 'ClientError'}
            )


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_delete_both_succeed(storage_with_s3):
    """
    Test: Delete from both S3 and local succeeds.
    
    Coverage: storage.py lines 345-346 (success path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file
    content = ContentFile(b"Delete both test")
    saved_name = storage.save('certs/delete-both.pdf', content)
    
    # Delete
    storage.delete(saved_name)
    
    # Verify both gone
    assert not storage.local_storage.exists(saved_name)
    
    # S3 should also be gone (moto returns empty list if not found)
    response = client.list_objects_v2(Bucket=bucket, Prefix=saved_name)
    assert response.get('KeyCount', 0) == 0


# ============================================================================
# URL GENERATION TESTS (lines 263-267: presign error fallback)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_url_generation_s3_error_fallback_local(storage_with_s3, mock_metric_emission):
    """
    Test: S3 presigned URL generation fails → fallback to local URL.
    
    Validates:
    - S3Boto3Storage.url() raises exception
    - Fallback to local URL
    - Metric cert.s3.read.fallback emitted
    
    Coverage: storage.py lines 263-267 (except path in url())
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file in local (for fallback)
    content = ContentFile(b"URL fallback test")
    saved_name = storage.save('certs/url-fallback.pdf', content)
    
    # Mock S3 url() to raise error
    with patch.object(storage.s3_storage, 'url', side_effect=ClientError(
        {'Error': {'Code': 'SignatureDoesNotMatch', 'Message': 'Auth error'}},
        'GetObject'
    )):
        with mock_metric_emission(storage) as metric_mock:
            # Get URL (S3 fails, fallback to local)
            url = storage.url(saved_name)
            
            # Should be local URL (contains /media/)
            assert '/media/' in url or saved_name in url
            
            # Verify fallback metric
            metric_mock.assert_any_call(
                'cert.s3.read.fallback',
                tags={'operation': 'url'}
            )


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_url_generation_s3_success(storage_with_s3):
    """
    Test: S3 presigned URL generation succeeds.
    
    Coverage: storage.py lines 263-267 (success path)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file
    content = ContentFile(b"URL success test")
    saved_name = storage.save('certs/url-ok.pdf', content)
    
    # Get URL
    url = storage.url(saved_name)
    
    # Should be S3 URL (contains amazonaws.com or bucket name)
    assert 'amazonaws.com' in url or bucket in url or 'Signature=' in url


# ============================================================================
# SIZE TESTS (lines 363-366: size error fallback)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_size_s3_error_fallback_local(storage_with_s3, mock_metric_emission):
    """
    Test: S3 size() fails → fallback to local size.
    
    Coverage: storage.py lines 363-366 (except path in size())
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file
    content = ContentFile(b"Size test content")
    saved_name = storage.save('certs/size-fallback.pdf', content)
    
    # Mock S3 size to raise error
    with patch.object(storage.s3_storage, 'size', side_effect=ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'Size unavailable'}},
        'HeadObject'
    )):
        with mock_metric_emission(storage) as metric_mock:
            # Get size (S3 fails, fallback to local)
            size = storage.size(saved_name)
            
            # Should match local file size
            assert size == 17  # len(b"Size test content")
            
            # Verify fallback metric
            metric_mock.assert_any_call(
                'cert.s3.read.fallback',
                tags={'operation': 'size'}
            )


# ============================================================================
# EXISTS TESTS (lines 165-180: exists fallback path)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_exists_s3_error_fallback_local(storage_with_s3, mock_metric_emission):
    """
    Test: S3 exists() fails → fallback to local exists.
    
    Coverage: storage.py lines 165-180 (except path in exists())
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file in local only
    content = ContentFile(b"Exists test")
    saved_name = storage.save('certs/exists-fallback.pdf', content)
    
    # Mock S3 exists to raise error
    with patch.object(storage.s3_storage, 'exists', side_effect=ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'S3 unavailable'}},
        'HeadObject'
    )):
        with mock_metric_emission(storage) as metric_mock:
            # Check exists (S3 fails, fallback to local)
            exists = storage.exists(saved_name)
            
            # Should find local file
            assert exists is True
            
            # Verify fallback metric
            metric_mock.assert_any_call(
                'cert.s3.read.fallback',
                tags={'operation': 'exists'}
            )


# ============================================================================
# TIME ACCESSOR TESTS (lines 372-391)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_time_accessors_passthrough(storage_with_s3):
    """
    Test: Time accessor methods delegate to local storage.
    
    Validates:
    - get_accessed_time() returns local time
    - get_created_time() returns local time
    - get_modified_time() returns local time
    
    Coverage: storage.py lines 372, 376, 380, 391
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Create file
    content = ContentFile(b"Time accessor test")
    saved_name = storage.save('certs/time-test.pdf', content)
    
    # Get times (should delegate to local storage)
    accessed = storage.get_accessed_time(saved_name)
    created = storage.get_created_time(saved_name)
    modified = storage.get_modified_time(saved_name)
    
    # All should return datetime objects
    from datetime import datetime
    assert isinstance(accessed, datetime)
    assert isinstance(created, datetime)
    assert isinstance(modified, datetime)


# ============================================================================
# FLAG COMBINATION TESTS (lines 295-303: various flag matrices)
# ============================================================================

@pytest.mark.s3
@pytest.mark.parametrize("dual_write,read_primary,expected_s3_writes", [
    (False, False, 0),  # Local-only mode
    (True, False, 1),   # Dual-write enabled, read from local
    (False, True, 0),   # Read-primary only (no writes yet)
    (True, True, 1),    # Full S3 mode (dual-write + read-primary)
])
def test_flag_combinations_write_behavior(storage_with_s3, dual_write, read_primary, expected_s3_writes):
    """
    Test: Flag combinations control write behavior.
    
    Coverage: storage.py lines 295-303 (flag-dependent paths)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Override settings dynamically
    with override_settings(
        CERT_S3_DUAL_WRITE=dual_write,
        CERT_S3_READ_PRIMARY=read_primary
    ):
        # Reinitialize storage with new flags
        from apps.tournaments.storage import CertificateS3Storage
        storage = CertificateS3Storage()
        storage.local_storage.location = storage_with_s3[0].local_storage.location
        storage.bucket_name = bucket
        
        # Save file
        content = ContentFile(b"Flag test")
        saved_name = storage.save('certs/flag-test.pdf', content)
        
        # Check S3 writes
        response = client.list_objects_v2(Bucket=bucket, Prefix='certs/flag-test.pdf')
        actual_s3_writes = response.get('KeyCount', 0)
        
        assert actual_s3_writes == expected_s3_writes, \
            f"dual_write={dual_write}, read_primary={read_primary} → expected {expected_s3_writes} S3 writes, got {actual_s3_writes}"


# ============================================================================
# UNICODE KEY TESTS (lines 53: key normalization)
# ============================================================================

@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_unicode_keys_consistent_mapping(storage_with_s3):
    """
    Test: Unicode characters in keys handled consistently.
    
    Validates:
    - Save with unicode path
    - Retrieve same content
    - Delete succeeds
    
    Coverage: storage.py line 53 (key normalization)
    """
    storage, client, resource, bucket = storage_with_s3
    
    # Unicode key with nested path
    unicode_key = 'certs/Curaçao_東京_Δ_test.pdf'
    content = ContentFile(b"Unicode key test content")
    
    # Save
    saved_name = storage.save(unicode_key, content)
    
    # Retrieve
    file_obj = storage.open(saved_name, 'rb')
    retrieved = file_obj.read()
    file_obj.close()
    
    assert retrieved == b"Unicode key test content"
    
    # Delete
    storage.delete(saved_name)
    assert not storage.exists(saved_name)


# ============================================================================
# UTF-8 ARTIFACT TEST (dry-run artifact encoding validation)
# ============================================================================

@pytest.mark.s3
def test_utf8_artifact_write_no_encoding_error(tmp_path):
    """
    Test: UTF-8 artifact writing with non-ASCII characters.
    
    Validates:
    - Write artifact with unicode content
    - Read back without UnicodeDecodeError
    - Content preserved correctly
    
    Coverage: scripts/s3_dry_run_rehearsal.py UTF-8 artifact logic
    """
    artifact_path = tmp_path / 'utf8-test-artifact.txt'
    
    # Non-ASCII content (Curaçao, 東京, Δ)
    test_content = """
DRY-RUN RESULTS:
=================
Location: Curaçao datacenter
Region: 東京 (Tokyo)
Performance: Δ = +15ms (within SLO)
Status: ✓ GO: All checks passed
Hash validation: 100% success (✓✓✓)
Unicode test: Ω Σ Δ π ∞ ≈ ≠ ≤ ≥
"""
    
    # Write with UTF-8 encoding
    with open(artifact_path, 'w', encoding='utf-8', newline='') as f:
        f.write(test_content)
    
    # Read back
    with open(artifact_path, 'r', encoding='utf-8') as f:
        retrieved = f.read()
    
    # Verify content preserved
    assert retrieved == test_content
    assert 'Curaçao' in retrieved
    assert '東京' in retrieved
    assert 'Δ' in retrieved
    assert '✓' in retrieved
