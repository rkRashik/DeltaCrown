"""Private origins. Application routes, not object-store URLs, grant delivery."""
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage


class NoRawURL:
    def url(self, name, *args, **kwargs):
        raise ValueError('Media delivery requires a record-authorized application URL')


class ProtectedFileSystemStorage(NoRawURL, FileSystemStorage):
    pass


class ProtectedS3Storage(NoRawURL, S3Storage):
    default_acl = None
    file_overwrite = False
    querystring_auth = True
    custom_domain = None
    object_parameters = {'CacheControl': 'private, no-store', 'ContentDisposition': 'attachment'}
