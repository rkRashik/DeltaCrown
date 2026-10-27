"""Existing Cloudinary naming/CDN behavior, restricted to deliberate public art."""
import os
import cloudinary
import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage


class PublicArtworkStorage(MediaCloudinaryStorage):
    def _upload(self, name, content):
        # Preserve the upstream naming convention, but explicitly prohibit
        # overwrites even if the account's upload defaults change.
        options = {
            'use_filename': True, 'unique_filename': True, 'overwrite': False,
            'resource_type': 'image', 'type': 'upload', 'tags': self.TAG,
        }
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)

    def _get_url(self, name):
        resource = cloudinary.CloudinaryResource(
            self._prepend_prefix(name), default_resource_type='image'
        )
        return resource.build_url(secure=True, type='upload')
