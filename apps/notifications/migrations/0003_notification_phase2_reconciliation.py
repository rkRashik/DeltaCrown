from django.db import migrations, models


def _table_and_vendor(schema_editor):
    Notification = schema_editor.connection.introspection.table_names
    del Notification  # silence linters for py3.12 runtime in migration context
    return "notifications_notification", schema_editor.connection.vendor


def _get_columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return {col.name for col in description}


def _add_columns_if_missing(apps, schema_editor):
    table_name, vendor = _table_and_vendor(schema_editor)
    existing = _get_columns(schema_editor, table_name)

    ts_type = "timestamp with time zone" if vendor == "postgresql" else "datetime"
    bool_type = "boolean" if vendor == "postgresql" else "integer"
    bool_default_false = "FALSE" if vendor == "postgresql" else "0"

    statements = []
    if "is_actionable" not in existing:
        statements.append(
            f"ALTER TABLE {schema_editor.quote_name(table_name)} "
            f"ADD COLUMN {schema_editor.quote_name('is_actionable')} {bool_type} NOT NULL DEFAULT {bool_default_false}"
        )
    if "priority" not in existing:
        statements.append(
            f"ALTER TABLE {schema_editor.quote_name(table_name)} "
            f"ADD COLUMN {schema_editor.quote_name('priority')} varchar(16) NOT NULL DEFAULT 'NORMAL'"
        )
    if "read_at" not in existing:
        statements.append(
            f"ALTER TABLE {schema_editor.quote_name(table_name)} "
            f"ADD COLUMN {schema_editor.quote_name('read_at')} {ts_type} NULL"
        )

    for sql in statements:
        schema_editor.execute(sql)


CATEGORY_NORMALIZATION_SQL = """
UPDATE notifications_notification
SET category = CASE
    WHEN UPPER(COALESCE(category, '')) IN ('TOURNAMENT', 'TOURNAMENTS') THEN 'TOURNAMENT'
    WHEN UPPER(COALESCE(category, '')) IN ('TEAM', 'TEAMS') THEN 'TEAM'
    WHEN UPPER(COALESCE(category, '')) IN ('ECONOMY', 'BOUNTIES') THEN 'ECONOMY'
    WHEN UPPER(COALESCE(category, '')) IN ('SOCIAL', 'FOLLOW') THEN 'SOCIAL'
    WHEN UPPER(COALESCE(category, '')) IN ('WARNING', 'WARN') THEN 'WARNING'
    WHEN COALESCE(category, '') = '' THEN 'SYSTEM'
    ELSE 'SYSTEM'
END;
"""


READ_AT_BACKFILL_SQL = """
UPDATE notifications_notification
SET read_at = created_at
WHERE is_read = TRUE AND read_at IS NULL;
"""


def _normalize_existing_rows(apps, schema_editor):
    schema_editor.execute(CATEGORY_NORMALIZATION_SQL)
    schema_editor.execute(READ_AT_BACKFILL_SQL)


def _create_indexes_if_missing(apps, schema_editor):
    table_name, _ = _table_and_vendor(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)
    existing_names = set(constraints.keys())

    if "notifications_recipient_category_created_idx" not in existing_names:
        schema_editor.execute(
            "CREATE INDEX notifications_recipient_category_created_idx "
            "ON notifications_notification (recipient_id, category, created_at)"
        )

    if "notifications_recipient_priority_read_idx" not in existing_names:
        schema_editor.execute(
            "CREATE INDEX notifications_recipient_priority_read_idx "
            "ON notifications_notification (recipient_id, priority, is_read)"
        )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("notifications", "0002_alter_notification_type"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_add_columns_if_missing, migrations.RunPython.noop),
                migrations.RunPython(_normalize_existing_rows, migrations.RunPython.noop),
                migrations.RunPython(_create_indexes_if_missing, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="notification",
                    name="is_actionable",
                    field=models.BooleanField(db_index=True, default=False),
                ),
                migrations.AddField(
                    model_name="notification",
                    name="priority",
                    field=models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("NORMAL", "Normal"),
                            ("HIGH", "High"),
                            ("CRITICAL", "Critical"),
                        ],
                        db_index=True,
                        default="NORMAL",
                        max_length=16,
                    ),
                ),
                migrations.AddField(
                    model_name="notification",
                    name="read_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AlterField(
                    model_name="notification",
                    name="category",
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ("TOURNAMENT", "Tournament"),
                            ("TEAM", "Team"),
                            ("ECONOMY", "Economy"),
                            ("SOCIAL", "Social"),
                            ("SYSTEM", "System"),
                            ("WARNING", "Warning"),
                        ],
                        db_index=True,
                        default="SYSTEM",
                        help_text="Frontend notification category taxonomy",
                        max_length=20,
                    ),
                ),
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(
                        fields=["recipient", "category", "created_at"],
                        name="notifications_recipient_category_created_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(
                        fields=["recipient", "priority", "is_read"],
                        name="notifications_recipient_priority_read_idx",
                    ),
                ),
            ],
        ),
    ]
