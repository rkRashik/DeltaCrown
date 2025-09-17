from django.db import migrations


def ensure_valorant_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    team_info = apps.get_model('game_valorant', 'ValorantTeamInfo')
    player = apps.get_model('game_valorant', 'ValorantPlayer')
    if team_info._meta.db_table not in existing:
        schema_editor.create_model(team_info)
    if player._meta.db_table not in existing:
        schema_editor.create_model(player)


class Migration(migrations.Migration):

    dependencies = [
        ('game_valorant', '0004_remove_valorantteaminfo_registration_and_more'),
    ]

    operations = [
        migrations.RunPython(ensure_valorant_tables, migrations.RunPython.noop),
    ]
