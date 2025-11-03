from django.db import migrations, models

def _has_column(schema_editor, table_name: str, column: str) -> bool:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            [table_name, column],
        )
        return cursor.fetchone() is not None

def add_allow_substitutes(apps, schema_editor):
    table = 'tournaments_tournamentsettings'
    column = 'allow_substitutes'
    if _has_column(schema_editor, table, column):
        return
    Model = apps.get_model('tournaments', 'TournamentSettings')
    field = models.BooleanField(
        default=False,
        help_text='Allow teams to register substitute players.',
    )
    field.set_attributes_from_name(column)
    schema_editor.add_field(Model, field)

def remove_allow_substitutes(apps, schema_editor):
    table = 'tournaments_tournamentsettings'
    column = 'allow_substitutes'
    if not _has_column(schema_editor, table, column):
        return
    Model = apps.get_model('tournaments', 'TournamentSettings')
    field = Model._meta.get_field(column)
    schema_editor.remove_field(Model, field)

class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0013_paymentverification_last_action_reason_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_allow_substitutes, remove_allow_substitutes),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='tournamentsettings',
                    name='allow_substitutes',
                    field=models.BooleanField(
                        default=False,
                        help_text='Allow teams to register substitute players.',
                    ),
                ),
            ],
        ),
    ]
