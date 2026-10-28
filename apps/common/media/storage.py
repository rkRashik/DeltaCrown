"""Private origins. Application routes, not object-store URLs, grant delivery."""
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage


class NoRawURL:
    def url(self, name, *args, **kwargs):
        raise ValueError('Media delivery requires a record-authorized application URL')


class ProtectedFileSystemStorage(NoRawURL, FileSystemStorage):
    pass


class ProtectedS3Storage(NoRawURL, S3Storage):
    def open_stream_object(self, name):
        """Return a private S3 GET stream without django-storages' full-file spool.

        Called only after record-level authorization in the media view. Never
        returns a provider URL or publishes an object.
        """
        key = self._encode_name(self._normalize_name(name))
        return self.bucket.Object(key).get()

    default_acl = None
    file_overwrite = False
    querystring_auth = True
    custom_domain = None
    object_parameters = {'CacheControl': 'private, no-store', 'ContentDisposition': 'attachment'}
