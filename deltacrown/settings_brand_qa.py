"""Strictly local, disposable rebrand QA; never point this at application data.

Set DATABASE_URL_TEST=postgresql://...@127.0.0.1:<port>/ownlobby_test.
The test runner reuses this disposable database only with --keepdb.
"""
import os
os.environ["DISABLE_INPROCESS_MATCH_REMINDER"] = "1"
from .settings_test import *
from django.core.exceptions import ImproperlyConfigured

_qa_database = DATABASES["default"]
if _qa_database.get("HOST") not in {"localhost", "127.0.0.1", "::1"} or _qa_database.get("NAME") != "ownlobby_test":
    raise ImproperlyConfigured("OwnLobby QA requires a LOCAL disposable database named ownlobby_test.")
_qa_database["TEST"] = {"NAME": "ownlobby_test"}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True
MEDIA_ROOT = BASE_DIR / "Artifacts/ownlobby/media"
STATIC_ROOT = BASE_DIR / "Artifacts/ownlobby/collected-static"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
SECURE_SSL_REDIRECT = False
MIDDLEWARE = [item for item in MIDDLEWARE if item != "deltacrown.middleware.media_proxy.MediaProxyMiddleware"]
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver", "deltacrown.xyz", "ownlobby.com"]
