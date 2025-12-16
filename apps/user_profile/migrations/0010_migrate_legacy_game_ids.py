from django.db import migrations


def migrate_legacy_game_ids(apps, schema_editor):
    """Migrate legacy game ID columns into the `game_profiles` JSON field.

    This migration is defensive: some legacy columns may already be absent
    in a deployed schema, so we only SELECT columns that actually exist.
    """
    import json

    UserProfile = apps.get_model('user_profile', 'UserProfile')

    mapping = [
        ('valorant', 'riot_id'),
        ('efootball', 'efootball_id'),
        ('dota2', 'steam_id'),
        ('cs2', 'steam_id'),
        ('mlbb', 'mlbb_id'),
        ('pubgm', 'pubg_mobile_id'),
        ('freefire', 'free_fire_id'),
        ('fc24', 'ea_id'),
        ('codm', 'codm_uid'),
    ]

    # Discover which legacy columns actually exist in the DB
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_profile_userprofile'")
        existing_cols = {r[0] for r in cursor.fetchall()}

        desired_fields = [field for (_game, field) in mapping if field in existing_cols]
        select_fields = ["id", "game_profiles"] + desired_fields

        if not desired_fields:
            # Nothing to migrate
            return

        sql = f"SELECT {', '.join(select_fields)} FROM user_profile_userprofile"
        cursor.execute(sql)
        rows = cursor.fetchall()

        for row in rows:
            row_id = row[0]
            gp_raw = row[1]
            try:
                gp = list(gp_raw or [])
            except Exception:
                # If DB driver returns string for JSON, try to load
                try:
                    gp = json.loads(gp_raw) if gp_raw else []
                except Exception:
                    gp = []

            changed = False
            for idx, (_game, field) in enumerate([m for m in mapping if m[1] in desired_fields]):
                val = row[2 + idx]
                if val:
                    exists = any(p.get('game', '').lower() == _game for p in gp)
                    if not exists:
                        gp.append({
                            'game': _game,
                            'ign': val,
                            'role': '',
                            'rank': '',
                            'platform': 'PC' if _game in ('valorant','cs2','dota2','efootball') else 'Mobile',
                            'is_verified': False,
                            'metadata': {},
                        })
                        changed = True

            if changed:
                # Use queryset update to avoid loading full model (safer during migrations)
                UserProfile.objects.filter(id=row_id).update(game_profiles=gp)


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0009_add_riot_id'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_game_ids, reverse_code=migrations.RunPython.noop),
    ]
