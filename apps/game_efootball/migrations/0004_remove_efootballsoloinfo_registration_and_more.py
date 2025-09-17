from django.db import migrations


def ensure_efootball_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    solo = apps.get_model('game_efootball', 'EfootballSoloInfo')
    duo = apps.get_model('game_efootball', 'EfootballDuoInfo')
    if solo._meta.db_table not in existing:
        schema_editor.create_model(solo)
    if duo._meta.db_table not in existing:
        schema_editor.create_model(duo)


class Migration(migrations.Migration):

    dependencies = [
        ('game_efootball', '0003_efootballsoloinfo_efootballduoinfo'),
    ]

    operations = [
        migrations.RunPython(ensure_efootball_tables, migrations.RunPython.noop),
    ]
