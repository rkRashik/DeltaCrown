"""Guarded local PostgreSQL QA with the real governed media path enabled."""

from .settings_brand_qa import *

OWNLOBBY_MEDIA_MODE = "local"
STORAGES = dict(STORAGES)
for category in ("public", "private"):
    STORAGES[category + "_media"] = {
        "BACKEND": "apps.common.media.storage.ProtectedFileSystemStorage",
        "OPTIONS": {"location": str(BASE_DIR / "Artifacts/final-engineering/media" / category)},
    }
STORAGES["default"] = STORAGES["private_media"]
CKEDITOR_5_FILE_STORAGE = "apps.common.media.editor.EditorStorage"

# Synthetic credentials are needed at Django override_settings teardown:
# django-cloudinary-storage reloads its app settings when the test restores
# the QA baseline. Never use a real Cloudinary API credential in Linux CI.
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": "synthetic-qa-cloud",
    "API_KEY": "synthetic-qa-key",
    "API_SECRET": "synthetic-qa-secret",
}
