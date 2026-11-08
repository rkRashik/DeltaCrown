"""Portable field behavior without changes to schema, names or migration state.

Deconstruction deliberately remains the original Django field. All behavior is
runtime Python: migrations must not depend on environment-specific storage.
"""
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.core.files.storage import storages
from django.db.models import FileField, ImageField
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.urls import reverse
from .policy import storage_alias


def enabled():
    return getattr(settings, 'OWNLOBBY_MEDIA_MODE', 'legacy') in {'local', 's3', 'hybrid'}


class GovernedFileMixin:
    def __init__(self, instance, field, name):
        super().__init__(instance, field, name)
        if enabled():
            self.storage = storages[storage_alias(field)]

    @property
    def url(self):
        if not enabled():
            return super().url
        self._require_file()
        if (getattr(settings, 'OWNLOBBY_MEDIA_MODE', 'legacy') == 'hybrid'
                and storage_alias(self.field) == 'public_media'):
            return self.storage.url(self.name)
        if not self.instance.pk:
            raise ValueError('Save the media record before requesting its URL')
        return reverse('governed_media', args=[
            self.instance._meta.concrete_model._meta.label_lower,
            self.field.name, str(self.instance.pk)
        ])

    def save(self, name, content, save=True):
        if enabled():
            from .derivatives import note_upload
            from .validation import validate_upload
            note_upload(self.instance, self.field)  # before the record is saved, so post_save sees it
            original_name = getattr(content, 'name', None)
            content.name = name
            try:
                validate_upload(content, self.field, self.instance)
            finally:
                content.name = original_name
        return super().save(name, content, save=save)


def _derive_after_upload(sender, instance, **kwargs):
    names = instance.__dict__.pop('_media_derivative_fields', None)
    if names:
        from .derivatives import generate_for_instance
        transaction.on_commit(lambda: generate_for_instance(instance, names))


post_save.connect(_derive_after_upload, dispatch_uid='ownlobby-media-derivatives')


class GovernedFile(GovernedFileMixin, FieldFile):
    pass


class GovernedImage(GovernedFileMixin, ImageFieldFile):
    pass


class MediaFileField(FileField):
    attr_class = GovernedFile

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, 'django.db.models.FileField', args, kwargs


class MediaImageField(ImageField):
    attr_class = GovernedImage

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, 'django.db.models.ImageField', args, kwargs
