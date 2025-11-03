from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0022_alter_tournament_short_description_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'tournaments_tournamentsettings'
                      AND column_name = 'round_duration_mins'
                ) THEN
                    ALTER TABLE tournaments_tournamentsettings ADD COLUMN round_duration_mins integer;
                END IF;
            END $$;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_duration_mins DROP NOT NULL;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_duration_mins DROP DEFAULT;
            """,
            """
            UPDATE tournaments_tournamentsettings SET round_duration_mins = COALESCE(round_duration_mins, 45);
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_duration_mins SET DEFAULT 45;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_duration_mins SET NOT NULL;
            """,
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'tournaments_tournamentsettings'
                      AND column_name = 'round_gap_mins'
                ) THEN
                    ALTER TABLE tournaments_tournamentsettings ADD COLUMN round_gap_mins integer;
                END IF;
            END $$;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_gap_mins DROP NOT NULL;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_gap_mins DROP DEFAULT;
            """,
            """
            UPDATE tournaments_tournamentsettings SET round_gap_mins = COALESCE(round_gap_mins, 10);
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_gap_mins SET DEFAULT 10;
            ALTER TABLE tournaments_tournamentsettings ALTER COLUMN round_gap_mins SET NOT NULL;
            """,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="tournamentsettings",
                    name="round_duration_mins",
                    field=models.PositiveIntegerField(blank=True, help_text="Target round duration in minutes for auto scheduling.", null=True),
                ),
                migrations.AddField(
                    model_name="tournamentsettings",
                    name="round_gap_mins",
                    field=models.PositiveIntegerField(blank=True, help_text="Gap between rounds in minutes for auto scheduling.", null=True),
                ),
            ],
            database_operations=[],
        ),
    ]

