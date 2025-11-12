"""
S3 Client Protocol and Dummy Implementation for Offline Testing

This module defines:
1. S3ClientProtocol: Interface for S3 operations
2. DummyS3Client: In-memory implementation for testing without boto3
3. RealS3ClientFactory: Production boto3 client factory

Usage in tests:
    storage = CertificateS3Storage(s3_client=DummyS3Client())
    # All operations work offline with in-memory dict + configurable latency
"""

from typing import Protocol, Dict, Any, Optional, BinaryIO
from datetime import datetime
from io import BytesIO
import hashlib
import time


class S3ClientProtocol(Protocol):
    """Protocol defining S3 client interface for dependency injection."""
    
    def put_object(self, Bucket: str, Key: str, Body: BinaryIO, **kwargs) -> Dict[str, Any]:
        """Upload object to S3."""
        ...
    
    def get_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Download object from S3."""
        ...
    
    def head_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Get object metadata."""
        ...
    
    def delete_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Delete object from S3."""
        ...
    
    def list_objects_v2(self, Bucket: str, **kwargs) -> Dict[str, Any]:
        """List objects in bucket."""
        ...
    
    def generate_presigned_url(self, ClientMethod: str, Params: Dict[str, str], 
                               ExpiresIn: int = 900, **kwargs) -> str:
        """Generate presigned URL."""
        ...


class DummyS3Client:
    """
    In-memory S3 client for offline testing.
    
    Features:
    - Stores objects in memory dict (key → bytes)
    - Configurable latency simulation (upload/download/metadata)
    - ETag generation (MD5)
    - Content-Length tracking
    - Last-Modified timestamps
    - Presigned URL generation (mocked)
    
    Usage:
        client = DummyS3Client(upload_latency_ms=50, download_latency_ms=25)
        client.put_object(Bucket='test', Key='file.pdf', Body=BytesIO(b'data'))
        obj = client.get_object(Bucket='test', Key='file.pdf')
        assert obj['Body'].read() == b'data'
    """
    
    def __init__(self, 
                 upload_latency_ms: int = 0,
                 download_latency_ms: int = 0,
                 metadata_latency_ms: int = 0,
                 fail_on_keys: Optional[set] = None):
        """
        Initialize dummy S3 client.
        
        Args:
            upload_latency_ms: Simulated upload latency (milliseconds)
            download_latency_ms: Simulated download latency (milliseconds)
            metadata_latency_ms: Simulated metadata latency (milliseconds)
            fail_on_keys: Set of keys that should raise exceptions (for failure testing)
        """
        self.storage: Dict[str, bytes] = {}  # key → content bytes
        self.metadata: Dict[str, Dict[str, Any]] = {}  # key → {ETag, ContentLength, LastModified}
        self.upload_latency_ms = upload_latency_ms
        self.download_latency_ms = download_latency_ms
        self.metadata_latency_ms = metadata_latency_ms
        self.fail_on_keys = fail_on_keys or set()
        
        # Stats for assertions
        self.put_count = 0
        self.get_count = 0
        self.head_count = 0
        self.delete_count = 0
        self.list_count = 0
    
    def _simulate_latency(self, latency_ms: int):
        """Simulate network latency."""
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)
    
    def _calculate_etag(self, content: bytes) -> str:
        """Calculate MD5 ETag for content."""
        return hashlib.md5(content).hexdigest()
    
    def _check_failure(self, key: str):
        """Raise exception if key is in fail_on_keys."""
        if key in self.fail_on_keys:
            raise Exception(f"Simulated S3 failure for key: {key}")
    
    def put_object(self, Bucket: str, Key: str, Body: BinaryIO, **kwargs) -> Dict[str, Any]:
        """Upload object to in-memory storage."""
        self._simulate_latency(self.upload_latency_ms)
        self._check_failure(Key)
        
        # Read content from file-like object
        if hasattr(Body, 'read'):
            content = Body.read()
            if hasattr(Body, 'seek'):
                Body.seek(0)  # Reset for potential re-reads
        else:
            content = Body
        
        # Store content + metadata
        self.storage[Key] = content
        etag = self._calculate_etag(content)
        self.metadata[Key] = {
            'ETag': f'"{etag}"',  # S3 wraps ETag in quotes
            'ContentLength': len(content),
            'LastModified': datetime.utcnow(),
            'Bucket': Bucket,
        }
        
        self.put_count += 1
        return {'ETag': f'"{etag}"'}
    
    def get_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Download object from in-memory storage."""
        self._simulate_latency(self.download_latency_ms)
        self._check_failure(Key)
        
        if Key not in self.storage:
            raise KeyError(f"Key not found: {Key}")
        
        content = self.storage[Key]
        meta = self.metadata[Key]
        
        self.get_count += 1
        return {
            'Body': BytesIO(content),
            'ETag': meta['ETag'],
            'ContentLength': meta['ContentLength'],
            'LastModified': meta['LastModified'],
        }
    
    def head_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Get object metadata from in-memory storage."""
        self._simulate_latency(self.metadata_latency_ms)
        self._check_failure(Key)
        
        if Key not in self.metadata:
            raise KeyError(f"Key not found: {Key}")
        
        self.head_count += 1
        return self.metadata[Key].copy()
    
    def delete_object(self, Bucket: str, Key: str, **kwargs) -> Dict[str, Any]:
        """Delete object from in-memory storage."""
        self._simulate_latency(self.metadata_latency_ms)
        self._check_failure(Key)
        
        # S3 delete is idempotent (no error if key doesn't exist)
        if Key in self.storage:
            del self.storage[Key]
            del self.metadata[Key]
        
        self.delete_count += 1
        return {}
    
    def list_objects_v2(self, Bucket: str, Prefix: str = '', **kwargs) -> Dict[str, Any]:
        """List objects in in-memory storage."""
        self._simulate_latency(self.metadata_latency_ms)
        self.list_count += 1
        
        # Filter by prefix
        matching_keys = [k for k in self.storage.keys() if k.startswith(Prefix)]
        
        contents = []
        for key in matching_keys:
            meta = self.metadata[key]
            contents.append({
                'Key': key,
                'Size': meta['ContentLength'],
                'LastModified': meta['LastModified'],
                'ETag': meta['ETag'],
            })
        
        return {
            'Contents': contents,
            'KeyCount': len(contents),
            'IsTruncated': False,
        }
    
    def generate_presigned_url(self, ClientMethod: str, Params: Dict[str, str], 
                               ExpiresIn: int = 900, **kwargs) -> str:
        """Generate mock presigned URL."""
        self._simulate_latency(self.metadata_latency_ms)
        
        bucket = Params.get('Bucket', 'unknown')
        key = Params.get('Key', 'unknown')
        
        # Mock URL format
        return f"https://{bucket}.s3.amazonaws.com/{key}?X-Amz-Expires={ExpiresIn}&X-Amz-Signature=MOCK"


def create_real_s3_client(region_name: str = 'us-east-1') -> Any:
    """
    Factory for real boto3 S3 client (production use).
    
    Args:
        region_name: AWS region
    
    Returns:
        boto3 S3 client
    
    Raises:
        ImportError: If boto3 not installed
    """
    try:
        import boto3
        return boto3.client('s3', region_name=region_name)
    except ImportError:
        raise ImportError(
            "boto3 not installed. Install with: pip install boto3\n"
            "For testing without boto3, use DummyS3Client instead."
        )
