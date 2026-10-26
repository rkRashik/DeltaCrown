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
