"""Environment-only storage setup; does not contact any provider."""
import os
from pathlib import Path
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
from django.core.exceptions import ImproperlyConfigured


def configure(storages, base_dir, media_root):
    mode = os.getenv('OWNLOBBY_MEDIA_MODE', 'legacy')
    if mode not in {'legacy', 'local', 's3', 'hybrid'}:
        raise ImproperlyConfigured('OWNLOBBY_MEDIA_MODE must be legacy, local, s3 or hybrid')
    if mode == 'legacy':
        return mode
    for category in ('public', 'private'):
        if mode == 'hybrid' and category == 'public':
            storages['public_media'] = {
                'BACKEND': 'apps.common.media.cloudinary.PublicArtworkStorage'
            }
            continue
        if mode == 'local':
            options = {'location': str(media_root if category == 'public' else Path(base_dir) / '.private-media')}
            backend = 'apps.common.media.storage.ProtectedFileSystemStorage'
        else:
            prefix = 'MEDIA_' + category.upper() + '_'
            options = {
                'bucket_name': os.getenv(prefix + 'BUCKET', ''),
                'endpoint_url': os.getenv(prefix + 'ENDPOINT_URL', ''),
                'region_name': os.getenv(prefix + 'REGION', 'auto'),
                'access_key': os.getenv(prefix + 'ACCESS_KEY_ID', ''),
                'secret_key': os.getenv(prefix + 'SECRET_ACCESS_KEY', ''),
                'signature_version': 's3v4', 'default_acl': None,
                'file_overwrite': False, 'querystring_auth': True,
                'custom_domain': None,
                'max_memory_size': 2_621_440,
                'transfer_config': TransferConfig(max_concurrency=2, use_threads=False),
                'client_config': Config(
                    connect_timeout=5, read_timeout=30,
                    s3={'addressing_style': 'path'},
                    retries={'mode': 'standard', 'total_max_attempts': 3},
                ),
            }
            backend = 'apps.common.media.storage.ProtectedS3Storage'
        storages[category + '_media'] = {'BACKEND': backend, 'OPTIONS': options}
    storages['default'] = storages['private_media'].copy()
    return mode
