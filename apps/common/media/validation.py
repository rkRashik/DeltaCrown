"""Bounded upload validation at FieldFile.save, including direct/admin writes."""
import warnings
from pathlib import PurePosixPath
from PIL import Image
from django.core.exceptions import ValidationError
from django.db.models import ImageField
from apps.common.validators import _sniff_mime, validate_document_upload, validate_image_upload


def validate_upload(content, field, instance):
    pos = content.tell()
    try:
        content.seek(0)
        if content.size > 20 * 1024 * 1024:
            raise ValidationError('Media exceeds the 20 MiB platform safety limit.')
        label = field.model._meta.label_lower
        image = isinstance(field, ImageField)
        is_video = label in {'organizations.teammedia', 'siteui.communitypostmedia', 'tournaments.matchmedia'} and (
            getattr(instance, 'file_type', '') == 'video' or getattr(instance, 'media_type', '') == 'video'
        )
        if label == 'tournaments.matchmedia' and getattr(instance, 'media_type', '') == 'replay':
            if PurePosixPath(content.name).suffix.lower() not in {'.dem', '.replay', '.rofl'}:
                raise ValidationError('Unsupported replay extension.')
            return  # Opaque, private attachment only; not interpreted or executed.
        if is_video:
            header = content.read(32); content.seek(0)
            ext = PurePosixPath(content.name).suffix.lower()
            if not ((ext == '.mp4' and header[4:8] == b'ftyp') or
                    (ext == '.webm' and header[:4] == b'\x1aE\xdf\xa3')):
                raise ValidationError('Invalid video container; MP4/WebM required.')
            if content.size > 10 * 1024 * 1024:
                raise ValidationError('Video exceeds the existing 10 MiB gallery limit.')
            return  # TeamMedia's legacy PDF-only validator is not a video validator.
        gallery_image = label in {'organizations.teammedia', 'siteui.communitypostmedia', 'tournaments.matchmedia'} and (_sniff_mime(content) or '').startswith('image/')
        for validator in field.validators:
            if gallery_image and validator is validate_document_upload:
                continue  # Gallery images historically include GIF/WebP, unlike PDF rules.
            validator(content)
        (validate_image_upload if image or gallery_image else validate_document_upload)(content)
        mime = _sniff_mime(content)
        allowed_extensions = {
            'image/jpeg': {'.jpg', '.jpeg'}, 'image/png': {'.png'},
            'image/webp': {'.webp'}, 'image/gif': {'.gif'}, 'application/pdf': {'.pdf'},
        }
        ext = PurePosixPath(content.name).suffix.lower()
        if ext not in allowed_extensions.get(mime, set()):
            raise ValidationError('File extension does not match its content.')
        if mime and mime.startswith('image/'):
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                try:
                    content.seek(0)
                    with Image.open(content) as decoded:
                        frames = getattr(decoded, 'n_frames', 1)
                        if frames > 100 or decoded.width * decoded.height * frames > 40_000_000:
                            raise ValidationError('Decoded image exceeds safe pixel/frame limits.')
                        decoded.verify()
                    content.seek(0)
                    with Image.open(content) as decoded:
                        for index in range(getattr(decoded, 'n_frames', 1)):
                            decoded.seek(index)
                            decoded.load()
                except (Image.DecompressionBombWarning, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
                    raise ValidationError('Invalid or oversized image.') from exc
        elif mime == 'application/pdf':
            from pypdf import PdfReader
            try:
                content.seek(0)
                pdf = PdfReader(content, strict=True)
                if pdf.is_encrypted or len(pdf.pages) > 500:
                    raise ValidationError('Encrypted or oversized PDF is not accepted.')
                root = pdf.trailer['/Root']
                names = root.get('/Names') or {}
                if hasattr(names, 'get_object'):
                    names = names.get_object()
                if root.get('/OpenAction') or root.get('/AA') or names.get('/JavaScript') or names.get('/EmbeddedFiles'):
                    raise ValidationError('Active PDF actions or embedded files are not accepted.')
            except ValidationError:
                raise
            except Exception as exc:
                raise ValidationError('Invalid PDF document.') from exc
    finally:
        content.seek(pos)
