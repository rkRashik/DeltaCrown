"""System checks for field-encryption and signing-key rotation settings (no secret values printed)."""
from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.core.exceptions import ImproperlyConfigured


@register(Tags.security)
def field_encryption_configuration(app_configs, **kwargs):
    from apps.user_profile.fields import _fernets

    try:
        _fernets()
    except ImproperlyConfigured as exc:
        return [Error(str(exc), id="user_profile.E001")]
    return []


@register(Tags.security, deploy=True)
def field_encryption_key_is_separate(app_configs, **kwargs):
    messages = []
    if not getattr(settings, "FIELD_ENCRYPTION_KEY", None):
        messages.append(Warning(
            "FIELD_ENCRYPTION_KEY is not set: OAuth token encryption is derived from SECRET_KEY, so "
            "rotating SECRET_KEY would strand stored tokens. Follow the signing-key rotation runbook.",
            id="user_profile.W001",
        ))
    if getattr(settings, "SECRET_KEY_FALLBACKS", None):
        messages.append(Warning(
            "SECRET_KEY_FALLBACKS is configured: a previous signing key is still accepted. Remove it "
            "once the runbook's removal conditions are met.",
            id="user_profile.W002",
        ))
    if getattr(settings, "FIELD_ENCRYPTION_LEGACY_SECRET_KEYS", None) or getattr(settings, "FIELD_ENCRYPTION_LEGACY_KEYS", None):
        messages.append(Warning(
            "Legacy field-encryption keys are configured (decrypt-only). Run reencrypt_oauth_tokens and "
            "remove them once it reports no legacy rows.",
            id="user_profile.W003",
        ))
    return messages
