"""
Consistency Checker Tests - Moto Integration

Tests certificate_consistency.py script with moto S3 backend.

Coverage:
- Equal counts → OK status
- Count mismatch → WARNING status
- Hash mismatch → ERROR status
- Orphan detection and cleanup
"""

import pytest
import hashlib
from pathlib import Path
from unittest.mock import patch
from django.test import override_settings


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_consistency_equal_counts_ok(moto_bucket, tmp_path, monkeypatch):
    """
    Test: Equal counts in S3 and local → status OK.
    
    Validates:
    - Create 3 files in both S3 and local
    - Consistency check returns OK
    - matched_count = 3
    """
    from scripts.certificate_consistency import check_consistency
    
    client, resource, bucket = moto_bucket
    
    # Setup: 3 files in both locations
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    for i in range(3):
        content = b'Certificate %d' % i
        key = f'certs/cert-{i:03d}.pdf'
        
        # Local
        local_file = media_root / f'cert-{i:03d}.pdf'
        local_file.write_bytes(content)
        
        # S3
        client.put_object(Bucket=bucket, Key=key, Body=content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Run consistency check
    results = check_consistency(check_hashes=False)
    
    # Assertions
    assert results['status'] == 'OK'
    assert results['local_count'] == 3
    assert results['s3_count'] == 3
    assert results['matched_count'] == 3
    assert len(results['orphaned_local']) == 0
    assert len(results['orphaned_s3']) == 0


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_consistency_count_mismatch_warning(moto_bucket, tmp_path, monkeypatch):
    """
    Test: Count mismatch → status WARNING.
    
    Validates:
    - 3 local files, 2 S3 objects
    - Status = WARNING
    - Orphaned local files detected
    """
    from scripts.certificate_consistency import check_consistency
    
    client, resource, bucket = moto_bucket
    
    # Setup: 3 local, 2 S3
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    # Local: 3 files
    for i in range(3):
        local_file = media_root / f'cert-{i:03d}.pdf'
        local_file.write_bytes(b'Local cert %d' % i)
    
    # S3: only 2 files (missing cert-002)
    for i in range(2):
        key = f'certs/cert-{i:03d}.pdf'
        client.put_object(Bucket=bucket, Key=key, Body=b'S3 cert %d' % i)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Run check
    results = check_consistency(check_hashes=False)
    
    # Assertions
    assert results['status'] == 'WARNING', "Count mismatch should trigger WARNING"
    assert results['local_count'] == 3
    assert results['s3_count'] == 2
    assert results['matched_count'] == 2
    assert len(results['orphaned_local']) == 1
    assert 'certs/cert-002.pdf' in results['orphaned_local']


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_consistency_hash_mismatch_error(moto_bucket, tmp_path, monkeypatch):
    """
    Test: Hash mismatch → status ERROR.
    
    Validates:
    - Same file in both locations
    - Different content (hash mismatch)
    - Status = ERROR
    - Hash mismatch captured
    """
    from scripts.certificate_consistency import check_consistency
    
    client, resource, bucket = moto_bucket
    
    # Setup: Same filename, different content
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    local_content = b'Local version of certificate'
    s3_content = b'S3 version of certificate (DIFFERENT)'
    
    key = 'certs/mismatch.pdf'
    
    # Local
    local_file = media_root / 'mismatch.pdf'
    local_file.write_bytes(local_content)
    
    # S3 (different content)
    client.put_object(Bucket=bucket, Key=key, Body=s3_content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Run check with hash validation
    results = check_consistency(check_hashes=True)
    
    # Assertions
    assert results['status'] == 'ERROR', "Hash mismatch should trigger ERROR"
    assert len(results['hash_mismatches']) == 1
    
    mismatch = results['hash_mismatches'][0]
    assert mismatch['key'] == key
    assert mismatch['local_md5'] == hashlib.md5(local_content).hexdigest()
    assert mismatch['s3_etag'] == hashlib.md5(s3_content).hexdigest()


@pytest.mark.s3
@override_settings(
    CERT_S3_DUAL_WRITE=True,
    CERT_S3_READ_PRIMARY=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_consistency_hash_validation_success(moto_bucket, tmp_path, monkeypatch):
    """
    Test: Hash validation passes when content matches.
    
    Validates:
    - Same content in both locations
    - --check-hashes passes
    - No hash mismatches
    """
    from scripts.certificate_consistency import check_consistency
    
    client, resource, bucket = moto_bucket
    
    # Setup: Identical content
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    content = b'Identical certificate content'
    key = 'certs/identical.pdf'
    
    # Local
    local_file = media_root / 'identical.pdf'
    local_file.write_bytes(content)
    
    # S3
    client.put_object(Bucket=bucket, Key=key, Body=content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Run check
    results = check_consistency(check_hashes=True)
    
    # Assertions
    assert results['status'] == 'OK'
    assert len(results['hash_mismatches']) == 0
