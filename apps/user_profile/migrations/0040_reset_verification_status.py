"""
Data migration: Reset all GameProfile verification to PENDING.

Part 6 of Game Passport overhaul — sets all existing records to
verification_status='PENDING' and is_verified=False so verification
can be properly re-established through the admin verification flow.
"""
from django.db import migrations


def reset_verification(apps, schema_editor):
    GameProfile = apps.get_model('user_profile', 'GameProfile')
    updated = GameProfile.objects.all().update(
        verification_status='PENDING',
        is_verified=False,
    )
    if updated:
        print(f"\n  Reset {updated} GameProfile(s) to PENDING verification.")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0039_gamechoiceconfig_delete_gamepassportschema'),
    ]

    operations = [
        migrations.RunPython(reset_verification, noop),
    ]
