"""
S3 Storage Backend for Certificate Files

Module: 6.5 - Certificate Storage Migration (S3)
Status: Implemented (behind feature flags)

This module provides:
- Dual-write capability (S3 primary + local shadow)
- Shadow-read fallback (S3 → local if S3 unavailable)
- Feature flags for safe rollout
- Presigned URL generation with 15-minute TTL
- No PII in object keys (UUID-based naming)

Feature Flags (all default OFF):
- CERT_S3_DUAL_WRITE: Enable S3 writes alongside local writes
- CERT_S3_READ_PRIMARY: Prefer S3 for reads (fallback to local)
- CERT_S3_BACKFILL_ENABLED: Enable background migration job

Usage:
    # In models.py
    from apps.tournaments.storage import CertificateS3Storage
    
    class Certificate(models.Model):
        file_pdf = models.FileField(
            upload_to='pdf/%Y/%m/',
            storage=CertificateS3Storage()
        )

Security:
- Private objects (no public ACL)
- Presigned URLs with 15-minute expiration
- Server-side encryption (SSE-S3 AES-256)
- HTTPS enforcement (bucket policy)

Performance:
- Target p95 <400ms for S3 upload (≤1MB files)
- Presigned URL generation p95 <100ms
- Connection pool: 10 concurrent connections
- Multipart threshold: 5MB
"""

import logging
from typing import Optional, Dict, Any
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    STORAGES_AVAILABLE = True
except ImportError:
    STORAGES_AVAILABLE = False
    S3Boto3Storage = None  # type: ignore

logger = logging.getLogger(__name__)


