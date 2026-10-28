"""Record lookup and authorization precede all private-origin I/O."""
from io import BytesIO
from pathlib import PurePosixPath

from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from django.utils.http import content_disposition_header
from django.apps import apps
from django.core.exceptions import ValidationError, FieldDoesNotExist
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from .throttles import MediaReadThrottle
from .fields import MediaFileField, MediaImageField, enabled
from .storage import ProtectedS3Storage
from .policy import can_download
from apps.common.validators import _sniff_mime


@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
@throttle_classes([MediaReadThrottle])
def download(request, label, field_name, pk):
    if not enabled():
        raise Http404
    try:
        model = apps.get_model(label)
        field = model._meta.get_field(field_name)
        if not isinstance(field, (MediaFileField, MediaImageField)):
            raise Http404
        obj = get_object_or_404(model._default_manager, pk=pk)
    except (LookupError, ValueError, ValidationError, FieldDoesNotExist):
        raise Http404 from None
    if not can_download(request.user, obj, field_name):
        raise Http404
    blob = getattr(obj, field_name)
    if not blob:
        raise Http404
    return serve_blob(blob)


class _S3Chunks:
    """ASGI-native private-object streaming with bounded memory and cleanup."""

    def __init__(self, body, prefix):
        self.body = body
        self.prefix = prefix

    async def __aiter__(self):
        try:
            if self.prefix:
                yield self.prefix
            while True:
                # Do not block Daphne's event loop on a remote S3 socket read.
                chunk = await sync_to_async(self.body.read, thread_sensitive=False)(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            self.close()

    def close(self):
        self.body.close()


def _serve_private_s3(blob):
    """Preserve record authorization, sniffed types and no-store policy."""
    body = None
    try:
        remote = blob.storage.open_stream_object(blob.name)
        body = remote["Body"]
        # Sniff actual bytes, not the untrusted S3 metadata Content-Type.
        prefix = body.read(8192)
        mime = _sniff_mime(BytesIO(prefix)) or 'application/octet-stream'
        inline = mime in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
        response = StreamingHttpResponse(_S3Chunks(body, prefix), content_type=mime)
        disposition = content_disposition_header(
            not inline, PurePosixPath(blob.name).name
        )
        if disposition:
            response['Content-Disposition'] = disposition
        size = remote.get('ContentLength')
        if isinstance(size, int) and size >= 0:
            response['Content-Length'] = str(size)
    except ClientError as exc:
        if body is not None:
            body.close()
        code = exc.response.get('Error', {}).get('Code')
        if str(code) in {'404', 'NoSuchKey', 'NotFound'}:
            raise Http404 from None
        response = HttpResponse('Media temporarily unavailable.', status=503)
        response['Retry-After'] = '30'
    except Exception:
        if body is not None:
            body.close()
        response = HttpResponse('Media temporarily unavailable.', status=503)
        response['Retry-After'] = '30'
    return response


def serve_blob(blob):
    """Shared response policy, called only after the caller authorizes the record."""
    if isinstance(blob.storage, ProtectedS3Storage):
        response = _serve_private_s3(blob)
        return _apply_media_headers(response)
    try:
        blob.open('rb')
        mime = _sniff_mime(blob) or 'application/octet-stream'
        inline = mime in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
        response = FileResponse(blob, as_attachment=not inline,
                                filename=PurePosixPath(blob.name).name, content_type=mime)
    except FileNotFoundError:
        blob.close()
        raise Http404 from None
    except Exception:
        blob.close()
        response = HttpResponse('Media temporarily unavailable.', status=503)
        response['Retry-After'] = '30'
    return _apply_media_headers(response)

def _apply_media_headers(response):
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Robots-Tag'] = 'noindex, noarchive'
    response['Referrer-Policy'] = 'no-referrer'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response


@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
@throttle_classes([MediaReadThrottle])
def editor_image(request, token):
    # A staff upload is a deliberate public publication, never a private record.
    from django.core import signing
    from django.core.files.storage import storages
    if not enabled():
        raise Http404
    try:
        name = signing.loads(token, salt='published-editor-image')
        if not isinstance(name, str) or not name.startswith('editor/') or '..' in name or '\\' in name:
            raise Http404
        blob = storages['public_media'].open(name, 'rb')
        mime = _sniff_mime(blob)
        if mime not in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}:
            blob.close()
            raise Http404
        response = FileResponse(blob, content_type=mime)
    except (signing.BadSignature, FileNotFoundError, ValueError):
        raise Http404 from None
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Robots-Tag'] = 'noindex, noarchive'
    response['Referrer-Policy'] = 'no-referrer'
    return response
