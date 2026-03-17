"""
Encrypt OAuth tokens at rest.

Changes access_token and refresh_token from TextField to EncryptedTextField,
then encrypts any existing plaintext values in-place.
"""

from django.db import migrations

from apps.user_profile.fields import EncryptedTextField, _get_fernet


def encrypt_existing_tokens(apps, schema_editor):
    """Encrypt any plaintext tokens already stored."""
    GameOAuthConnection = apps.get_model("user_profile", "GameOAuthConnection")
    fernet = _get_fernet()

    for conn in GameOAuthConnection.objects.all():
        changed = False
        if conn.access_token and not conn.access_token.startswith("gAAAAA"):
            conn.access_token = fernet.encrypt(conn.access_token.encode()).decode()
            changed = True
        if conn.refresh_token and not conn.refresh_token.startswith("gAAAAA"):
            conn.refresh_token = fernet.encrypt(conn.refresh_token.encode()).decode()
            changed = True
        if changed:
            # Raw update to avoid model-level re-encryption
            GameOAuthConnection.objects.filter(pk=conn.pk).update(
                access_token=conn.access_token,
                refresh_token=conn.refresh_token,
            )


def noop_reverse(apps, schema_editor):
    """Reverse is a no-op — encrypted tokens stay encrypted."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0037_gameoauthconnection_epic_provider"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gameoauthconnection",
            name="access_token",
            field=EncryptedTextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="gameoauthconnection",
            name="refresh_token",
            field=EncryptedTextField(blank=True, default=""),
        ),
        migrations.RunPython(encrypt_existing_tokens, noop_reverse),
    ]
