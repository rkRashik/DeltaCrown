"""Django system checks for the DeltaCrown deployment.

These checks surface deployment-time misconfigurations that would otherwise
cause silent data loss in production. They are registered in
``SiteUIConfig.ready()`` so ``python manage.py check`` (and Render's deploy
process) will fail loudly when something important is missing.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.checks import Warning, register


@register()
def media_storage_check(app_configs, **kwargs):
    """Warn when running in production without persistent media storage.

    Render's filesystem is ephemeral — every container restart wipes
    ``MEDIA_ROOT``. The platform falls back to ``FileSystemStorage`` when
    ``CLOUDINARY_URL`` is not set, which means uploaded files (game icons,
    team logos, banners, KYC docs, certificates) disappear on the next deploy.

    This check fires only when ``DEBUG=False`` so local development is
    untouched.
    """
    issues = []
    if settings.DEBUG:
        return issues

    default_storage = ""
    try:
        default_storage = settings.STORAGES["default"]["BACKEND"]
    except Exception:
        pass

    if not os.getenv("CLOUDINARY_URL") and "FileSystem" in default_storage:
        issues.append(
            Warning(
                "Media storage is on local filesystem in production.",
                hint=(
                    "Render's filesystem is ephemeral — every container "
                    "restart wipes /media. Set the CLOUDINARY_URL environment "
                    "variable (or another persistent storage backend) so "
                    "uploaded game icons, team logos, banners, and KYC docs "
                    "survive deploys."
                ),
                id="siteui.W001",
            )
        )

    return issues
