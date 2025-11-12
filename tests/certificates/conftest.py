"""
Pytest Configuration and Fixtures for Certificate S3 Tests

Provides:
- moto S3 backend fixtures
- Storage factory with S3Boto3Storage injection
- Spy/mock utilities for call tracking
- Feature flag override helpers
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from django.test import override_settings
from django.core.files.base import ContentFile


@pytest.fixture(scope="function")
def moto_s3():
    """
    Start moto S3 mock for integration tests.
    
    Usage:
        @pytest.mark.s3
        def test_something(moto_s3):
            # boto3 calls will use mocked S3
            client = boto3.client('s3', region_name='us-east-1')
            client.create_bucket(Bucket='test-bucket')
    """
    with mock_aws():
        yield


@pytest.fixture(scope="function")
def moto_bucket(moto_s3):
    """
    Create moto S3 bucket for tests.
    
    Returns:
        tuple: (boto3.client, boto3.resource, bucket_name)
    """
    region = 'us-east-1'
    bucket_name = 'test-deltacrown-certificates'
    
    client = boto3.client('s3', region_name=region)
    resource = boto3.resource('s3', region_name=region)
    
    # Create bucket
    client.create_bucket(Bucket=bucket_name)
    
    # Configure bucket for presigned URLs
    client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
            'CORSRules': [{
                'AllowedOrigins': ['*'],
                'AllowedMethods': ['GET', 'HEAD'],
                'AllowedHeaders': ['*'],
                'MaxAgeSeconds': 3000
            }]
        }
    )
    
    yield client, resource, bucket_name
    
    # Cleanup: delete all objects and bucket
    try:
        bucket = resource.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.delete()
    except:
        pass


@pytest.fixture
def storage_with_s3(moto_bucket, monkeypatch, tmp_path):
    """
    Create CertificateS3Storage with real S3Boto3Storage (via moto).
    
    This fixture:
    - Uses moto-backed S3 (not DummyS3Client)
    - Sets AWS credentials for moto
    - Patches STORAGES_AVAILABLE to True
    - Overrides settings for S3 configuration
    - Returns storage instance that exercises S3Boto3Storage paths
    
    Returns:
        tuple: (storage, client, resource, bucket_name)
    """
    import apps.tournaments.storage as storage_module
    from storages.backends.s3boto3 import S3Boto3Storage
    import os
    
    client, resource, bucket_name = moto_bucket
    
    # CRITICAL: Patch STORAGES_AVAILABLE and S3Boto3Storage to bypass import-time cache
    monkeypatch.setattr(storage_module, 'STORAGES_AVAILABLE', True)
    monkeypatch.setattr(storage_module, 'S3Boto3Storage', S3Boto3Storage)
    
    # Set fake AWS credentials for moto (required by boto3)
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    
    # Override Django settings
    monkeypatch.setattr('django.conf.settings.AWS_STORAGE_BUCKET_NAME', bucket_name)
    monkeypatch.setattr('django.conf.settings.AWS_S3_REGION_NAME', 'us-east-1')
    monkeypatch.setattr('django.conf.settings.AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setattr('django.conf.settings.AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setattr('django.conf.settings.MEDIA_ROOT', str(tmp_path / 'media'))
    monkeypatch.setattr('django.conf.settings.MEDIA_URL', '/media/')
    
    # Enable S3 features
    monkeypatch.setattr('django.conf.settings.CERT_S3_DUAL_WRITE', True)
    monkeypatch.setattr('django.conf.settings.CERT_S3_READ_PRIMARY', True)
    
    # Now import after patching
    from apps.tournaments.storage import CertificateS3Storage
    
    # Create storage WITHOUT s3_client injection (forces S3Boto3Storage usage)
    storage = CertificateS3Storage()
    
    # Ensure local media directory exists
    os.makedirs(tmp_path / 'media', exist_ok=True)
    
    return storage, client, resource, bucket_name


@pytest.fixture
def spy_local_storage():
    """
    Create spy for local storage operations.
    
    Usage:
        def test_read_primary_no_local_touch(storage, spy_local_storage):
            with spy_local_storage(storage.local_storage, 'open') as spy:
                storage.open('test.pdf')
                assert spy.call_count == 0  # S3 path, no local touch
    """
    from unittest.mock import patch
    
    class SpyContext:
        def __init__(self, obj, method_name):
            self.obj = obj
            self.method_name = method_name
            self.spy = None
            self.patcher = None
        
        def __enter__(self):
            original_method = getattr(self.obj, self.method_name)
            self.spy = Mock(wraps=original_method)
            self.patcher = patch.object(self.obj, self.method_name, self.spy)
            self.patcher.__enter__()
            return self.spy
        
        def __exit__(self, *args):
            if self.patcher:
                self.patcher.__exit__(*args)
    
    def create_spy(obj, method_name):
        return SpyContext(obj, method_name)
    
    return create_spy


@pytest.fixture
def mock_metric_emission():
    """
    Mock metric emission for validation.
    
    Usage:
        def test_metric_emitted(storage, mock_metric_emission):
            with mock_metric_emission(storage) as mock:
                storage.save('test.pdf', ContentFile(b'data'))
                mock.assert_any_call('cert.s3.write.success', 1, tags=None)
    """
    def create_mock(storage_instance):
        return patch.object(storage_instance, '_emit_metric', wraps=storage_instance._emit_metric)
    
    return create_mock


@pytest.fixture
def s3_error_injector(moto_bucket):
    """
    Inject S3 errors for testing error paths.
    
    Usage:
        def test_s3_error_fallback(storage, s3_error_injector):
            with s3_error_injector('get_object', 'NoSuchKey'):
                # Next S3 operation will raise NoSuchKey
                file = storage.open('missing.pdf')  # Falls back to local
    """
    from botocore.exceptions import ClientError
    
    client, _, _ = moto_bucket
    
    class ErrorInjector:
        def __init__(self, operation, error_code):
            self.operation = operation
            self.error_code = error_code
            self.patcher = None
        
        def __enter__(self):
            def error_raiser(*args, **kwargs):
                raise ClientError(
                    {'Error': {'Code': self.error_code, 'Message': 'Injected error'}},
                    self.operation
                )
            
            # Patch the client method
            self.patcher = patch.object(
                client,
                self.operation,
                side_effect=error_raiser
            )
            self.patcher.__enter__()
            return self
        
        def __exit__(self, *args):
            if self.patcher:
                self.patcher.__exit__(*args)
    
    def inject_error(operation, error_code='InternalError'):
        return ErrorInjector(operation, error_code)
    
    return inject_error


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "s3: S3 integration tests (run with S3_TESTS=1)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip S3 tests if S3_TESTS not set."""
    skip_s3 = pytest.mark.skip(reason="S3_TESTS=0 (offline mode)")
    s3_tests_enabled = os.environ.get('S3_TESTS', '0') == '1'
    
    for item in items:
        if "s3" in item.keywords and not s3_tests_enabled:
            item.add_marker(skip_s3)
