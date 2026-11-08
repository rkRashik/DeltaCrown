"""Record lookup and authorization precede all private-origin I/O."""
import asyncio
import threading
import weakref
from io import BytesIO
from pathlib import PurePosixPath

from botocore.exceptions import ClientError
from django.utils.http import content_disposition_header, parse_etags
from django.apps import apps
from django.core.exceptions import ValidationError, FieldDoesNotExist
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotModified, HttpResponseRedirect, StreamingHttpResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from .throttles import DerivativeReadThrottle, MediaReadThrottle
from .fields import MediaFileField, MediaImageField, enabled
from . import derivatives, origin
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
    # Public-intended artwork only. Personal profile media keeps `no-store` (a private account's picture must not
    # sit in a browser cache after sign-out), though its derivatives revalidate (OL-07B).
    art = (model._meta.label_lower, field_name) in derivatives.POLICY and model._meta.label_lower != 'user_profile.userprofile'
    etag = f'"o-{derivatives.version(blob.name)}"' if art else None
    if etag and etag in parse_etags(request.headers.get('If-None-Match', '')):
        response = _apply_media_headers(HttpResponseNotModified())  # authorized above: no origin read, no bytes
    else:
        response = serve_blob(blob)
    # Artwork meant for the public may be reused by the user's own browser (never a shared cache): stable art
    # for 15 minutes, visibility-dependent art only after revalidation (the 304 above). Evidence, KYC, other
    # media and every error response stay `private, no-store`.
    if art and response.status_code in (200, 304):
        response['Cache-Control'] = derivatives.cache_control_for(model._meta.label_lower, field_name)
        response['ETag'] = etag
    return response


def serve_derivative(storage, key, lease=None):
    """Serve a stored WebP derivative, or None when it cannot be read (caller falls back to the original).

    Derivatives are small and immutable (the key embeds the record and content version), so a recently served one
    comes from a small bounded in-memory cache and a miss is read completely under a short origin lease: no
    streaming lifecycle, no slot held while the client downloads. Anything unexpectedly large still streams like a
    private original. The type is fixed by us, never taken from provider metadata. Authorization has already run.
    """
    if isinstance(storage, ProtectedS3Storage):
        data = origin.cache_get(key)
        if data is not None:
            return HttpResponse(data, content_type='image/webp')
        body = None
        lease = lease or origin.acquire(small=True)  # the derivative view already holds the request's slot
        if lease is None:
            return _busy()
        try:
            remote = storage.open_stream_object(key)
            body = remote['Body']
            size = remote.get('ContentLength')
            if isinstance(size, int) and 0 <= size <= origin.SMALL_OBJECT_BYTES:
                data = body.read(origin.SMALL_OBJECT_BYTES + 1)
                body.close()
                lease.release()
                if len(data) > origin.SMALL_OBJECT_BYTES:  # lied about its length: do not trust or cache it
                    return None
                origin.cache_put(key, data)
                return HttpResponse(data, content_type='image/webp')
            response = StreamingHttpResponse(_S3Chunks(body, b'', lease), content_type='image/webp')
            if isinstance(size, int) and size >= 0:
                response['Content-Length'] = str(size)
            return response
        except Exception as exc:
            if body is not None:
                body.close()
            lease.release()
            code = str(getattr(exc, 'response', {}).get('Error', {}).get('Code', '')) if isinstance(exc, ClientError) else ''
            if code in {'404', 'NoSuchKey', 'NotFound'}:
                return None  # not generated yet: the authorized original route still works
            # A transient provider error or timeout: retry the (tiny) derivative; do not redirect to a multi-MB original.
            response = HttpResponse('Media temporarily unavailable.', status=503)
            response['Retry-After'] = '2'
            return response
    try:
        return FileResponse(storage.open(key, 'rb'), content_type='image/webp')
    except (FileNotFoundError, OSError):
        return None


@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
@throttle_classes([DerivativeReadThrottle])
def derivative(request, label, field_name, pk, variant, ver):
    """Gate, then serve. A cold page asks for ~50 derivatives at once over HTTP/2 and every request thread would
    otherwise open its own database connection (TLS handshake on a 0.15 vCPU instance) before touching storage:
    that starved the process and shed half of them. The gate bounds how many do database + storage work at once;
    the others wait briefly for a slot (no connection held while waiting)."""
    if not enabled():
        raise Http404
    gate = origin.acquire(small=True)
    if gate is None:
        return _apply_media_headers(_busy())
    try:
        return _derivative(request, label, field_name, pk, variant, ver, gate)
    finally:
        gate.release()


