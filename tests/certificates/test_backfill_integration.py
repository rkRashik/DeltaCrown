"""
Backfill Script Tests - Moto Integration

Tests backfill_certificates_to_s3.py script with moto S3 backend.

Coverage:
- Batch processing with --limit
- Resume with --resume-token
- Hash verification (MD5/ETag matching)
- Error handling
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch
from django.test import override_settings
from django.core.files.base import ContentFile


@pytest.mark.s3
@override_settings(
    CERT_S3_BACKFILL_ENABLED=True,
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_backfill_limit_parameter(moto_bucket, tmp_path, monkeypatch):
    """
    Test: --limit parameter limits files processed.
    
    Validates:
    - Create 10 local files
    - Backfill with --limit 5
    - Exactly 5 files uploaded to S3
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    
    client, resource, bucket = moto_bucket
    
    # Setup: Create 10 local PDF files
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    for i in range(10):
        pdf_file = media_root / f'cert-{i:03d}.pdf'
        pdf_file.write_bytes(b'PDF content %d' % i)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Backfill with limit=5
    stats = backfill_certificates(limit=5, verify_hash=False, dry_run=False)
    
    # Assertions
    assert stats['uploaded_count'] == 5, "Should upload exactly 5 files"
    assert stats['errors'] == []
    
    # Verify S3 has 5 objects
    response = client.list_objects_v2(Bucket=bucket)
    assert response.get('KeyCount', 0) == 5


@pytest.mark.s3
@override_settings(
    CERT_S3_BACKFILL_ENABLED=True,
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_backfill_resume_token(moto_bucket, tmp_path, monkeypatch):
    """
    Test: --resume-token resumes from specific file.
    
    Validates:
    - Create 5 files: cert-000, cert-001, cert-002, cert-003, cert-004
    - Resume from cert-002.pdf
    - Only cert-002, cert-003, cert-004 uploaded (3 files)
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    
    client, resource, bucket = moto_bucket
    
    # Setup: Create 5 files
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    for i in range(5):
        pdf_file = media_root / f'cert-{i:03d}.pdf'
        pdf_file.write_bytes(b'PDF content %d' % i)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Backfill with resume_token pointing to cert-002.pdf
    stats = backfill_certificates(
        limit=None,
        resume_token='cert-002.pdf',
        verify_hash=False,
        dry_run=False
    )
    
    # Should upload cert-002, cert-003, cert-004 (3 files)
    assert stats['uploaded_count'] == 3, "Should upload 3 files (from cert-002 onwards)"
    
    # Verify S3 objects
    response = client.list_objects_v2(Bucket=bucket)
    keys = sorted([obj['Key'] for obj in response.get('Contents', [])])
    assert len(keys) == 3
    assert 'certs/cert-002.pdf' in keys
    assert 'certs/cert-004.pdf' in keys


@pytest.mark.s3
@override_settings(
    CERT_S3_BACKFILL_ENABLED=True,
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_backfill_verify_hash_success(moto_bucket, tmp_path, monkeypatch):
    """
    Test: --verify-hash validates MD5/ETag matches.
    
    Validates:
    - Upload file with known content
    - Verify hash matches between local and S3
    - verified_count increments
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    import hashlib
    
    client, resource, bucket = moto_bucket
    
    # Setup: Create file with known content
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    test_content = b'Certificate PDF with known hash'
    expected_md5 = hashlib.md5(test_content).hexdigest()
    
    pdf_file = media_root / 'test-hash.pdf'
    pdf_file.write_bytes(test_content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Backfill with hash verification
    stats = backfill_certificates(
        limit=None,
        resume_token=None,
        verify_hash=True,
        dry_run=False
    )
    
    # Assertions
    assert stats['uploaded_count'] == 1
    assert stats['verified_count'] == 1, "Hash verification should succeed"
    assert stats['errors'] == []


@pytest.mark.s3
@override_settings(
    CERT_S3_BACKFILL_ENABLED=True,
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_backfill_verify_hash_mismatch_error(moto_bucket, tmp_path, monkeypatch):
    """
    Test: --verify-hash detects MD5/ETag mismatch.
    
    Validates:
    - Upload file
    - Simulate corrupted ETag in S3
    - Error captured in stats['errors']
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    from unittest.mock import Mock, patch
    
    client, resource, bucket = moto_bucket
    
    # Setup
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    pdf_file = media_root / 'corrupted.pdf'
    pdf_file.write_bytes(b'Original content')
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Mock head_object to return wrong ETag
    original_head = client.head_object
    
    def mock_head_object(Bucket, Key):
        response = original_head(Bucket=Bucket, Key=Key)
        response['ETag'] = '"wronghash123456789"'  # Corrupt ETag
        return response
    
    with patch.object(client, 'head_object', side_effect=mock_head_object):
        stats = backfill_certificates(
            limit=None,
            verify_hash=True,
            dry_run=False
        )
    
    # Should have error for hash mismatch
    assert stats['uploaded_count'] == 1
    assert len(stats['errors']) > 0
    assert 'HASH MISMATCH' in stats['errors'][0]


@pytest.mark.s3
@override_settings(
    CERT_S3_BACKFILL_ENABLED=True,
    CERT_S3_DUAL_WRITE=True,
    AWS_STORAGE_BUCKET_NAME='test-deltacrown-certificates'
)
def test_backfill_skip_existing_files(moto_bucket, tmp_path, monkeypatch):
    """
    Test: Files already in S3 are skipped.
    
    Validates:
    - Pre-populate S3 with file
    - Backfill same file
    - Skipped (not re-uploaded)
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    
    client, resource, bucket = moto_bucket
    
    # Setup
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    
    pdf_file = media_root / 'existing.pdf'
    content = b'Already in S3'
    pdf_file.write_bytes(content)
    
    # Pre-upload to S3
    client.put_object(Bucket=bucket, Key='certs/existing.pdf', Body=content)
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Backfill (should skip)
    stats = backfill_certificates(limit=None, dry_run=False)
    
    # Assertions
    assert stats['uploaded_count'] == 0, "Should not re-upload existing file"
    assert stats['skipped_count'] == 1, "Should skip existing file"


@pytest.mark.s3
@override_settings(CERT_S3_BACKFILL_ENABLED=False)
def test_backfill_disabled_feature_flag(tmp_path, monkeypatch):
    """
    Test: CERT_S3_BACKFILL_ENABLED=False prevents backfill.
    
    Validates:
    - Backfill aborts with error
    - No uploads occur
    """
    from scripts.backfill_certificates_to_s3 import backfill_certificates
    
    # Setup
    media_root = tmp_path / 'media' / 'certs'
    media_root.mkdir(parents=True, exist_ok=True)
    pdf_file = media_root / 'test.pdf'
    pdf_file.write_bytes(b'test')
    
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    
    # Backfill should abort
    stats = backfill_certificates(limit=None)
    
    assert 'error' in stats
    assert 'disabled' in stats['error'].lower()
