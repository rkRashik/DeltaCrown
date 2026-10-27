"""Hybrid media policy tests; provider calls are mocked, credentials synthetic."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.common.media.configuration import configure
from apps.common.media.policy import CLOUDINARY_PUBLIC_FIELDS, KNOWN_FIELDS, storage_alias
from apps.siteui.checks import governed_media_release_check


@override_settings(OWNLOBBY_MEDIA_MODE='hybrid')
class HybridMediaTests(SimpleTestCase):
    def test_only_unconditional_public_artwork_uses_cdn(self):
        for label, name in KNOWN_FIELDS:
            field = apps.get_model(label)._meta.get_field(name)
            self.assertEqual(storage_alias(field),
                             'public_media' if (label, name) in CLOUDINARY_PUBLIC_FIELDS else 'private_media')

    def test_configuration_uses_existing_cloudinary_and_only_private_s3(self):
        with patch.dict('os.environ', {'OWNLOBBY_MEDIA_MODE': 'hybrid'}):
            config = {}
            self.assertEqual(configure(config, Path('.'), Path('media')), 'hybrid')
        self.assertEqual(config['public_media']['BACKEND'], 'apps.common.media.cloudinary.PublicArtworkStorage')
        self.assertEqual(config['private_media']['BACKEND'], 'apps.common.media.storage.ProtectedS3Storage')
        self.assertEqual(config['default'], config['private_media'])
        self.assertFalse(config['private_media']['OPTIONS']['file_overwrite'])
        self.assertEqual(config['private_media']['OPTIONS']['client_config'].s3, {'addressing_style': 'path'})

    def test_cloudinary_keeps_existing_identifiers_and_secure_cdn(self):
        from apps.common.media.cloudinary import PublicArtworkStorage
        from cloudinary_storage.storage import MediaCloudinaryStorage
        name = 'media/organizations/logos/existing-artwork'
        storage = PublicArtworkStorage()
        self.assertEqual(storage._prepend_prefix(name), MediaCloudinaryStorage()._prepend_prefix(name))
        self.assertTrue(storage.url(name).startswith('https://res.cloudinary.com/'))
        Organization = apps.get_model('organizations.Organization')
        with override_settings(STORAGES={
            'public_media': {'BACKEND': 'apps.common.media.cloudinary.PublicArtworkStorage'},
        }):
            obj = Organization(logo=name)
            self.assertEqual(obj.logo.name, name)
            self.assertEqual(obj.logo.url, storage.url(name))

    def test_cloudinary_upload_never_overwrites_and_delete_not_called(self):
        from apps.common.media.cloudinary import PublicArtworkStorage
        output = BytesIO()
        Image.new('RGB', (2, 2)).save(output, 'PNG')
        with patch('cloudinary.uploader.upload', return_value={'public_id': 'media/art/new-unique'}) as upload, patch('cloudinary.uploader.destroy') as destroy:
            result = PublicArtworkStorage().save('art/image.png', ContentFile(output.getvalue()))
        self.assertEqual(result, 'media/art/new-unique')
        self.assertFalse(upload.call_args.kwargs['overwrite'])
        self.assertTrue(upload.call_args.kwargs['unique_filename'])
        self.assertEqual(upload.call_args.kwargs['type'], 'upload')
        destroy.assert_not_called()

    def test_unbound_editor_drafts_cannot_publish_to_cloudinary(self):
        from apps.common.media.editor import EditorStorage
        with patch('cloudinary.uploader.upload') as upload, self.assertRaises(ValidationError):
            EditorStorage().save('draft.png', ContentFile(b'not-published'))
        upload.assert_not_called()

    def test_existing_private_name_is_unchanged_and_never_cloudinary(self):
        from apps.common.media.storage import ProtectedS3Storage
        config = {'private_media': {'BACKEND': 'apps.common.media.storage.ProtectedS3Storage',
                  'OPTIONS': {'bucket_name': 'synthetic-private', 'access_key': 'synthetic', 'secret_key': 'synthetic'}}}
        with override_settings(STORAGES=config):
            record = apps.get_model('user_profile.VerificationRecord')(pk=123, id_document_front='media/kyc/original')
            self.assertEqual(record.id_document_front.name, 'media/kyc/original')
            self.assertIsInstance(record.id_document_front.storage, ProtectedS3Storage)
            self.assertTrue(record.id_document_front.url.startswith('/files/'))
            with self.assertRaises(ValueError):
                record.id_document_front.storage.url(record.id_document_front.name)

    def test_release_gate_requires_real_persistence_restore_and_legacy_privacy(self):
        env = {'OWNLOBBY_MEDIA_MODE': 'hybrid', 'CLOUDINARY_URL': 'cloudinary://synthetic:synthetic@synthetic',
               'MEDIA_PRIVATE_BUCKET': 'synthetic-private', 'MEDIA_PRIVATE_ENDPOINT_URL': 'https://storage.example.invalid/storage/v1/s3',
               'MEDIA_PRIVATE_ACCESS_KEY_ID': 'synthetic', 'MEDIA_PRIVATE_SECRET_ACCESS_KEY': 'synthetic'}
        with patch.dict('os.environ', env):
            config = {}
            configure(config, Path('.'), Path('media'))
            with override_settings(STORAGES=config, DEBUG=False, REQUIRE_PERSISTENT_MEDIA=True,
                                   MEDIA_STORAGE_VERIFIED=False, MEDIA_RESTORE_VERIFIED=False,
                                   MEDIA_LEGACY_PRIVACY_VERIFIED=False):
                self.assertEqual({e.id for e in governed_media_release_check(None)}, {'siteui.E005', 'siteui.E007'})
                with override_settings(MEDIA_STORAGE_VERIFIED=True, MEDIA_RESTORE_VERIFIED=True,
                                       MEDIA_LEGACY_PRIVACY_VERIFIED=True):
                    self.assertEqual(governed_media_release_check(None), [])
                with patch.dict('os.environ', {'CLOUDINARY_URL': ''}):
                    self.assertIn('siteui.E003', {e.id for e in governed_media_release_check(None)})