def _derivative(request, label, field_name, pk, variant, ver, gate):
    """Serve a pre-generated WebP derivative under the original record's authorization.

    Anything that is not exactly an existing, current, allowlisted derivative falls back to the original
    route (which authorizes again), so a stale or not-yet-generated URL never shows a broken image.
    """
    try:
        model = apps.get_model(label)
        field = model._meta.get_field(field_name)
        if not isinstance(field, MediaImageField):
            raise Http404
        obj = get_object_or_404(model._default_manager, pk=pk)
    except (LookupError, ValueError, ValidationError, FieldDoesNotExist):
        raise Http404 from None
    if not can_download(request.user, obj, field_name):
        raise Http404
    blob = getattr(obj, field_name)
    if not blob:
        raise Http404
    original = reverse('governed_media', args=[model._meta.label_lower, field_name, str(obj.pk)])
    response = None
    current = variant in derivatives.VARIANTS and derivatives.allowed(field) and ver == derivatives.version(blob.name)
    # Never `public` (no purgeable shared cache exists). Public-intended artwork may be reused by the browser for
    # 15 minutes; visibility/privacy-dependent artwork must revalidate every time. Either way the validator is the
    # content version, so an unchanged image costs a 304, not bytes, and authorization always runs first.
    etag = f'"{ver}-{variant}"'
    cache = derivatives.cache_control(field) if derivatives.allowed(field) else 'private, no-cache'
    if current and request.headers.get('If-None-Match') == etag:
        response = HttpResponseNotModified()
    elif current:
        response = serve_derivative(blob.storage, derivatives.storage_key(
            model._meta.label_lower, field_name, obj.pk, ver, variant), gate)
    if response is None:
        response = HttpResponseRedirect(original)
        response['Cache-Control'] = 'private, max-age=60'
        return response
    if response.status_code == 503:
        return _apply_media_headers(response)  # shed: never cacheable, never carries the ETag
    if response.status_code == 200:
        _apply_media_headers(response)
    response['Cache-Control'] = cache
    response['ETag'] = etag
    return response


class _S3Chunks:
    """ASGI-native private-object streaming with bounded memory, a held origin lease and guaranteed cleanup."""

    def __init__(self, body, prefix, lease):
        self.body = body
        self.prefix = prefix
        # Runs once: on close(), or when a response abandoned by a disconnected client is garbage collected.
        self._cleanup = weakref.finalize(self, _release_origin, body, lease)

    async def __aiter__(self):
        try:
            if self.prefix:
                yield self.prefix
            loop = asyncio.get_running_loop()
            while True:
                # Never block Daphne's event loop on a remote S3 socket read; use the dedicated bounded pool.
                chunk = await loop.run_in_executor(origin.pool, self.body.read, origin.CHUNK)
                if not chunk:
                    break
                yield chunk
        finally:
            # Never block the event loop: closing a body another thread is still reading waits for that read.
            threading.Thread(target=self._cleanup, name="media-origin-close", daemon=True).start()

    def close(self):
        self._cleanup()


def _release_origin(body, lease):
    lease.release()  # free the slot first: closing a half-read body can wait for a stalled socket read
    body.close()


def _busy():
    response = HttpResponse('Media is busy, retry shortly.', status=503)
    response['Retry-After'] = '2'
    return response


def _serve_private_s3(blob):
    """Preserve record authorization, sniffed types and no-store policy."""
    body = None
    lease = origin.acquire()
    if lease is None:
        return _busy()
    try:
        remote = blob.storage.open_stream_object(blob.name)
        body = remote["Body"]
        # Sniff actual bytes, not the untrusted S3 metadata Content-Type.
        prefix = body.read(8192)
        mime = _sniff_mime(BytesIO(prefix)) or 'application/octet-stream'
        # Never reflect HTML/SVG/unknown MIME from private uploads into the browser.
        if mime not in {'image/png', 'image/jpeg', 'image/webp', 'image/gif',
                        'application/pdf', 'video/mp4', 'video/webm'}:
            mime = 'application/octet-stream'
        inline = mime in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
        response = StreamingHttpResponse(_S3Chunks(body, prefix, lease), content_type=mime)
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
        lease.release()
        code = exc.response.get('Error', {}).get('Code')
        if str(code) in {'404', 'NoSuchKey', 'NotFound'}:
            raise Http404 from None
        response = HttpResponse('Media temporarily unavailable.', status=503)
        response['Retry-After'] = '30'
    except Exception:
        if body is not None:
            body.close()
        lease.release()
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