class CertificateS3Storage:
    """
    Dual-write storage backend for certificate files.
    
    Features:
    - Writes to S3 (primary) and local FS (shadow) when CERT_S3_DUAL_WRITE=True
    - Reads from S3 with fallback to local FS when CERT_S3_READ_PRIMARY=True
    - Falls back to local-only mode when flags are OFF
    - Emits metrics for monitoring (success/failure counters)
    
    Flags:
    - CERT_S3_DUAL_WRITE (default False): Enable S3 writes
    - CERT_S3_READ_PRIMARY (default False): Prefer S3 for reads
    - CERT_S3_BACKFILL_ENABLED (default False): Enable migration job
    """
    
    def __init__(self, s3_client=None, **kwargs):
        """
        Initialize storage backend with feature flag checks.
        
        Args:
            s3_client: Optional S3 client for dependency injection (for testing with DummyS3Client)
            **kwargs: Additional storage configuration
        
        Raises:
            ImproperlyConfigured: If S3 enabled but django-storages not installed
        """
        self.dual_write_enabled = getattr(settings, 'CERT_S3_DUAL_WRITE', False)
        self.read_primary_s3 = getattr(settings, 'CERT_S3_READ_PRIMARY', False)
        
        # Local storage (always available for shadow writes and fallback)
        self.local_storage = FileSystemStorage(
            location=settings.MEDIA_ROOT,
            base_url=settings.MEDIA_URL
        )
        
        # S3 storage (only if enabled and storages available, or injected for testing)
        self.s3_storage = None
        self.s3_client = s3_client  # For direct S3 operations (testing)
        
        if self.dual_write_enabled or self.read_primary_s3 or s3_client:
            if s3_client:
                # Testing mode: use injected client directly
                self.s3_storage = None  # Bypass S3Boto3Storage wrapper
                self.s3_client = s3_client
            else:
                # Production mode: use S3Boto3Storage
                if not STORAGES_AVAILABLE:
                    raise ImproperlyConfigured(
                        "S3 storage enabled but django-storages not installed. "
                        "Install with: pip install django-storages[s3] boto3"
                    )
                
                # Configure S3 storage
                self.s3_storage = S3Boto3Storage(
                    bucket_name=getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'deltacrown-certificates-prod'),
                    region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
                    default_acl=None,  # Private objects
                    querystring_auth=True,  # Enable presigned URLs
                    querystring_expire=900,  # 15 minutes (900 seconds)
                    object_parameters={
                        'CacheControl': 'private, max-age=600',  # 10min browser cache
                        'ServerSideEncryption': 'AES256',  # SSE-S3 encryption
                    },
                    file_overwrite=False,  # Prevent accidental overwrites
                    max_memory_size=5242880,  # 5MB multipart threshold
                    use_threads=True,  # Concurrent uploads
                    **kwargs
                )
    
    def _emit_metric(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, Any]] = None):
        """
        Emit metric for monitoring (counters).
        
        Metrics:
        - cert.s3.write.success: Successful S3 uploads
        - cert.s3.write.fail: Failed S3 uploads
        - cert.s3.read.success: Successful S3 reads
        - cert.s3.read.fallback: S3 read failures (fell back to local)
        
        Args:
            metric_name: Metric name (e.g., 'cert.s3.write.success')
            value: Metric value (default 1 for counters)
            tags: Optional metric tags (e.g., {'operation': 'upload'})
        """
        # TODO: Integrate with observability framework (e.g., StatsD, CloudWatch)
        # For now, log metrics for manual collection
        logger.info(
            f"METRIC: {metric_name}={value}",
            extra={'metric_name': metric_name, 'value': value, 'tags': tags or {}}
        )
    
    def _safe_s3_operation(self, operation: str, *args, **kwargs):
        """
        Execute S3 operation with error handling and metrics.
        
        Args:
            operation: S3Boto3Storage method name (e.g., 'save', 'exists', 'url')
            *args, **kwargs: Method arguments
        
        Returns:
            Operation result or None on failure
        """
        if not self.s3_storage:
            return None
        
        try:
            method = getattr(self.s3_storage, operation)
            result = method(*args, **kwargs)
            self._emit_metric(f'cert.s3.{operation}.success')
            return result
        except Exception as e:
            self._emit_metric(f'cert.s3.{operation}.fail', tags={'error': type(e).__name__})
            logger.warning(
                f"S3 {operation} failed: {e}",
                exc_info=True,
                extra={'operation': operation, 'call_args': args, 'call_kwargs': kwargs}
            )
            return None
    
    def save(self, name: str, content, max_length: Optional[int] = None):
        """
        Save file to S3 (primary) and local FS (shadow).
        
        Behavior:
        - CERT_S3_DUAL_WRITE=True: Write to S3 + local (shadow)
        - CERT_S3_DUAL_WRITE=False: Write to local only
        
        Args:
            name: File name (e.g., 'pdf/2025/11/uuid.pdf')
            content: File content (File object or ContentFile)
            max_length: Max filename length (ignored)
        
        Returns:
            str: Saved filename (relative path)
        """
        # Always save to local (primary if dual_write OFF, shadow if ON)
        local_name = self.local_storage.save(name, content)
        
        # Save to S3 if dual-write enabled
        if self.dual_write_enabled and self.s3_storage:
            # Reset content position for second write
            if hasattr(content, 'seek'):
                content.seek(0)
            
            s3_name = self._safe_s3_operation('save', name, content, max_length=max_length)
            if s3_name:
                logger.info(f"Dual-write succeeded: local={local_name}, s3={s3_name}")
                return s3_name  # Return S3 name for consistency
            else:
                logger.warning(f"Dual-write S3 failed, using local: {local_name}")
        
        return local_name
    
    def exists(self, name: str) -> bool:
        """
        Check if file exists in S3 (primary) or local FS (fallback).
        
        Behavior:
        - CERT_S3_READ_PRIMARY=True: Check S3 first, fallback to local
        - CERT_S3_READ_PRIMARY=False: Check local only
        
        Args:
            name: File name to check
        
        Returns:
            bool: True if file exists
        """
        if self.read_primary_s3 and self.s3_storage:
            s3_exists = self._safe_s3_operation('exists', name)
            if s3_exists is not None:
                return s3_exists
            # Fallback to local on S3 error
            self._emit_metric('cert.s3.read.fallback', tags={'operation': 'exists'})
        
        return self.local_storage.exists(name)
    
    def url(self, name: str) -> str:
        """
        Generate presigned URL (S3) or local URL (fallback).
        
        Behavior:
        - CERT_S3_READ_PRIMARY=True: Generate S3 presigned URL (15min TTL)
        - CERT_S3_READ_PRIMARY=False: Generate local URL
        
        Args:
            name: File name
        
        Returns:
            str: URL for file access
        """
        if self.read_primary_s3 and self.s3_storage:
            s3_url = self._safe_s3_operation('url', name)
            if s3_url:
                return s3_url
            # Fallback to local on S3 error
            self._emit_metric('cert.s3.read.fallback', tags={'operation': 'url'})
        
        return self.local_storage.url(name)
    
    def open(self, name: str, mode: str = 'rb'):
        """
        Open file from S3 (primary) or local FS (fallback).
        
        Args:
            name: File name
            mode: File open mode (default 'rb')
        
        Returns:
            File object
        """
        if self.read_primary_s3 and self.s3_storage:
            try:
                file_obj = self.s3_storage.open(name, mode)
                self._emit_metric('cert.s3.read.success', tags={'operation': 'open'})
                return file_obj
            except Exception as e:
                self._emit_metric('cert.s3.read.fallback', tags={'operation': 'open', 'error': type(e).__name__})
                logger.warning(f"S3 open failed, falling back to local: {e}")
        
        return self.local_storage.open(name, mode)
    
    def delete(self, name: str):
        """
        Delete file from both S3 and local FS.
        
        Args:
            name: File name to delete
        """
        # Delete from S3 if enabled
        if (self.dual_write_enabled or self.read_primary_s3) and self.s3_storage:
            self._safe_s3_operation('delete', name)
        
        # Always delete from local
        if self.local_storage.exists(name):
            self.local_storage.delete(name)
    
    def size(self, name: str) -> int:
        """
        Get file size from S3 (primary) or local FS (fallback).
        
        Args:
            name: File name
        
        Returns:
            int: File size in bytes
        """
        if self.read_primary_s3 and self.s3_storage:
            s3_size = self._safe_s3_operation('size', name)
            if s3_size is not None:
                return s3_size
            self._emit_metric('cert.s3.read.fallback', tags={'operation': 'size'})
        
        return self.local_storage.size(name)
    
    def get_accessed_time(self, name: str):
        """Get file last accessed time (local FS only)."""
        return self.local_storage.get_accessed_time(name)
    
    def get_created_time(self, name: str):
        """Get file creation time (local FS only)."""
        return self.local_storage.get_created_time(name)
    
    def get_modified_time(self, name: str):
        """Get file last modified time (local FS only)."""
        return self.local_storage.get_modified_time(name)


# Convenience function for model usage
def get_certificate_storage():
    """
    Get configured certificate storage backend.
    
    Returns:
        CertificateS3Storage: Storage backend instance
    """
    return CertificateS3Storage()
