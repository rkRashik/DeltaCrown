"""Django system checks for the DeltaCrown deployment.

These checks surface deployment-time misconfigurations that would otherwise
cause silent data loss in production. They are registered in
``SiteUIConfig.ready()`` so ``python manage.py check`` (and Render's deploy
process) will fail loudly when something important is missing.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.checks import Error, Warning, register


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

    if "FileSystem" in default_storage:
        issues.append(
            Warning(
                "Media storage is on local filesystem in production.",
                hint=(
                    "Render's filesystem is ephemeral — every container "
                    "restart wipes /media. Configure separate governed media origins; legacy Cloudinary alone is insufficient. "
                    "Verify persistence and private file authorization so "
                    "uploaded game icons, team logos, banners, and KYC docs "
                    "survive deploys."
                ),
                id="siteui.W001",
            )
        )

    return issues


@register(deploy=True)
def persistent_media_release_check(app_configs, **kwargs):
    backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
    if not settings.DEBUG and getattr(settings, "REQUIRE_PERSISTENT_MEDIA", False) and "FileSystem" in backend:
        return [Error(
            "Production release requires durable media storage; default storage is ephemeral filesystem.",
            hint="Verify and configure durable storage and private evidence delivery before deployment. Do not bypass this gate to silence it.",
            id="siteui.E001",
        )]
    return []

@register(deploy=True)
def governed_media_release_check(app_configs, **kwargs):
    """A backend declaration is not proof of persistence, privacy or recovery."""
    if settings.DEBUG or not getattr(settings, 'REQUIRE_PERSISTENT_MEDIA', False):
        return []
    issues = []
    if getattr(settings, 'OWNLOBBY_MEDIA_MODE', 'legacy') != 's3':
        issues.append(Error('Production requires separate governed S3-compatible media origins.', id='siteui.E002'))
        return issues
    aliases = [settings.STORAGES.get(name, {}) for name in ('public_media', 'private_media')]
    for alias in aliases:
        opts = alias.get('OPTIONS', {})
        if alias.get('BACKEND') != 'apps.common.media.storage.ProtectedS3Storage' or not all(
            opts.get(k) for k in ('bucket_name', 'endpoint_url', 'access_key', 'secret_key')
        ) or not str(opts.get('endpoint_url', '')).startswith('https://'):
            issues.append(Error('Incomplete or insecure governed media storage configuration.', id='siteui.E003'))
    if aliases[0].get('OPTIONS', {}).get('bucket_name') == aliases[1].get('OPTIONS', {}).get('bucket_name'):
        issues.append(Error('Public and confidential media must use distinct buckets.', id='siteui.E004'))
    if not getattr(settings, 'MEDIA_STORAGE_VERIFIED', False) or not getattr(settings, 'MEDIA_RESTORE_VERIFIED', False):
        issues.append(Error('Private-origin, restart persistence and independent restore proof required.',
                            hint='Leave verification flags false until approved real staging and restore drills pass.', id='siteui.E005'))
    return issues

@register()
def media_field_policy_check(app_configs, **kwargs):
    if getattr(settings, 'OWNLOBBY_MEDIA_MODE', 'legacy') == 'legacy':
        return []
    from django.apps import apps
    from django.db.models import FileField
    from apps.common.media.fields import MediaFileField, MediaImageField
    from apps.common.media.policy import KNOWN_FIELDS
    issues = []
    for model in apps.get_models():
        if model._meta.proxy:
            continue
        for field in model._meta.fields:
            if isinstance(field, FileField) and (
                not isinstance(field, (MediaFileField, MediaImageField))
                or (model._meta.label_lower, field.name) not in KNOWN_FIELDS
            ):
                issues.append(Error('Upload field requires an explicit storage/delivery policy.', obj=field, id='siteui.E006'))
    return issues
