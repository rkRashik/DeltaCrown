from django.db import migrations, models


def ensure_automatic_flag(apps, schema_editor):
    table = "tournaments_tournamentsettings"
    connection = schema_editor.connection
    introspection = connection.introspection
    with connection.cursor() as cursor:
        columns = [col.name for col in introspection.get_table_description(cursor, table)]
    if "automatic_scheduling_enabled" not in columns:
        schema_editor.execute(
            "ALTER TABLE tournaments_tournamentsettings ADD COLUMN automatic_scheduling_enabled boolean"
        )
    if "auto_schedule" in columns:
        schema_editor.execute(
            "UPDATE tournaments_tournamentsettings "
            "SET automatic_scheduling_enabled = COALESCE(automatic_scheduling_enabled, auto_schedule)"
        )
    schema_editor.execute(
        "UPDATE tournaments_tournamentsettings "
        "SET automatic_scheduling_enabled = FALSE "
        "WHERE automatic_scheduling_enabled IS NULL"
    )
    schema_editor.execute(
        "ALTER TABLE tournaments_tournamentsettings "
        "ALTER COLUMN automatic_scheduling_enabled SET DEFAULT FALSE"
    )
    schema_editor.execute(
        "ALTER TABLE tournaments_tournamentsettings "
        "ALTER COLUMN automatic_scheduling_enabled SET NOT NULL"
    )


def rollback_automatic_flag(apps, schema_editor):
    table = "tournaments_tournamentsettings"
    connection = schema_editor.connection
    introspection = connection.introspection
    with connection.cursor() as cursor:
        columns = [col.name for col in introspection.get_table_description(cursor, table)]
    if "auto_schedule" in columns:
        schema_editor.execute(
            "UPDATE tournaments_tournamentsettings "
            "SET auto_schedule = COALESCE(automatic_scheduling_enabled, FALSE)"
        )
    if "automatic_scheduling_enabled" in columns:
        schema_editor.execute(
            "ALTER TABLE tournaments_tournamentsettings "
            "ALTER COLUMN automatic_scheduling_enabled DROP NOT NULL"
        )
        schema_editor.execute(
            "ALTER TABLE tournaments_tournamentsettings "
            "ALTER COLUMN automatic_scheduling_enabled DROP DEFAULT"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0017_add_custom_format_enabled"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="tournamentsettings",
                    name="automatic_scheduling_enabled",
                    field=models.BooleanField(default=False),
                ),
            ],
            database_operations=[
                migrations.RunPython(ensure_automatic_flag, rollback_automatic_flag),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="tournamentsettings",
                    name="auto_schedule",
                ),
            ],
            database_operations=[],
        ),
    ]