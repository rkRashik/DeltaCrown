"""Staff editor uploads are deliberate public-image publishing, not evidence."""
import uuid
from types import SimpleNamespace
from pathlib import PurePosixPath
from django.core import signing
from django.core.files.storage import Storage, storages
from django.db.models import ImageField
from django.urls import reverse
from .validation import validate_upload


class EditorStorage(Storage):
    def _open(self, name, mode='rb'):
        return storages['public_media'].open(name, mode)

    def _save(self, name, content):
        field = ImageField()
        field.model = SimpleNamespace(_meta=SimpleNamespace(label_lower='editor.image'))
        original_name = getattr(content, 'name', None)
        content.name = name
        try:
            validate_upload(content, field, None)
        finally:
            content.name = original_name
        key = 'editor/' + uuid.uuid4().hex + PurePosixPath(name).suffix.lower()
        return storages['public_media'].save(key, content)

    def exists(self, name):
        return storages['public_media'].exists(name)

    def delete(self, name):
        return storages['public_media'].delete(name)

    def url(self, name):
        return reverse('published_editor_media', args=[signing.dumps(name, salt='published-editor-image')])
