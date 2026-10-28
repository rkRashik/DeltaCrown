"""Synthetic-only S3 media streaming tests: no credentials or external IO."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from botocore.exceptions import ClientError
from django.http import Http404
from django.test import SimpleTestCase

from apps.common.media.storage import ProtectedS3Storage
from apps.common.media.views import serve_blob


class FakeBody:
    def __init__(self, content):
        self.stream = BytesIO(content)
        self.closed = False

    def read(self, size=-1):
        return self.stream.read(size)

    def close(self):
        self.closed = True
        self.stream.close()


async def read_stream(response):
    result = bytearray()
    async for chunk in response.streaming_content:
        result.extend(chunk)
    return bytes(result)


class S3MediaStreamTests(SimpleTestCase):
    def setUp(self):
        self.storage = ProtectedS3Storage(
            bucket_name='synthetic',
            access_key='synthetic',
            secret_key='synthetic',
            region_name='ap-south-1',
            endpoint_url='https://example.invalid',
        )
        self.blob = SimpleNamespace(storage=self.storage, name='cards/7.png')

    def test_streams_large_object_as_async_chunks_not_spooled_file(self):
        payload = b'\x89PNG\r\n\x1a\n' + b'x' * (1024 * 1024)
        body = FakeBody(payload)
        with patch.object(self.storage, 'open_stream_object',
                          return_value={'Body': body, 'ContentLength': len(payload)}) as get:
            response = serve_blob(self.blob)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.is_async)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(response['Content-Length'], str(len(payload)))
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(async_to_sync(read_stream)(response), payload)
            response.close()
        self.assertTrue(body.closed)
        get.assert_called_once_with('cards/7.png')

    def test_unknown_content_fails_closed_as_download(self):
        body = FakeBody(b'<html>danger</html>')
        with patch.object(self.storage, 'open_stream_object',
                          return_value={'Body': body, 'ContentLength': 19}):
            response = serve_blob(self.blob)
            self.assertEqual(response['Content-Type'], 'application/octet-stream')
            self.assertTrue(response['Content-Disposition'].startswith('attachment'))
            response.close()
            self.assertTrue(body.closed)

    def test_storage_unavailable_returns_retryable_503_never_public_fallback(self):
        with patch.object(self.storage, 'open_stream_object',
                          side_effect=OSError('synthetic origin failure')):
            response = serve_blob(self.blob)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '30')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_missing_s3_object_is_404(self):
        err = ClientError({'Error': {'Code': 'NoSuchKey', 'Message': 'missing'}}, 'GetObject')
        with patch.object(self.storage, 'open_stream_object', side_effect=err):
            with self.assertRaises(Http404):
                serve_blob(self.blob)
