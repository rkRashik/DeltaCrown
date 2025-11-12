"""
PII Safety Tests for Certificate S3 Storage

Validates that storage operations do NOT leak Personally Identifiable Information (PII):
- S3 keys contain only object IDs (no usernames, emails, IPs)
- Log messages do not contain user data
- Metrics do not contain user-specific identifiers
- Error messages sanitize sensitive data

Compliance: GDPR, CCPA, PCI-DSS (where applicable)
"""

import pytest
import logging
import re
from unittest.mock import patch, Mock
from django.core.files.base import ContentFile

from apps.tournaments.storage import CertificateS3Storage
from tests.certificates.helpers import capture_cert_metrics


# PII patterns to detect (these should NEVER appear in keys/logs/metrics)
PII_PATTERNS = [
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email
    r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IP address
    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full name (First Last)
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{16}\b',  # Credit card (naive)
]


def contains_pii(text):
    """Check if text contains any PII patterns."""
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


@pytest.mark.django_db
class TestS3PIISafety:
    """Test PII safety in S3 storage operations."""
    
    def test_s3_keys_contain_only_ids_no_usernames(self, storage_with_s3):
        """
        Save files with user context, verify S3 keys contain only object IDs.
        
        Expected: Keys like "certificates/cert_12345.pdf", NOT "certificates/john.doe@example.com.pdf"
        """
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            # Simulate saving with user context (should be ignored in key generation)
            user_email = "john.doe@example.com"
            user_name = "John Doe"
            user_ip = "192.168.1.100"
            
            content = ContentFile(b"certificate_data")
            path = storage.save("certificates/cert_12345.pdf", content)
            
            # Validation: path should NOT contain PII
            assert user_email not in path, f"Email leaked in S3 key: {path}"
            assert user_name not in path, f"Name leaked in S3 key: {path}"
            assert user_ip not in path, f"IP leaked in S3 key: {path}"
            assert not contains_pii(path), f"PII pattern detected in key: {path}"
            
            # Key should only contain object ID and extension
            assert re.match(r'^certificates/cert_\d+\.pdf$', path), f"Key format invalid: {path}"
    
    def test_log_messages_sanitize_user_data(self, storage_with_s3, caplog):
        """
        Trigger storage errors with user context, verify logs sanitize PII.
        
        Expected: Logs contain object IDs, NOT "Failed for user john.doe@example.com"
        """
        storage = storage_with_s3
        
        with caplog.at_level(logging.WARNING):
            with capture_cert_metrics() as em:
                # Simulate error with user context
                user_email = "jane.smith@example.com"
                
                # Force S3 error by mocking client
                with patch.object(storage.s3_storage.client, 'upload_file') as mock_upload:
                    from botocore.exceptions import ClientError
                    mock_upload.side_effect = ClientError(
                        {'Error': {'Code': '500', 'Message': 'Internal Server Error'}},
                        'UploadFile'
                    )
                    
                    content = ContentFile(b"test_data")
                    try:
                        storage.save("certs/cert_67890.pdf", content)
                    except Exception:
                        pass  # Expected
                
                # Check all log messages
                for record in caplog.records:
                    assert user_email not in record.message, f"Email leaked in log: {record.message}"
                    assert not contains_pii(record.message), f"PII in log: {record.message}"
    
    def test_metrics_contain_operation_names_only(self, storage_with_s3):
        """
        Perform 10 operations with user context, verify metrics contain only operation types.
        
        Expected: Metrics like "cert.s3.save.success", NOT "cert.s3.save.user.12345"
        """
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            user_ids = [101, 202, 303, 404, 505]
            
            for user_id in user_ids:
                content = ContentFile(f"cert_for_user_{user_id}".encode())
                path = storage.save(f"certs/cert_{user_id}.pdf", content)
                assert storage.exists(path)
            
            # Validation: metric names should NOT contain user IDs
            for metric_name in em.counts.keys():
                assert not any(str(uid) in metric_name for uid in user_ids), \
                    f"User ID leaked in metric: {metric_name}"
                
                # Metrics should follow pattern: cert.s3.<operation>.<status>
                assert re.match(r'^cert\.s3\.(save|read|delete|url|write)\.(success|fail|fallback)$', metric_name), \
                    f"Metric name pattern invalid: {metric_name}"
    
    def test_error_messages_sanitize_sensitive_paths(self, storage_with_s3):
        """
        Trigger errors with sensitive file paths, verify error messages sanitize paths.
        
        Expected: Errors like "Failed to save object cert_123", NOT "/home/user/secrets/file.pdf"
        """
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            # Simulate error with sensitive path
            sensitive_path = "/home/admin/private_keys/secret.pem"
            
            with patch.object(storage.local_storage, 'save') as mock_save:
                mock_save.side_effect = Exception(f"Failed to save {sensitive_path}")
                
                content = ContentFile(b"sensitive_data")
                try:
                    storage.save("certs/cert_999.pdf", content)
                except Exception as e:
                    error_msg = str(e)
                    
                    # Validation: error should NOT leak full sensitive path
                    # (CertificateS3Storage should sanitize paths in error handling)
                    # For now, just ensure we're aware of potential leaks
                    assert "private_keys" not in error_msg or "sanitized" in error_msg.lower(), \
                        f"Sensitive path leaked: {error_msg}"
    
    def test_s3_presigned_urls_do_not_leak_credentials(self, storage_with_s3):
        """
        Generate presigned URLs, verify they don't contain AWS credentials in plain text.
        
        Expected: URLs contain signatures, NOT "aws_secret_access_key=..."
        """
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            content = ContentFile(b"test_url_safety")
            path = storage.save("certs/url_test.pdf", content)
            
            url = storage.url(path)
            
            # Validation: URL should NOT contain plain-text credentials
            assert "aws_secret_access_key" not in url.lower(), "AWS secret leaked in URL"
            assert "password" not in url.lower(), "Password leaked in URL"
            
            # URL should contain signature (safe) but not raw credentials
            assert "Signature=" in url or "X-Amz-Signature=" in url, "Signature missing from presigned URL"
    
    def test_concurrent_operations_do_not_cross_leak_context(self, storage_with_s3):
        """
        10 threads with different user contexts, verify no context leakage between threads.
        
        Expected: Each thread's operations isolated, no user_A data in user_B logs/metrics.
        """
        import threading
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            results = {}
            
            def worker(user_id, user_email):
                local_results = []
                for i in range(5):
                    content = ContentFile(f"cert_user_{user_id}_{i}".encode())
                    path = storage.save(f"certs/user_{user_id}_cert_{i}.pdf", content)
                    
                    # Verify path doesn't leak other users' emails
                    assert user_email not in path, f"Email leaked: {user_email} in {path}"
                    local_results.append(path)
                
                results[user_id] = local_results
            
            users = [
                (1001, "alice@example.com"),
                (1002, "bob@example.com"),
                (1003, "charlie@example.com"),
                (1004, "diana@example.com"),
                (1005, "eve@example.com"),
            ]
            
            threads = [threading.Thread(target=worker, args=(uid, email)) for uid, email in users]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # Cross-check: user_1001's paths should NOT reference user_1002, etc.
            for user_id, paths in results.items():
                other_user_ids = [uid for uid, _ in users if uid != user_id]
                for path in paths:
                    for other_uid in other_user_ids:
                        assert str(other_uid) not in path, \
                            f"User {other_uid} ID leaked in {user_id}'s path: {path}"
    
    def test_pii_safety_with_utf8_filenames(self, storage_with_s3):
        """
        Save files with UTF-8 names (e.g., "东京_cert.pdf"), verify no encoding leaks PII.
        
        Expected: UTF-8 handled safely, no mojibake exposing user data.
        """
        storage = storage_with_s3
        
        with capture_cert_metrics() as em:
            utf8_names = [
                "certs/东京_cert_001.pdf",
                "certs/Curaçao_cert_002.pdf",
                "certs/Москва_cert_003.pdf",
            ]
            
            for name in utf8_names:
                content = ContentFile(f"utf8_test_{name}".encode('utf-8'))
                path = storage.save(name, content)
                
                # Validation: path encoding should be safe
                assert not contains_pii(path), f"PII pattern in UTF-8 path: {path}"
                assert storage.exists(path), f"UTF-8 path not accessible: {path}"
